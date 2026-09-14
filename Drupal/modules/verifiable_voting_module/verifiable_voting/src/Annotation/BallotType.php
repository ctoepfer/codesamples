<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Annotation;

use Drupal\Component\Annotation\Plugin;

/**
 * Defines a ballot-type plugin annotation.
 *
 * @Annotation
 */
final class BallotType extends Plugin {

  /**
   * The human-readable plugin label.
   *
   * @var string
   */
  public string $label = '';

}
