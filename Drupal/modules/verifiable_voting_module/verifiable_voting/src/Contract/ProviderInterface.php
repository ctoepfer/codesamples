<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Common contract for named, selectable Verifiable Voting providers.
 */
interface ProviderInterface {

  /**
   * Returns the stable provider identifier stored in election configuration.
   */
  public function id(): string;

  /**
   * Returns the administrator-facing provider label.
   */
  public function label(): string;

  /**
   * Returns non-sensitive configuration errors.
   *
   * @param array<string, mixed> $configuration
   *   Provider configuration.
   *
   * @return string[]
   *   Validation errors. An empty array means ready.
   */
  public function validateConfiguration(array $configuration): array;

}
