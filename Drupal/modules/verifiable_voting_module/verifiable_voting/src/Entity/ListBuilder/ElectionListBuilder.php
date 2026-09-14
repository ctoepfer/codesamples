<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Entity\ListBuilder;

use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Entity\EntityListBuilder;

/**
 * Lists election entities for the administration UI.
 */
final class ElectionListBuilder extends EntityListBuilder {

  /**
   * {@inheritdoc}
   */
  public function buildHeader(): array {
    return [
      'title' => $this->t('Election'),
      'status' => $this->t('Status'),
      'opens_at' => $this->t('Opens'),
      'closes_at' => $this->t('Closes'),
    ] + parent::buildHeader();
  }

  /**
   * {@inheritdoc}
   */
  public function buildRow(EntityInterface $entity): array {
    return [
      'title' => $entity->toLink(),
      'status' => $entity->get('status')->value,
      'opens_at' => $entity->get('opens_at')->value ?: $this->t('Not scheduled'),
      'closes_at' => $entity->get('closes_at')->value ?: $this->t('Not scheduled'),
    ] + parent::buildRow($entity);
  }

}
