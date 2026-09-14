<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\Core\Database\Connection;
use Drupal\Core\Datetime\TimeInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Lock\LockBackendInterface;
use Drupal\verifiable_voting\Contract\CanonicalizerInterface;
use Drupal\verifiable_voting\Contract\LedgerInterface;

/**
 * Appends canonical public evidence to a per-election SHA-256 hash chain.
 */
final class HashChainLedger implements LedgerInterface {

  /**
   * Constructs a hash-chain ledger.
   */
  public function __construct(
    private readonly Connection $database,
    private readonly TimeInterface $time,
    private readonly LockBackendInterface $lock,
    private readonly CanonicalizerInterface $canonicalizer,
    private readonly EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function append(string $election_uuid, string $entry_type, array $payload): array {
    if (!preg_match('/^[a-z][a-z0-9_]{0,63}$/D', $entry_type)) {
      throw new \InvalidArgumentException('Ledger entry types must be stable lowercase identifiers.');
    }
    $lock_name = 'verifiable_voting:ledger:' . $election_uuid;
    if (!$this->lock->acquire($lock_name, 30.0)) {
      throw new \RuntimeException('Election ledger is busy. Retry the operation.');
    }
    try {
      $transaction = $this->database->startTransaction();
      $state = $this->loadOrCreateState($election_uuid);
      $sequence = (int) $state->next_sequence;
      $previous_hash = (string) $state->last_hash;
      $record = [
        'protocol_version' => 'verifiable-voting/1',
        'election_uuid' => $election_uuid,
        'sequence' => $sequence,
        'entry_type' => $entry_type,
        'timestamp' => $this->time->getRequestTime(),
        'payload' => $payload,
      ];
      $canonical_record = $this->canonicalizer->canonicalize($record);
      $record_hash = hash('sha256', "verifiable-voting/hash-chain/1\x00" . $previous_hash . $canonical_record, TRUE);
      $entry = $this->entityTypeManager->getStorage('verifiable_voting_ledger_entry')->create([
        'election_uuid' => $election_uuid,
        'sequence' => $sequence,
        'entry_type' => $entry_type,
        'record_json' => $canonical_record,
        'previous_hash' => $this->encode($previous_hash),
        'record_hash' => $this->encode($record_hash),
        'created' => $this->time->getRequestTime(),
      ]);
      $election = $this->entityTypeManager->getStorage('verifiable_voting_election')->loadByProperties(['uuid' => $election_uuid]);
      if ($election === []) {
        throw new \LogicException('Ledger append target election was not found.');
      }
      $entry->set('election', reset($election)->id());
      $entry->save();
      $this->database->update('verifiable_voting_ledger_state')->fields([
        'next_sequence' => $sequence + 1,
        'last_hash' => $record_hash,
        'updated' => $this->time->getRequestTime(),
      ])->condition('election_uuid', $election_uuid)->execute();
      unset($transaction);
      return $record + [
        'previous_hash' => $this->encode($previous_hash),
        'record_hash' => $this->encode($record_hash),
      ];
    }
    finally {
      $this->lock->release($lock_name);
    }
  }

  /**
   * {@inheritdoc}
   */
  public function verify(string $election_uuid): array {
    $ids = $this->entityTypeManager->getStorage('verifiable_voting_ledger_entry')->getQuery()
      ->accessCheck(FALSE)
      ->condition('election_uuid', $election_uuid)
      ->sort('sequence')
      ->execute();
    $entries = $this->entityTypeManager->getStorage('verifiable_voting_ledger_entry')->loadMultiple($ids);
    $previous_hash = str_repeat("\x00", 32);
    $expected_sequence = 1;
    $errors = [];
    foreach ($entries as $entry) {
      $sequence = (int) $entry->get('sequence')->value;
      if ($sequence !== $expected_sequence) {
        $errors[] = sprintf('Expected ledger sequence %d, found %d.', $expected_sequence, $sequence);
      }
      $stored_canonical = (string) $entry->get('record_json')->value;
      try {
        $record = json_decode($stored_canonical, TRUE, 512, JSON_THROW_ON_ERROR);
        if (!is_array($record) || $this->canonicalizer->canonicalize($record) !== $stored_canonical) {
          $errors[] = sprintf('Ledger sequence %d is not canonical JSON.', $sequence);
        }
      }
      catch (\Throwable) {
        $errors[] = sprintf('Ledger sequence %d cannot be decoded.', $sequence);
        $record = [];
      }
      $stored_previous = (string) $entry->get('previous_hash')->value;
      if (!hash_equals($this->encode($previous_hash), $stored_previous)) {
        $errors[] = sprintf('Ledger sequence %d has an invalid predecessor hash.', $sequence);
      }
      $calculated_hash = hash('sha256', "verifiable-voting/hash-chain/1\x00" . $previous_hash . $stored_canonical, TRUE);
      $stored_hash = (string) $entry->get('record_hash')->value;
      if (!hash_equals($this->encode($calculated_hash), $stored_hash)) {
        $errors[] = sprintf('Ledger sequence %d hash does not verify.', $sequence);
      }
      $previous_hash = $calculated_hash;
      $expected_sequence++;
    }
    return [
      'valid' => $errors === [],
      'errors' => $errors,
      'final_hash' => $this->encode($previous_hash),
      'count' => count($entries),
    ];
  }

  /**
   * Loads or creates durable state for a ledger while inside a transaction.
   */
  private function loadOrCreateState(string $election_uuid): object {
    $state = $this->database->select('verifiable_voting_ledger_state', 's')
      ->fields('s')
      ->condition('election_uuid', $election_uuid)
      ->forUpdate()
      ->execute()
      ->fetchObject();
    if ($state !== FALSE) {
      return $state;
    }
    $this->database->insert('verifiable_voting_ledger_state')->fields([
      'election_uuid' => $election_uuid,
      'next_sequence' => 1,
      'last_hash' => str_repeat("\x00", 32),
      'updated' => $this->time->getRequestTime(),
    ])->execute();
    return (object) [
      'next_sequence' => 1,
      'last_hash' => str_repeat("\x00", 32),
    ];
  }

  /**
   * Encodes binary public hashes as URL-safe base64 without padding.
   */
  private function encode(string $hash): string {
    return sodium_bin2base64($hash, SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
  }

}
