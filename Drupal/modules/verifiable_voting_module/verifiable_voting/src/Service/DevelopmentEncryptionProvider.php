<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\verifiable_voting\Contract\CanonicalizerInterface;
use Drupal\verifiable_voting\Contract\EncryptionProviderInterface;

/**
 * Development-only trusted-server XChaCha20-Poly1305 ballot encryption.
 *
 * This provider protects a ballot at rest but its service can decrypt each
 * ballot. It is not an end-to-end, threshold, or homomorphic election scheme.
 */
final class DevelopmentEncryptionProvider implements EncryptionProviderInterface {

  /**
   * Constructs the provider.
   */
  public function __construct(private readonly CanonicalizerInterface $canonicalizer) {}

  /**
   * {@inheritdoc}
   */
  public function id(): string {
    return 'development_xchacha20poly1305';
  }

  /**
   * {@inheritdoc}
   */
  public function label(): string {
    return 'Development trusted-server XChaCha20-Poly1305';
  }

  /**
   * {@inheritdoc}
   */
  public function validateConfiguration(array $configuration): array {
    try {
      $this->key();
    }
    catch (\RuntimeException) {
      return ['The development ballot-encryption key is missing or invalid.'];
    }
    return [];
  }

  /**
   * {@inheritdoc}
   */
  public function encrypt(string $election_uuid, array $plaintext, array $configuration): array {
    $nonce = random_bytes(SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES);
    $aad = $this->aad($election_uuid);
    $payload = $this->canonicalizer->canonicalize([
      'protocol_version' => 'verifiable-voting/1',
      'election_uuid' => $election_uuid,
      'ballot' => $plaintext,
    ]);
    $ciphertext = sodium_crypto_aead_xchacha20poly1305_ietf_encrypt($payload, $aad, $nonce, $this->key());
    return [
      'algorithm' => 'XChaCha20-Poly1305-IETF',
      'key_id' => (string) ($configuration['key_id'] ?? 'development-ballot-key'),
      'nonce' => sodium_bin2base64($nonce, SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING),
      'ciphertext' => sodium_bin2base64($ciphertext, SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING),
      'aad_sha256' => sodium_bin2base64(hash('sha256', $aad, TRUE), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING),
      'profile' => 'development-trusted-server',
    ];
  }

  /**
   * {@inheritdoc}
   */
  public function decrypt(string $election_uuid, array $ciphertext, array $configuration): array {
    foreach (['nonce', 'ciphertext', 'algorithm'] as $field) {
      if (!is_string($ciphertext[$field] ?? NULL)) {
        throw new \InvalidArgumentException('Ciphertext envelope is malformed.');
      }
    }
    if ($ciphertext['algorithm'] !== 'XChaCha20-Poly1305-IETF') {
      throw new \InvalidArgumentException('Ciphertext algorithm is unsupported.');
    }
    try {
      $nonce = sodium_base642bin($ciphertext['nonce'], SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
      $encrypted = sodium_base642bin($ciphertext['ciphertext'], SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
      $payload = sodium_crypto_aead_xchacha20poly1305_ietf_decrypt($encrypted, $this->aad($election_uuid), $nonce, $this->key());
    }
    catch (\SodiumException $exception) {
      throw new \InvalidArgumentException('Ciphertext envelope contains invalid base64url data.', previous: $exception);
    }
    if ($payload === FALSE) {
      throw new \InvalidArgumentException('Ciphertext authentication failed.');
    }
    $decoded = json_decode($payload, TRUE, 512, JSON_THROW_ON_ERROR);
    if (!is_array($decoded) || ($decoded['election_uuid'] ?? NULL) !== $election_uuid || !is_array($decoded['ballot'] ?? NULL)) {
      throw new \InvalidArgumentException('Ciphertext payload does not match the election context.');
    }
    return $decoded['ballot'];
  }

  /**
   * {@inheritdoc}
   */
  public function publicMetadata(array $configuration): array {
    return [
      'algorithm' => 'XChaCha20-Poly1305-IETF',
      'key_id' => (string) ($configuration['key_id'] ?? 'development-ballot-key'),
      'profile' => 'development-trusted-server',
      'warning' => 'This provider permits server-side individual ballot decryption and is not an end-to-end election profile.',
    ];
  }

  /**
   * Returns the environment-supplied 256-bit AEAD key.
   */
  private function key(): string {
    $encoded = getenv('VERIFIABLE_VOTING_DEVELOPMENT_BALLOT_KEY');
    if (!is_string($encoded) || $encoded === '') {
      throw new \RuntimeException('VERIFIABLE_VOTING_DEVELOPMENT_BALLOT_KEY is not set.');
    }
    try {
      $key = sodium_base642bin($encoded, SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
    }
    catch (\SodiumException $exception) {
      throw new \RuntimeException('Development ballot-encryption key is not valid base64url.', previous: $exception);
    }
    if (strlen($key) !== SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_KEYBYTES) {
      throw new \RuntimeException('Development ballot-encryption key has an invalid length.');
    }
    return $key;
  }

  /**
   * Creates associated data that prevents election replay.
   */
  private function aad(string $election_uuid): string {
    return "verifiable-voting/1\x00" . $election_uuid;
  }

}
