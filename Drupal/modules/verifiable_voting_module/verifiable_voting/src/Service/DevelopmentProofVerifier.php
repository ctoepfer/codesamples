<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\verifiable_voting\Contract\ProofVerifierInterface;

/**
 * Reference verifier for server-validated pre-encryption ballots.
 *
 * This is not a zero-knowledge proof verifier. The intake service validates
 * canonical plaintext before invoking encryption, so this provider proves only
 * that a structurally valid ciphertext envelope was accepted by this server.
 */
final class DevelopmentProofVerifier implements ProofVerifierInterface {

  /**
   * {@inheritdoc}
   */
  public function id(): string {
    return 'development_proof';
  }

  /**
   * {@inheritdoc}
   */
  public function label(): string {
    return 'Development server-validated ballot envelope';
  }

  /**
   * {@inheritdoc}
   */
  public function validateConfiguration(array $configuration): array {
    return [];
  }

  /**
   * {@inheritdoc}
   */
  public function verify(string $election_uuid, array $ciphertext, array $proof, array $configuration): array {
    $valid = isset($ciphertext['algorithm'], $ciphertext['nonce'], $ciphertext['ciphertext'])
      && is_string($ciphertext['algorithm'])
      && is_string($ciphertext['nonce'])
      && is_string($ciphertext['ciphertext']);
    return [
      'valid' => $valid,
      'public_evidence' => $valid ? [
        'provider' => $this->id(),
        'profile' => 'server-validated-pre-encryption',
        'warning' => 'This is not a zero-knowledge ballot-validity proof.',
      ] : [],
      'reason_code' => $valid ? 'accepted' : 'malformed_ciphertext',
    ];
  }

}
