<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Entity;

use Drupal\Core\Entity\ContentEntityInterface;

/**
 * Defines the election entity contract.
 */
interface ElectionInterface extends ContentEntityInterface {

  /**
   * Returns the allowed lifecycle states in canonical order.
   *
   * @return string[]
   *   State identifiers.
   */
  public static function lifecycleStates(): array;

  /**
   * Returns whether the election has reached or passed a lifecycle state.
   */
  public function isAtLeast(string $state): bool;

  /**
   * Returns the immutable election UUID used in cryptographic namespaces.
   */
  public function electionUuid(): string;

  /**
   * Returns the frozen public manifest, if one exists.
   *
   * @return array<string, mixed>
   *   Public manifest fields.
   */
  public function publicManifest(): array;

}
