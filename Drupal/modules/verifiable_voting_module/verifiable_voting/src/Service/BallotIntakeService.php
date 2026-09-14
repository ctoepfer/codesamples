<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\Core\Database\Connection;
use Drupal\Core\Datetime\TimeInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\verifiable_voting\Contract\EligibilityProviderInterface;
use Drupal\verifiable_voting\Contract\EncryptionProviderInterface;
use Drupal\verifiable_voting\Contract\ProofVerifierInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;
use Drupal\verifiable_voting\Plugin\BallotTypeManager;

/**
 * Validates and accepts ballots within a single durable database transaction.
 */
final class BallotIntakeService {

  /**
   * Constructs ballot intake.
   */
  public function __construct(
    private readonly Connection $database,
    private readonly TimeInterface $time,
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly BallotTypeManager $ballotTypeManager,
    private readonly ProviderRegistry $eligibilityRegistry,
    private readonly ProviderRegistry $proofRegistry,
    private readonly ProviderRegistry $encryptionRegistry,
    private readonly ReceiptGenerator $receiptGenerator,
    private readonly HashChainLedger $ledger,
    private readonly PrivacyAwareAuditLogger $auditLogger,
  ) {}

  /**
   * Accepts one ballot and returns its non-secret receipt and ledger evidence.
   *
   * @param array<string, mixed> $plaintext_ballot
   *   Untrusted selection data. It is never persisted in the ballot entity.
   * @param array<string, mixed> $credential
   *   Provider-specific credential assertion.
   * @param array<string, mixed> $proof
   *   Provider-specific externally generated proof material.
   *
   * @return array{receipt: string, display_receipt: string, sequence: int, ledger_hash: string}
   *   Public receipt and evidence fields.
   */
  public function accept(ElectionInterface $election, array $plaintext_ballot, array $credential, array $proof = []): array {
    $this->assertElectionOpen($election);
    $ballot_type = $this->ballotTypeManager->createInstance((string) $election->get('ballot_type')->value);
    $choices = $this->activeChoices($election);
    $allowed_choice_uuids = array_map(static fn($choice): string => (string) $choice->uuid(), $choices);
    $canonical_ballot = $ballot_type->canonicalizePlaintextBallot($plaintext_ballot, $allowed_choice_uuids, $this->configuration($election, 'ballot_definition'));

    $eligibility = $this->eligibilityRegistry->get((string) $election->get('eligibility_provider')->value);
    $encryption = $this->encryptionRegistry->get((string) $election->get('encryption_provider')->value);
    $verifier = $this->proofRegistry->get((string) $election->get('proof_provider')->value);
    if (!$eligibility instanceof EligibilityProviderInterface || !$encryption instanceof EncryptionProviderInterface || !$verifier instanceof ProofVerifierInterface) {
      throw new \LogicException('Configured ballot providers do not meet their required contracts.');
    }

    $eligibility_result = $eligibility->verify($election->electionUuid(), $credential, $this->configuration($election, 'eligibility_configuration'));
    if (!$eligibility_result['accepted'] || $eligibility_result['nullifier'] === '') {
      $this->auditLogger->log('ballot_rejected', $election->electionUuid(), ['reason_code' => $eligibility_result['reason_code'], 'provider' => $eligibility->id()]);
      throw new \InvalidArgumentException('Eligibility verification failed.');
    }
    $ciphertext = $encryption->encrypt($election->electionUuid(), $canonical_ballot, $this->configuration($election, 'encryption_configuration'));
    $proof_result = $verifier->verify($election->electionUuid(), $ciphertext, $proof, $this->configuration($election, 'proof_configuration'));
    if (!$proof_result['valid']) {
      $this->auditLogger->log('ballot_rejected', $election->electionUuid(), ['reason_code' => $proof_result['reason_code'], 'provider' => $verifier->id()]);
      throw new \InvalidArgumentException('Ballot proof verification failed.');
    }

    $transaction = $this->database->startTransaction();
    try {
      $this->database->insert('verifiable_voting_nullifier_guard')->fields([
        'election_uuid' => $election->electionUuid(),
        'nullifier' => $eligibility_result['nullifier'],
        'created' => $this->time->getRequestTime(),
      ])->execute();
    }
    catch (\Exception $exception) {
      $this->auditLogger->log('ballot_rejected', $election->electionUuid(), ['reason_code' => 'duplicate_nullifier', 'provider' => $eligibility->id()]);
      throw new \DomainException('This election credential has already cast an accepted ballot.', previous: $exception);
    }

    $accepted_envelope = [
      'protocol_version' => (string) $election->get('protocol_version')->value,
      'election_uuid' => $election->electionUuid(),
      'ciphertext' => $ciphertext,
      'proof' => $proof_result['public_evidence'],
      'eligibility_evidence' => $eligibility_result['public_evidence'],
      'nullifier' => $eligibility_result['nullifier'],
      'accepted_at' => $this->time->getRequestTime(),
    ];
    $receipt = $this->receiptGenerator->generate($accepted_envelope);
    $ledger_record = $this->ledger->append($election->electionUuid(), 'accepted_ballot', $accepted_envelope + ['receipt' => $receipt]);

    $ballot = $this->entityTypeManager->getStorage('verifiable_voting_ballot_acceptance')->create([
      'election' => $election->id(),
      'election_uuid' => $election->electionUuid(),
      'protocol_version' => $accepted_envelope['protocol_version'],
      'ciphertext_json' => json_encode($ciphertext, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE),
      'proof_json' => json_encode($proof_result['public_evidence'], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE),
      'eligibility_evidence_json' => json_encode($eligibility_result['public_evidence'], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE),
      'nullifier' => $eligibility_result['nullifier'],
      'sequence' => $ledger_record['sequence'],
      'ledger_hash' => $ledger_record['record_hash'],
      'receipt' => $receipt,
      'accepted_at' => $accepted_envelope['accepted_at'],
    ]);
    $ballot->save();
    unset($transaction);

    $this->auditLogger->log('ballot_accepted', $election->electionUuid(), [
      'sequence' => $ledger_record['sequence'],
      'record_hash' => $ledger_record['record_hash'],
      'receipt' => $receipt,
      'provider' => $eligibility->id(),
    ]);
    return [
      'receipt' => $receipt,
      'display_receipt' => $this->receiptGenerator->format($receipt),
      'sequence' => $ledger_record['sequence'],
      'ledger_hash' => $ledger_record['record_hash'],
    ];
  }

