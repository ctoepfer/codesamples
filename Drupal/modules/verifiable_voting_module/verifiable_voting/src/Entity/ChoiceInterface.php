<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Entity;

use Drupal\Core\Entity\ContentEntityInterface;

/**
 * Defines a stable option available on a ballot.
 */
interface ChoiceInterface extends ContentEntityInterface {

  /**
   * Returns the election entity identifier.
   */
  public function electionId(): int;

  /**
   * Returns the immutable choice UUID used by ballot data.
   */
  public function choiceUuid(): string;

}
