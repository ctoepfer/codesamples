<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\verifiable_voting\Contract\CanonicalizerInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;

/**
 * Produces portable, independently inspectable election evidence files.
 */
final class AuditExporter {

  /**
   * Constructs the exporter.
   */
  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly CanonicalizerInterface $canonicalizer,
  ) {}

  /**
   * Builds a stable file map for an audit package.
   *
   * @return array<string, string>
   *   Relative package filename to canonical JSON or UTF-8 text.
   */
  public function buildFiles(ElectionInterface $election): array {
    $manifest = $election->publicManifest();
    $storage = $this->entityTypeManager->getStorage('verifiable_voting_ledger_entry');
    $ids = $storage->getQuery()->accessCheck(FALSE)
      ->condition('election_uuid', $election->electionUuid())
      ->sort('sequence')
      ->execute();
    $entries = [];
    foreach ($storage->loadMultiple($ids) as $entry) {
      $entries[] = json_decode((string) $entry->get('record_json')->value, TRUE, 512, JSON_THROW_ON_ERROR) + [
        'previous_hash' => (string) $entry->get('previous_hash')->value,
        'record_hash' => (string) $entry->get('record_hash')->value,
      ];
    }
    $tally = (string) $election->get('final_tally')->value;
    $certification = [
      'protocol_version' => 'verifiable-voting/1',
      'election_uuid' => $election->electionUuid(),
      'status' => (string) $election->get('status')->value,
      'certified_at' => (int) $election->get('certified_at')->value,
      'signature' => (string) $election->get('certification_signature')->value,
      'final_ledger_root' => (string) $election->get('ledger_final_root')->value,
    ];
    return [
      'election.json' => $this->canonicalizer->canonicalize($manifest),
      'ledger.json' => $this->canonicalizer->canonicalize([
        'protocol_version' => 'verifiable-voting/1',
        'election_uuid' => $election->electionUuid(),
        'entries' => $entries,
      ]),
      'ledger-root.json' => $this->canonicalizer->canonicalize([
        'protocol_version' => 'verifiable-voting/1',
        'election_uuid' => $election->electionUuid(),
        'ledger_root' => (string) $election->get('ledger_final_root')->value,
        'manifest_hash' => (string) $election->get('manifest_hash')->value,
      ]),
      'tally.json' => $tally !== '' ? $tally : $this->canonicalizer->canonicalize([]),
      'certification.json' => $this->canonicalizer->canonicalize($certification),
      'README.txt' => "Verifiable Voting audit package\n\nThis package contains public evidence exported by the Drupal module. It is not by itself a claim of election certification, ballot secrecy, anonymous eligibility, cast-as-intended verification, coercion resistance, or independent tally verification. Recompute canonical hashes and verify the documented protocol profile before relying on an artifact.\n",
    ];
  }

}
