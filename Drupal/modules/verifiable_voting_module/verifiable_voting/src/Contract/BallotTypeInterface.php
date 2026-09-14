<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Contract;

/**
 * Validates ballot definitions and plaintext selections before encryption.
 */
interface BallotTypeInterface {

  /**
   * Returns the stable ballot-type plugin identifier.
   */
  public function id(): string;

  /**
   * Returns the human-readable ballot-type label.
   */
  public function label(): string;

  /**
   * Validates election-level ballot configuration and frozen choices.
   *
   * @param array<string, mixed> $definition
   *   Ballot configuration.
   * @param array<int, array<string, mixed>> $choices
   *   Active choice definitions.
   *
   * @return string[]
   *   Errors, if any.
   */
  public function validateDefinition(array $definition, array $choices): array;

  /**
   * Validates and returns a canonical plaintext ballot representation.
   *
   * @param array<string, mixed> $ballot
   *   Untrusted plaintext ballot input.
   * @param array<int, string> $allowed_choice_uuids
   *   Frozen active choice UUIDs.
   * @param array<string, mixed> $definition
   *   Frozen ballot configuration.
   *
   * @return array<string, mixed>
   *   Canonical plaintext ballot.
   *
   * @throws \InvalidArgumentException
   *   Thrown when the ballot violates the election rules.
   */
  public function canonicalizePlaintextBallot(array $ballot, array $allowed_choice_uuids, array $definition): array;

  /**
   * Returns public, non-sensitive ballot rules.
   *
   * @param array<string, mixed> $definition
   *   Frozen ballot configuration.
   *
   * @return array<string, mixed>
   *   Public rules.
   */
  public function getPublicRules(array $definition): array;

}
