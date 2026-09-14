<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Creates encrypted ballot envelopes and exposes public cryptographic metadata.
 */
interface EncryptionProviderInterface extends ProviderInterface {

  /**
   * Encrypts a canonical plaintext ballot for one election.
   *
   * @param string $election_uuid
   *   Immutable election UUID.
   * @param array<string, mixed> $plaintext
   *   Canonical ballot representation.
   * @param array<string, mixed> $configuration
   *   Frozen provider configuration.
   *
   * @return array<string, mixed>
   *   Ciphertext envelope containing only safe public metadata and ciphertext.
   */
  public function encrypt(string $election_uuid, array $plaintext, array $configuration): array;

  /**
   * Decrypts a ballot only for a provider explicitly authorized to do so.
   *
   * This method exists for development and trusted-server reference profiles.
   * Production threshold or homomorphic providers must not expose individual
   * cast ballot plaintext to Drupal.
   *
   * @param string $election_uuid
   *   Immutable election UUID.
   * @param array<string, mixed> $ciphertext
   *   Ciphertext envelope.
   * @param array<string, mixed> $configuration
   *   Frozen provider configuration.
   *
   * @return array<string, mixed>
   *   Canonical plaintext ballot.
   */
  public function decrypt(string $election_uuid, array $ciphertext, array $configuration): array;

  /**
   * Returns public key and algorithm metadata for the audit package.
   *
   * @param array<string, mixed> $configuration
   *   Frozen provider configuration.
   *
   * @return array<string, mixed>
   *   Public metadata only.
   */
  public function publicMetadata(array $configuration): array;

}
