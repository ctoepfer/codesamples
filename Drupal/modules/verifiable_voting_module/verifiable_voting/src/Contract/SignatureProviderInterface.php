<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Signs and verifies versioned election artifacts.
 */
interface SignatureProviderInterface extends ProviderInterface {

  /**
   * Produces a detached signature over already canonical bytes.
   */
  public function sign(string $message, array $configuration): string;

  /**
   * Verifies a detached signature over already canonical bytes.
   */
  public function verify(string $message, string $signature, array $configuration): bool;

  /**
   * Returns safe public signing metadata.
   *
   * @return array<string, mixed>
   *   Public key metadata.
   */
  public function publicMetadata(array $configuration): array;

}
