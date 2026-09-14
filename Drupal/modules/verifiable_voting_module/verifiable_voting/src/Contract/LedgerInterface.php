<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Appends and verifies versioned public election evidence records.
 */
interface LedgerInterface {

  /**
   * Appends an evidence record to an election's ordered hash chain.
   *
   * @param string $election_uuid
   *   Immutable election UUID.
   * @param string $entry_type
   *   Protocol entry type.
   * @param array<string, mixed> $payload
   *   Public safe payload.
   *
   * @return array<string, mixed>
   *   The committed ledger record.
   */
  public function append(string $election_uuid, string $entry_type, array $payload): array;

  /**
   * Recomputes and verifies a complete election ledger.
   *
   * @return array{valid: bool, errors: string[], final_hash: string, count: int}
   *   Verification result.
   */
  public function verify(string $election_uuid): array;

}
