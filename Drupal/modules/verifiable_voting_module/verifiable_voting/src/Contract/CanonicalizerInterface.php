<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Produces deterministic bytes for protocol hashing and signing.
 */
interface CanonicalizerInterface {

  /**
   * Canonicalizes JSON-compatible structured data.
   *
   * @param array<string, mixed>|array<int, mixed> $data
   *   JSON-compatible data without unsupported values.
   */
  public function canonicalize(array $data): string;

}
