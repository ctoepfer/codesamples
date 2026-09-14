<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\verifiable_voting\Contract\EligibilityProviderInterface;

/**
 * Development-only opaque-token eligibility provider.
 *
 * Tokens are checked against configured SHA-256 digests. The provider returns
 * an election-scoped nullifier, not the token or a user identity. This does not
 * provide anonymous credentials or unlinkability from the token issuer.
 */
final class DevelopmentCredentialEligibilityProvider implements EligibilityProviderInterface {

  /**
   * {@inheritdoc}
   */
  public function id(): string {
    return 'development_credential';
  }

  /**
   * {@inheritdoc}
   */
  public function label(): string {
    return 'Development opaque credential token';
  }

  /**
   * {@inheritdoc}
   */
  public function validateConfiguration(array $configuration): array {
    $hashes = $configuration['accepted_token_hashes'] ?? [];
    if (!is_array($hashes) || $hashes === []) {
      return ['At least one SHA-256 credential-token digest must be configured for the development provider.'];
    }
    foreach ($hashes as $hash) {
      if (!is_string($hash) || !preg_match('/^[a-f0-9]{64}$/D', $hash)) {
        return ['Development credential digests must be lowercase hexadecimal SHA-256 values.'];
      }
    }
    return [];
  }

  /**
   * {@inheritdoc}
   */
  public function verify(string $election_uuid, array $credential, array $configuration): array {
    $token = $credential['token'] ?? NULL;
    if (!is_string($token) || $token === '') {
      return ['accepted' => FALSE, 'nullifier' => '', 'public_evidence' => [], 'reason_code' => 'missing_credential'];
    }
    $token_hash = hash('sha256', $token);
    $accepted = FALSE;
    foreach ($configuration['accepted_token_hashes'] ?? [] as $accepted_hash) {
      if (is_string($accepted_hash) && hash_equals($accepted_hash, $token_hash)) {
        $accepted = TRUE;
      }
    }
    sodium_memzero($token);
    if (!$accepted) {
      return ['accepted' => FALSE, 'nullifier' => '', 'public_evidence' => [], 'reason_code' => 'ineligible_credential'];
    }
    $nullifier = sodium_bin2base64(
      hash('sha256', "verifiable-voting/development-nullifier/v1\x00" . $election_uuid . "\x00" . $token_hash, TRUE),
      SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING,
    );
    return [
      'accepted' => TRUE,
      'nullifier' => $nullifier,
      'public_evidence' => ['provider' => $this->id(), 'profile' => 'development-non-anonymous'],
      'reason_code' => 'accepted',
    ];
  }

}
