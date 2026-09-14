<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\verifiable_voting\Contract\CanonicalizerInterface;

/**
 * Derives stable receipt digests from accepted ballot envelopes.
 */
final class ReceiptGenerator {

  /**
   * Constructs a receipt generator.
   */
  public function __construct(private readonly CanonicalizerInterface $canonicalizer) {}

  /**
   * Derives a URL-safe SHA-256 receipt from the actual accepted envelope.
   *
   * @param array<string, mixed> $accepted_envelope
   *   Complete accepted envelope before its ledger fields are added.
   */
  public function generate(array $accepted_envelope): string {
    $bytes = $this->canonicalizer->canonicalize($accepted_envelope);
    return sodium_bin2base64(hash('sha256', $bytes, TRUE), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING);
  }

  /**
   * Formats a receipt for humans without changing the full verifier value.
   */
  public function format(string $receipt, int $group_size = 4): string {
    return implode('-', str_split($receipt, $group_size));
  }

}
