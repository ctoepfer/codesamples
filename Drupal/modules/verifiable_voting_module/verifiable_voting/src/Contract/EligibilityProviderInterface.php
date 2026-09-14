<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Confirms an election-scoped eligible credential without accepting a ballot.
 */
interface EligibilityProviderInterface extends ProviderInterface {

  /**
   * Verifies an election-scoped credential assertion.
   *
   * Implementations must not return Drupal user identifiers or other identity
   * data that would be written to a public ballot or ledger record.
   *
   * @param string $election_uuid
   *   Immutable election UUID.
   * @param array<string, mixed> $credential
   *   Provider-specific credential assertion.
   * @param array<string, mixed> $configuration
   *   Frozen provider configuration.
   *
   * @return array{accepted: bool, nullifier: string, public_evidence: array<string, mixed>, reason_code: string}
   *   An election-scoped result. The nullifier must be nonempty only on success.
   */
  public function verify(string $election_uuid, array $credential, array $configuration): array;

}
