<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\verifiable_voting\Contract\ProviderInterface;

/**
 * Selects tagged provider services by a stable provider identifier.
 */
final class ProviderRegistry {

  /**
   * @var array<string, \Drupal\verifiable_voting\Contract\ProviderInterface>
   */
  private array $providers = [];

  /**
   * Constructs a registry from Drupal tagged services.
   *
   * @param iterable<\Drupal\verifiable_voting\Contract\ProviderInterface> $providers
   *   Tagged providers.
   */
  public function __construct(iterable $providers) {
    foreach ($providers as $provider) {
      if (!$provider instanceof ProviderInterface) {
        throw new \LogicException('A tagged Verifiable Voting provider must implement ProviderInterface.');
      }
      if (isset($this->providers[$provider->id()])) {
        throw new \LogicException(sprintf('Duplicate Verifiable Voting provider id "%s".', $provider->id()));
      }
      $this->providers[$provider->id()] = $provider;
    }
  }

  /**
   * Returns a provider by its stored identifier.
   */
  public function get(string $id): ProviderInterface {
    if (!isset($this->providers[$id])) {
      throw new \InvalidArgumentException(sprintf('Unknown Verifiable Voting provider "%s".', $id));
    }
    return $this->providers[$id];
  }

  /**
   * Returns whether a provider is registered.
   */
  public function has(string $id): bool {
    return isset($this->providers[$id]);
  }

  /**
   * Returns provider labels for administration interfaces.
   *
   * @return array<string, string>
   *   Provider labels keyed by identifier.
   */
  public function options(): array {
    $options = [];
    foreach ($this->providers as $id => $provider) {
      $options[$id] = $provider->label();
    }
    return $options;
  }

}
