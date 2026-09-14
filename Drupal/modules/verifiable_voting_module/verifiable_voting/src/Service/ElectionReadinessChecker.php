<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\verifiable_voting\Contract\BallotTypeInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;
use Drupal\verifiable_voting\Plugin\BallotTypeManager;

/**
 * Evaluates security and configuration gates before an election may open.
 */
final class ElectionReadinessChecker {

  /**
   * Constructs the readiness checker.
   */
  public function __construct(
    private readonly BallotTypeManager $ballotTypeManager,
    private readonly ProviderRegistry $eligibilityRegistry,
    private readonly ProviderRegistry $proofRegistry,
    private readonly ProviderRegistry $encryptionRegistry,
    private readonly ProviderRegistry $signatureRegistry,
    private readonly EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * Runs all gates needed to open an election.
   *
   * @return array<int, array{id: string, passed: bool, message: string}>
   *   Ordered readiness checks.
   */
  public function check(ElectionInterface $election): array {
    $checks = [];
    $checks[] = $this->result('sodium', extension_loaded('sodium'), 'Native PHP ext-sodium is available.');
    $checks[] = $this->result('uuid', $election->electionUuid() !== '', 'Election UUID exists.');
    $checks[] = $this->result('machine_name', (string) $election->get('machine_name')->value !== '', 'Election machine name exists.');
    $open = (int) $election->get('opens_at')->value;
    $close = (int) $election->get('closes_at')->value;
    $checks[] = $this->result('dates', $open === 0 || $close === 0 || $close > $open, 'Opening and closing dates are coherent.');

    $choice_ids = $this->entityTypeManager->getStorage('verifiable_voting_choice')->getQuery()
      ->accessCheck(FALSE)
      ->condition('election', $election->id())
      ->condition('active', TRUE)
      ->sort('weight')
      ->sort('uuid')
      ->execute();
    $choices = $this->entityTypeManager->getStorage('verifiable_voting_choice')->loadMultiple($choice_ids);
    $checks[] = $this->result('choices', count($choices) >= 2, 'At least two active choices are configured.');
    $stable_ids = [];
    foreach ($choices as $choice) {
      $stable = (string) $choice->get('stable_id')->value;
      $stable_ids[] = $stable;
    }
    $checks[] = $this->result('choice_stable_ids', count($stable_ids) === count(array_unique($stable_ids)), 'Choice stable identifiers are unique.');

    $ballot_type = $this->ballotType($election, $checks);
    if ($ballot_type instanceof BallotTypeInterface) {
      foreach ($ballot_type->validateDefinition($this->configuration($election, 'ballot_definition'), $this->choiceDefinitionArray($choices)) as $error) {
        $checks[] = $this->result('ballot_definition', FALSE, $error);
      }
      $checks[] = $this->result('ballot_definition_valid', !array_filter($checks, static fn(array $check): bool => $check['id'] === 'ballot_definition' && !$check['passed']), 'Ballot definition validates against frozen choices.');
    }

    $this->checkProvider($checks, 'eligibility', $this->eligibilityRegistry, (string) $election->get('eligibility_provider')->value, $this->configuration($election, 'eligibility_configuration'));
    $this->checkProvider($checks, 'proof', $this->proofRegistry, (string) $election->get('proof_provider')->value, $this->configuration($election, 'proof_configuration'));
    $this->checkProvider($checks, 'encryption', $this->encryptionRegistry, (string) $election->get('encryption_provider')->value, $this->configuration($election, 'encryption_configuration'));
    $this->checkProvider($checks, 'signature', $this->signatureRegistry, (string) $election->get('signature_provider')->value, $this->configuration($election, 'signature_configuration'));

    return $checks;
  }

  /**
   * Returns whether every readiness check passed.
   */
  public function isReady(ElectionInterface $election): bool {
    foreach ($this->check($election) as $check) {
      if (!$check['passed']) {
        return FALSE;
      }
    }
    return TRUE;
  }

  /**
   * Checks the selected ballot type.
   *
   * @param array<int, array{id: string, passed: bool, message: string}> $checks
   *   Mutable check list.
   */
  private function ballotType(ElectionInterface $election, array &$checks): ?BallotTypeInterface {
    try {
      $plugin = $this->ballotTypeManager->createInstance((string) $election->get('ballot_type')->value);
      if (!$plugin instanceof BallotTypeInterface) {
        throw new \LogicException('Selected ballot plugin has an invalid contract.');
      }
      $checks[] = $this->result('ballot_type', TRUE, 'Selected ballot type is available.');
      return $plugin;
    }
    catch (\Throwable) {
      $checks[] = $this->result('ballot_type', FALSE, 'Selected ballot type is unavailable or invalid.');
      return NULL;
    }
  }

  /**
   * Adds a provider availability and configuration check.
   *
   * @param array<int, array{id: string, passed: bool, message: string}> $checks
   *   Mutable check list.
   */
  private function checkProvider(array &$checks, string $kind, ProviderRegistry $registry, string $provider_id, array $configuration): void {
    try {
      $provider = $registry->get($provider_id);
      $errors = $provider->validateConfiguration($configuration);
      $checks[] = $this->result($kind, $errors === [], $errors === [] ? sprintf('%s provider is ready.', ucfirst($kind)) : implode(' ', $errors));
    }
    catch (\Throwable) {
      $checks[] = $this->result($kind, FALSE, sprintf('%s provider is unavailable.', ucfirst($kind)));
    }
  }

  /**
   * Produces a standard readiness record.
   *
   * @return array{id: string, passed: bool, message: string}
   *   Readiness record.
   */
  private function result(string $id, bool $passed, string $message): array {
    return ['id' => $id, 'passed' => $passed, 'message' => $message];
  }

  /**
   * Extracts a map field into a plain array.
   *
   * @return array<string, mixed>
   *   Configuration map.
   */
  private function configuration(ElectionInterface $election, string $field_name): array {
    $item = $election->get($field_name)->first();
    if ($item === NULL) {
      return [];
    }
    $value = $item->getValue();
    return is_array($value) ? $value : [];
  }

  /**
   * @param array<int, \Drupal\Core\Entity\ContentEntityInterface> $choices
   *   Choice entities.
   *
   * @return array<int, array<string, mixed>>
   *   Choice definitions.
   */
  private function choiceDefinitionArray(array $choices): array {
    $definitions = [];
    foreach ($choices as $choice) {
      $definitions[] = ['uuid' => (string) $choice->uuid(), 'stable_id' => (string) $choice->get('stable_id')->value];
    }
    return $definitions;
  }

}
