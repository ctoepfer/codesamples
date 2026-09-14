<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Entity;

use Drupal\Core\Entity\ContentEntityBase;
use Drupal\Core\Entity\EntityStorageException;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * Stores an accepted encrypted ballot without voter identity fields.
 *
 * This entity deliberately has no Drupal user, IP address, session, request,
 * display name, or other identity-bearing field. Deployments must still manage
 * web-server, proxy, analytics, and support-system metadata separately.
 *
 * @ContentEntityType(
 *   id = "verifiable_voting_ballot_acceptance",
 *   label = @Translation("Accepted ballot"),
 *   label_collection = @Translation("Accepted ballots"),
 *   handlers = {
 *     "list_builder" = "Drupal\verifiable_voting\Entity\ListBuilder\BallotAcceptanceListBuilder",
 *     "access" = "Drupal\Core\Entity\EntityAccessControlHandler"
 *   },
 *   base_table = "verifiable_voting_ballot_acceptance",
 *   data_table = "verifiable_voting_ballot_acceptance_field_data",
 *   admin_permission = "view verifiable voting security audit",
 *   entity_keys = {
 *     "id" = "id",
 *     "uuid" = "uuid",
 *     "label" = "receipt"
 *   }
 * )
 */
final class BallotAcceptance extends ContentEntityBase {

  /**
   * {@inheritdoc}
   */
  public function preSave($storage): void {
    if (!$this->isNew()) {
      throw new EntityStorageException('Accepted ballot records are immutable.');
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
    $fields['protocol_version'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Protocol version'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 64);
    $fields['ciphertext_json'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Encrypted ballot envelope'))
      ->setRequired(TRUE);
    $fields['proof_json'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Validity proof or verifier evidence'))
      ->setRequired(TRUE);
    $fields['eligibility_evidence_json'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Public eligibility evidence'))
      ->setRequired(TRUE);
    $fields['nullifier'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Election-scoped nullifier'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 128);
    $fields['sequence'] = BaseFieldDefinition::create('integer')
      ->setLabel(new TranslatableMarkup('Public ledger sequence'))
      ->setRequired(TRUE)
      ->setSetting('unsigned', TRUE);
    $fields['ledger_hash'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Ledger record hash'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 128);
    $fields['receipt'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Receipt digest'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 128);
    $fields['accepted_at'] = BaseFieldDefinition::create('timestamp')
      ->setLabel(new TranslatableMarkup('Accepted at'))
      ->setRequired(TRUE);
    return $fields;
  }

}
