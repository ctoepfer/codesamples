<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

use Drupal\verifiable_voting\Entity\ElectionInterface;

/**
 * Produces a versioned tally artifact from accepted ballots.
 */
interface TallyProviderInterface extends ProviderInterface {

  /**
   * Tallies an election without coupling ballot storage to tally rules.
   *
   * @return array<string, mixed>
   *   Versioned tally artifact suitable for ledger commitment.
   */
  public function tally(ElectionInterface $election): array;

}
