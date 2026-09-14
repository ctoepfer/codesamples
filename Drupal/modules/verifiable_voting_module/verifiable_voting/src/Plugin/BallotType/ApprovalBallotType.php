<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Plugin\BallotType;

use Drupal\Core\Plugin\PluginBase;
use Drupal\verifiable_voting\Contract\BallotTypeInterface;

/**
 * Provides a bounded approval / choose-up-to-N ballot.
 *
 * @BallotType(
 *   id = "approval",
 *   label = @Translation("Approval / choose up to N")
 * )
 */
final class ApprovalBallotType extends PluginBase implements BallotTypeInterface {

  /**
   * {@inheritdoc}
   */
  public function id(): string {
    return (string) $this->pluginId;
  }

  /**
   * {@inheritdoc}
   */
  public function label(): string {
    return (string) $this->pluginDefinition['label'];
  }

  /**
   * {@inheritdoc}
   */
  public function validateDefinition(array $definition, array $choices): array {
    $errors = [];
    $maximum = $definition['max_selections'] ?? NULL;
    if (!is_int($maximum) && !(is_string($maximum) && ctype_digit($maximum))) {
      $errors[] = 'The maximum number of selections must be a positive integer.';
      return $errors;
    }
    $maximum = (int) $maximum;
    if ($maximum < 1) {
      $errors[] = 'The maximum number of selections must be at least one.';
    }
    if (count($choices) < 2) {
      $errors[] = 'At least two active choices are required.';
    }
    if ($maximum > count($choices)) {
      $errors[] = 'The maximum number of selections cannot exceed the active choice count.';
    }
    return $errors;
  }

  /**
   * {@inheritdoc}
   */
  public function canonicalizePlaintextBallot(array $ballot, array $allowed_choice_uuids, array $definition): array {
    $selections = $ballot['selections'] ?? NULL;
    if (!is_array($selections) || array_is_list($selections) === FALSE) {
      throw new \InvalidArgumentException('Ballot selections must be a JSON array.');
    }
    $selections = array_values($selections);
    if (count($selections) === 0) {
      throw new \InvalidArgumentException('At least one choice must be selected.');
    }
    $maximum = (int) ($definition['max_selections'] ?? 0);
    if ($maximum < 1 || count($selections) > $maximum) {
      throw new \InvalidArgumentException('Ballot selection count violates the election rule.');
    }
    foreach ($selections as $selection) {
      if (!is_string($selection) || !in_array($selection, $allowed_choice_uuids, TRUE)) {
        throw new \InvalidArgumentException('Ballot contains an unknown choice identifier.');
      }
    }
    if (count(array_unique($selections, SORT_STRING)) !== count($selections)) {
      throw new \InvalidArgumentException('Ballot may not select a choice more than once.');
    }
    sort($selections, SORT_STRING);
    return ['selections' => $selections];
  }

  /**
   * {@inheritdoc}
   */
  public function getPublicRules(array $definition): array {
    return [
      'kind' => 'approval',
      'max_selections' => (int) ($definition['max_selections'] ?? 0),
      'minimum_selections' => 1,
    ];
  }

}
