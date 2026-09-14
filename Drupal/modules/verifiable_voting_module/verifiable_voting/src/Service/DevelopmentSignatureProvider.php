<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\verifiable_voting\Contract\SignatureProviderInterface;

/**
 * Development-only Ed25519 signer using an environment-provided private key.
 *
 * This provider intentionally refuses to read private keys from Drupal
 * configuration or content entities. Production deployments must replace it
 * with a provider backed by governed key custody or an external signer.
 */
final class DevelopmentSignatureProvider implements SignatureProviderInterface {

  /**
   * {@inheritdoc}
   */
  public function id(): string {
    return 'development_ed25519';
  }

  /**
   * {@inheritdoc}
   */
  public function label(): string {
    return 'Development Ed25519 signer (environment secret only)';
  }

  /**
   * {@inheritdoc}
   */
  public function validateConfiguration(array $configuration): array {
    try {
      $this->secretKey();
    }
    catch (\RuntimeException) {
      return ['The development signing secret is missing or invalid.'];
    }
    return [];
  }

  /**
   * {@inheritdoc}
   */
  public function sign(string $message, array $configuration): string {
    return sodium_crypto_sign_detached($message, $this->secretKey());
  }

  /**
   * {@inheritdoc}
   */
  public function verify(string $message, string $signature, array $configuration): bool {
    return sodium_crypto_sign_verify_detached($signature, $message, $this->publicKey());
  }

  /**
   * {@inheritdoc}
   */
  public function publicMetadata(array $configuration): array {
    return [
      'algorithm' => 'Ed25519',
      'key_id' => (string) ($configuration['key_id'] ?? 'development-ed25519'),
      'public_key' => sodium_bin2base64($this->publicKey(), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING),
      'profile' => 'development-only',
    ];
  }

  /**
   * Returns the environment supplied Ed25519 secret key.
   */
  private function secretKey(): string {
    $encoded = getenv('VERIFIABLE_VOTING_DEVELOPMENT_SIGNING_SECRET_KEY');
    if (!is_string($encoded) || $encoded === '') {
      throw new \RuntimeException('VERIFIABLE_VOTING_DEVELOPMENT_SIGNING_SECRET_KEY is not set.');
    }
    try {
      $key = sodium_base642bin($encoded, SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
    }
    catch (\SodiumException $exception) {
      throw new \RuntimeException('Development signing secret is not valid base64url.', previous: $exception);
    }
    if (strlen($key) !== SODIUM_CRYPTO_SIGN_SECRETKEYBYTES) {
      throw new \RuntimeException('Development signing secret has an invalid length.');
    }
    return $key;
  }

  /**
   * Returns the public half of the development signing key.
   */
  private function publicKey(): string {
    return sodium_crypto_sign_publickey_from_secretkey($this->secretKey());
  }

}
