<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\Core\Database\Connection;
use Drupal\Core\Datetime\TimeInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\verifiable_voting\Contract\SignatureProviderInterface;
use Drupal\verifiable_voting\Contract\TallyProviderInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;

/**
 * Applies guarded lifecycle transitions and records each public checkpoint.
 */
final class ElectionLifecycleManager {

  /**
   * Constructs the lifecycle manager.
   */
  public function __construct(
    private readonly Connection $database,
    private readonly TimeInterface $time,
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly ElectionReadinessChecker $readinessChecker,
    private readonly JcsCanonicalizer $canonicalizer,
    private readonly HashChainLedger $ledger,
    private readonly ProviderRegistry $signatureRegistry,
    private readonly ProviderRegistry $encryptionRegistry,
    private readonly ProviderRegistry $tallyRegistry,
    private readonly PrivacyAwareAuditLogger $auditLogger,
  ) {}

  /**
   * Applies a permitted, security-sensitive lifecycle operation.
   */
  public function transition(ElectionInterface $election, string $operation): void {
    $state = (string) $election->get('status')->value;
    $allowed = [
      'open' => ['draft', 'configured'],
      'close' => ['open'],
      'tally' => ['closed'],
      'certify' => ['tallying'],
      'archive' => ['certified'],
      'invalidate' => ['open', 'closed', 'tallying', 'certified'],
    ];
    if (!isset($allowed[$operation]) || !in_array($state, $allowed[$operation], TRUE)) {
      throw new \DomainException(sprintf('Operation "%s" is not permitted from lifecycle state "%s".', $operation, $state));
    }
    match ($operation) {
      'open' => $this->open($election),
      'close' => $this->close($election),
      'tally' => $this->tally($election),
      'certify' => $this->certify($election),
      'archive' => $this->archive($election),
      'invalidate' => $this->invalidate($election),
    };
  }

