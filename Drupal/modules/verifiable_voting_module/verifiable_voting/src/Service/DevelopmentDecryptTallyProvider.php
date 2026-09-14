<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\verifiable_voting\Contract\EncryptionProviderInterface;
use Drupal\verifiable_voting\Contract\TallyProviderInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;

/**
 * Development-only trusted-server tally provider.
 *
 * It decrypts individual ballots and therefore must never be deployed as a
 * claim of end-to-end secrecy, threshold decryption, or homomorphic tallying.
 */
final class DevelopmentDecryptTallyProvider implements TallyProviderInterface {

  /**
   * Constructs the provider.
   */
  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly ProviderRegistry $encryptionRegistry,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function id(): string {
    return 'development_decrypt_tally';
  }

  /**
   * {@inheritdoc}
   */
  public function label(): string {
    return 'Development trusted-server decrypt-and-tally';
  }

  /**
   * {@inheritdoc}
   */
  public function validateConfiguration(array $configuration): array {
    return [];
  }

  /**
   * {@inheritdoc}
   */
  public function tally(ElectionInterface $election): array {
    $provider = $this->encryptionRegistry->get((string) $election->get('encryption_provider')->value);
    if (!$provider instanceof EncryptionProviderInterface) {
      throw new \LogicException('Selected encryption provider cannot decrypt development ballots.');
    }
    $ballot_ids = $this->entityTypeManager->getStorage('verifiable_voting_ballot_acceptance')->getQuery()
      ->accessCheck(FALSE)
      ->condition('election', $election->id())
      ->sort('sequence')
      ->execute();
    $ballots = $this->entityTypeManager->getStorage('verifiable_voting_ballot_acceptance')->loadMultiple($ballot_ids);
    $totals = [];
    foreach ($ballots as $ballot) {
      $ciphertext = json_decode((string) $ballot->get('ciphertext_json')->value, TRUE, 512, JSON_THROW_ON_ERROR);
      $plaintext = $provider->decrypt($election->electionUuid(), $ciphertext, $this->configuration($election, 'encryption_configuration'));
      foreach ($plaintext['selections'] ?? [] as $choice_uuid) {
        if (!is_string($choice_uuid)) {
          throw new \UnexpectedValueException('Decrypted ballot has a non-string choice identifier.');
        }
        $totals[$choice_uuid] = ($totals[$choice_uuid] ?? 0) + 1;
      }
    }
    ksort($totals, SORT_STRING);
    return [
      'protocol_version' => 'verifiable-voting/1',
      'provider' => $this->id(),
      'profile' => 'development-trusted-server',
      'warning' => 'Individual ballots were decrypted by the tally provider. This is not a privacy-preserving production tally.',
      'election_uuid' => $election->electionUuid(),
      'accepted_ballot_count' => count($ballots),
      'totals' => $totals,
    ];
  }

  /**
   * Extracts provider configuration from a map field.
   *
   * @return array<string, mixed>
   *   Configuration map.
   */
  private function configuration(ElectionInterface $election, string $field_name): array {
    $item = $election->get($field_name)->first();
    return $item === NULL ? [] : $item->getValue();
  }

}
