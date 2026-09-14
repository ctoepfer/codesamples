<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Verifies ballot well-formedness or external proof artifacts.
 */
interface ProofVerifierInterface extends ProviderInterface {

  /**
   * Verifies proof material against a ciphertext and frozen election context.
   *
   * @param string $election_uuid
   *   Immutable election UUID.
   * @param array<string, mixed> $ciphertext
   *   Encrypted ballot envelope.
   * @param array<string, mixed> $proof
   *   Proof material supplied by the cast flow.
   * @param array<string, mixed> $configuration
   *   Frozen provider configuration.
   *
   * @return array{valid: bool, public_evidence: array<string, mixed>, reason_code: string}
   *   Verification result. Evidence must be safe for publication.
   */
  public function verify(string $election_uuid, array $ciphertext, array $proof, array $configuration): array;

}