  /**
   * Rejects ballot acceptance outside the open window or state.
   */
  private function assertElectionOpen(ElectionInterface $election): void {
    if ((string) $election->get('status')->value !== 'open') {
      throw new \DomainException('The election is not open for ballot acceptance.');
    }
    $now = $this->time->getRequestTime();
    $opens_at = (int) $election->get('opens_at')->value;
    $closes_at = (int) $election->get('closes_at')->value;
    if (($opens_at > 0 && $now < $opens_at) || ($closes_at > 0 && $now >= $closes_at)) {
      throw new \DomainException('The election is outside its configured voting window.');
    }
  }

  /**
   * Returns active choices in deterministic public order.
   *
   * @return array<int, \Drupal\Core\Entity\ContentEntityInterface>
   *   Choice entities.
   */
  private function activeChoices(ElectionInterface $election): array {
    $storage = $this->entityTypeManager->getStorage('verifiable_voting_choice');
    $ids = $storage->getQuery()->accessCheck(FALSE)
      ->condition('election', $election->id())
      ->condition('active', TRUE)
      ->sort('weight')
      ->sort('uuid')
      ->execute();
    return $storage->loadMultiple($ids);
  }

  /**
   * Extracts provider configuration from a map field.
   *
   * @return array<string, mixed>
   *   Configuration map.
   */
  private function configuration(ElectionInterface $election, string $field_name): array {
    $item = $election->get($field_name)->first();
    return $item === NULL ? [] : $item->getValue();
  }

}
