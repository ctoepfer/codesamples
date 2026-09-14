<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Entity;

use Drupal\Core\Entity\ContentEntityBase;
use Drupal\Core\Entity\EntityStorageException;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * Stores one immutable public evidence record in an election hash chain.
 *
 * @ContentEntityType(
 *   id = "verifiable_voting_ledger_entry",
 *   label = @Translation("Ledger entry"),
 *   label_collection = @Translation("Ledger entries"),
 *   handlers = {
 *     "list_builder" = "Drupal\verifiable_voting\Entity\ListBuilder\LedgerEntryListBuilder",
 *     "access" = "Drupal\Core\Entity\EntityAccessControlHandler"
 *   },
 *   base_table = "verifiable_voting_ledger_entry",
 *   data_table = "verifiable_voting_ledger_entry_field_data",
 *   admin_permission = "view verifiable voting security audit",
 *   entity_keys = {
 *     "id" = "id",
 *     "uuid" = "uuid",
 *     "label" = "record_hash"
 *   }
 * )
 */
final class LedgerEntry extends ContentEntityBase {

  /**
   * {@inheritdoc}
   */
  public function preSave($storage): void {
    if (!$this->isNew()) {
      throw new EntityStorageException('Ledger entries are immutable. Append a new entry instead.');
    }
    parent::preSave($storage);
  }

  /**
   * {@inheritdoc}
   */
  public static function baseFieldDefinitions(EntityTypeInterface $entity_type): array {
    $fields = parent::baseFieldDefinitions($entity_type);
    $fields['election'] = BaseFieldDefinition::create('entity_reference')
      ->setLabel(new TranslatableMarkup('Election'))
      ->setRequired(TRUE)
      ->setSetting('target_type', 'verifiable_voting_election');
    $fields['election_uuid'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Election UUID'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 128);
    $fields['sequence'] = BaseFieldDefinition::create('integer')
      ->setLabel(new TranslatableMarkup('Sequence'))
      ->setRequired(TRUE)
      ->setSetting('unsigned', TRUE);
    $fields['entry_type'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Entry type'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 64);
    $fields['record_json'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Canonical public record'))
      ->setRequired(TRUE);
    $fields['previous_hash'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Previous record hash'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 128);
    $fields['record_hash'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Record hash'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 128);
    $fields['created'] = BaseFieldDefinition::create('created')
      ->setLabel(new TranslatableMarkup('Committed'));
    return $fields;
  }

}
