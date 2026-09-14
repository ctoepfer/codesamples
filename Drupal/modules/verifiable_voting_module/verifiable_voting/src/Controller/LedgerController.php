<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\JsonResponse;

/**
 * Publishes minimal public ledger and receipt-inclusion views.
 */
final class LedgerController extends ControllerBase {

  /**
   * Constructs the controller.
   */
  public function __construct(private readonly EntityTypeManagerInterface $entityTypeManager) {}

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container): self {
    return new self($container->get('entity_type.manager'));
  }

  /**
   * Returns public ledger evidence in deterministic sequence order.
   */
  public function view(ElectionInterface $verifiable_voting_election): JsonResponse {
    $storage = $this->entityTypeManager->getStorage('verifiable_voting_ledger_entry');
    $ids = $storage->getQuery()->accessCheck(FALSE)
      ->condition('election_uuid', $verifiable_voting_election->electionUuid())
      ->sort('sequence')
      ->execute();
    $entries = [];
    foreach ($storage->loadMultiple($ids) as $entry) {
      $record = json_decode((string) $entry->get('record_json')->value, TRUE, 512, JSON_THROW_ON_ERROR);
      $entries[] = $record + [
        'previous_hash' => (string) $entry->get('previous_hash')->value,
        'record_hash' => (string) $entry->get('record_hash')->value,
      ];
    }
    $response = new JsonResponse([
      'protocol_version' => 'verifiable-voting/1',
      'election_uuid' => $verifiable_voting_election->electionUuid(),
      'manifest_hash' => (string) $verifiable_voting_election->get('manifest_hash')->value,
      'final_ledger_root' => (string) $verifiable_voting_election->get('ledger_final_root')->value,
      'entries' => $entries,
    ]);
    $response->headers->set('Cache-Control', 'no-store');
    return $response;
  }

  /**
   * Returns the public evidence associated with one receipt digest.
   */
  public function receipt(ElectionInterface $verifiable_voting_election, string $receipt): JsonResponse {
    $storage = $this->entityTypeManager->getStorage('verifiable_voting_ballot_acceptance');
    $ids = $storage->getQuery()->accessCheck(FALSE)
      ->condition('election', $verifiable_voting_election->id())
      ->condition('receipt', $receipt)
      ->range(0, 1)
      ->execute();
    if ($ids === []) {
      return new JsonResponse(['receipt' => $receipt, 'found' => FALSE], 404);
    }
    $ballot = $storage->load(reset($ids));
    $response = new JsonResponse([
      'found' => TRUE,
      'election_uuid' => $verifiable_voting_election->electionUuid(),
      'receipt' => $receipt,
      'sequence' => (int) $ballot->get('sequence')->value,
      'ledger_hash' => (string) $ballot->get('ledger_hash')->value,
      'message' => 'This proves only that the receipt is present in this published application ledger. It does not prove cast-as-intended, secrecy, coercion resistance, or a correct tally.',
    ]);
    $response->headers->set('Cache-Control', 'no-store');
    return $response;
  }

}