  /**
   * Freezes and opens an election after all readiness checks succeed.
   */
  private function open(ElectionInterface $election): void {
    $checks = $this->readinessChecker->check($election);
    $failed = array_filter($checks, static fn(array $check): bool => !$check['passed']);
    if ($failed !== []) {
      $messages = implode(' ', array_map(static fn(array $check): string => $check['message'], $failed));
      throw new \RuntimeException('Election cannot open: ' . $messages);
    }
    $manifest = $this->buildManifest($election);
    $manifest_json = $this->canonicalizer->canonicalize($manifest);
    $manifest_hash = sodium_bin2base64(hash('sha256', $manifest_json, TRUE), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
    $transaction = $this->database->startTransaction();
    $election->set('manifest_json', $manifest_json);
    $election->set('manifest_hash', $manifest_hash);
    $election->set('status', 'open');
    $election->save();
    $record = $this->ledger->append($election->electionUuid(), 'election_opened', [
      'manifest' => $manifest,
      'manifest_hash' => $manifest_hash,
    ]);
    unset($transaction);
    $this->auditLogger->log('election_opened', $election->electionUuid(), ['record_hash' => $record['record_hash'], 'status' => 'open']);
  }

  /**
   * Closes an open election and commits the last pre-tally checkpoint.
   */
  private function close(ElectionInterface $election): void {
    $transaction = $this->database->startTransaction();
    $election->set('status', 'closed');
    $election->save();
    $record = $this->ledger->append($election->electionUuid(), 'election_closed', [
      'manifest_hash' => (string) $election->get('manifest_hash')->value,
      'closed_at' => $this->time->getRequestTime(),
    ]);
    unset($transaction);
    $this->auditLogger->log('election_closed', $election->electionUuid(), ['record_hash' => $record['record_hash'], 'status' => 'closed']);
  }

  /**
   * Produces and commits a provider-versioned tally artifact.
   */
  private function tally(ElectionInterface $election): void {
    $provider = $this->tallyRegistry->get((string) $election->get('tally_provider')->value);
    if (!$provider instanceof TallyProviderInterface) {
      throw new \LogicException('Configured tally provider has an invalid contract.');
    }
    $artifact = $provider->tally($election);
    $artifact_json = $this->canonicalizer->canonicalize($artifact);
    $artifact_hash = sodium_bin2base64(hash('sha256', $artifact_json, TRUE), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
    $transaction = $this->database->startTransaction();
    $election->set('final_tally', $artifact_json);
    $election->set('status', 'tallying');
    $election->save();
    $record = $this->ledger->append($election->electionUuid(), 'tally_generated', [
      'tally_artifact' => $artifact,
      'tally_artifact_hash' => $artifact_hash,
    ]);
    unset($transaction);
    $this->auditLogger->log('tally_generated', $election->electionUuid(), ['record_hash' => $record['record_hash'], 'artifact_hash' => $artifact_hash, 'status' => 'tallying']);
  }

  /**
   * Records a signed certification statement and final ledger root.
   */
  private function certify(ElectionInterface $election): void {
    $ledger_result = $this->ledger->verify($election->electionUuid());
    if (!$ledger_result['valid']) {
      throw new \RuntimeException('Election ledger cannot be certified because it does not verify.');
    }
    $signer = $this->signatureRegistry->get((string) $election->get('signature_provider')->value);
    if (!$signer instanceof SignatureProviderInterface) {
      throw new \LogicException('Configured signing provider has an invalid contract.');
    }
    $statement = [
      'protocol_version' => 'verifiable-voting/1',
      'election_uuid' => $election->electionUuid(),
      'ledger_root_before_certification' => $ledger_result['final_hash'],
      'ledger_entry_count_before_certification' => $ledger_result['count'],
      'manifest_hash' => (string) $election->get('manifest_hash')->value,
      'tally_hash' => sodium_bin2base64(hash('sha256', (string) $election->get('final_tally')->value, TRUE), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING),
      'certified_at' => $this->time->getRequestTime(),
    ];
    $statement_json = $this->canonicalizer->canonicalize($statement);
    $signature = sodium_bin2base64($signer->sign($statement_json, $this->configuration($election, 'signature_configuration')), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
    $transaction = $this->database->startTransaction();
    $record = $this->ledger->append($election->electionUuid(), 'election_certified', [
      'certification' => $statement,
      'signature' => $signature,
      'signer' => $signer->publicMetadata($this->configuration($election, 'signature_configuration')),
    ]);
    $election->set('ledger_final_root', $record['record_hash']);
    $election->set('certified_at', $statement['certified_at']);
    $election->set('certification_signature', $signature);
    $election->set('status', 'certified');
    $election->save();
    unset($transaction);
    $this->auditLogger->log('election_certified', $election->electionUuid(), ['record_hash' => $record['record_hash'], 'status' => 'certified']);
  }

  /**
   * Archives a certified election without altering its committed evidence.
   */
  private function archive(ElectionInterface $election): void {
    $election->set('status', 'archived');
    $election->save();
    $this->auditLogger->log('election_archived', $election->electionUuid(), ['status' => 'archived']);
  }

  /**
   * Makes invalidation a new public, auditable lifecycle event.
   */
  private function invalidate(ElectionInterface $election): void {
    $transaction = $this->database->startTransaction();
    $record = $this->ledger->append($election->electionUuid(), 'election_invalidated', [
      'invalidated_at' => $this->time->getRequestTime(),
      'previous_status' => (string) $election->get('status')->value,
    ]);
    $election->set('status', 'invalidated');
    $election->save();
    unset($transaction);
    $this->auditLogger->log('election_invalidated', $election->electionUuid(), ['record_hash' => $record['record_hash'], 'status' => 'invalidated']);
  }

  /**
   * Builds the immutable public manifest using stable IDs and UUIDs.
   *
   * @return array<string, mixed>
   *   Public manifest.
   */
  private function buildManifest(ElectionInterface $election): array {
    $storage = $this->entityTypeManager->getStorage('verifiable_voting_choice');
    $ids = $storage->getQuery()->accessCheck(FALSE)
      ->condition('election', $election->id())
      ->condition('active', TRUE)
      ->sort('weight')
      ->sort('uuid')
      ->execute();
    $choices = [];
    foreach ($storage->loadMultiple($ids) as $choice) {
      $choices[] = [
        'uuid' => (string) $choice->uuid(),
        'stable_id' => (string) $choice->get('stable_id')->value,
        'label' => (string) $choice->get('label')->value,
        'description' => (string) $choice->get('description')->value,
        'weight' => (int) $choice->get('weight')->value,
      ];
    }
    $encryption = $this->providerMetadata($this->encryptionRegistry, (string) $election->get('encryption_provider')->value, $this->configuration($election, 'encryption_configuration'));
    $signature = $this->providerMetadata($this->signatureRegistry, (string) $election->get('signature_provider')->value, $this->configuration($election, 'signature_configuration'));
    return [
      'protocol_version' => (string) $election->get('protocol_version')->value,
      'election_uuid' => $election->electionUuid(),
      'machine_name' => (string) $election->get('machine_name')->value,
      'title' => $election->label(),
      'description' => (string) $election->get('description')->value,
      'opens_at' => (int) $election->get('opens_at')->value,
      'closes_at' => (int) $election->get('closes_at')->value,
      'ballot_type' => (string) $election->get('ballot_type')->value,
      'ballot_definition' => $this->configuration($election, 'ballot_definition'),
      'choices' => $choices,
      'providers' => [
        'eligibility' => (string) $election->get('eligibility_provider')->value,
        'proof' => (string) $election->get('proof_provider')->value,
        'encryption' => $encryption,
        'signature' => $signature,
        'tally' => (string) $election->get('tally_provider')->value,
      ],
    ];
  }

  /**
   * Returns public provider metadata where supported.
   *
   * @param object $provider
   *   Provider with publicMetadata().
   *
   * @return array<string, mixed>
   *   Public metadata.
   */
  private function providerMetadata(ProviderRegistry $registry, string $provider_id, array $configuration): array {
    $provider = $registry->get($provider_id);
    if (!method_exists($provider, 'publicMetadata')) {
      return ['provider' => $provider->id()];
    }
    /** @var array<string, mixed> $metadata */
    $metadata = $provider->publicMetadata($configuration);
    return $metadata + ['provider' => $provider->id()];
  }

  /**
   * Extracts a map field into a plain array.
   *
   * @return array<string, mixed>
   *   Configuration map.
   */
  private function configuration(ElectionInterface $election, string $field_name): array {
    $item = $election->get($field_name)->first();
    return $item === NULL ? [] : $item->getValue();
  }

}
