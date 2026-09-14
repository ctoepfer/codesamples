<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Entity;

use Drupal\Core\Entity\ContentEntityBase;
use Drupal\Core\Entity\EntityChangedTrait;
use Drupal\Core\Entity\EntityStorageException;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * Stores a stable, domain-neutral option for an election.
 *
 * @ContentEntityType(
 *   id = "verifiable_voting_choice",
 *   label = @Translation("Choice"),
 *   label_collection = @Translation("Choices"),
 *   handlers = {
 *     "list_builder" = "Drupal\verifiable_voting\Entity\ListBuilder\ChoiceListBuilder",
 *     "form" = {
 *       "add" = "Drupal\verifiable_voting\Form\ChoiceForm",
 *       "edit" = "Drupal\verifiable_voting\Form\ChoiceForm",
 *       "delete" = "Drupal\Core\Entity\ContentEntityDeleteForm"
 *     },
 *     "access" = "Drupal\Core\Entity\EntityAccessControlHandler"
 *   },
 *   base_table = "verifiable_voting_choice",
 *   data_table = "verifiable_voting_choice_field_data",
 *   admin_permission = "administer verifiable voting",
 *   entity_keys = {
 *     "id" = "id",
 *     "uuid" = "uuid",
 *     "label" = "label"
 *   },
 *   links = {
 *     "canonical" = "/admin/config/verifiable-voting/choices/{verifiable_voting_choice}",
 *     "add-form" = "/admin/config/verifiable-voting/elections/{verifiable_voting_election}/choices/add",
 *     "edit-form" = "/admin/config/verifiable-voting/choices/{verifiable_voting_choice}/edit",
 *     "delete-form" = "/admin/config/verifiable-voting/choices/{verifiable_voting_choice}/delete"
 *   }
 * )
 */
final class Choice extends ContentEntityBase implements ChoiceInterface {

  use EntityChangedTrait;

  /**
   * {@inheritdoc}
   */
  public function electionId(): int {
    return (int) $this->get('election')->target_id;
  }

  /**
   * {@inheritdoc}
   */
  public function choiceUuid(): string {
    return (string) $this->uuid();
  }

  /**
   * {@inheritdoc}
   */
  public function preSave($storage): void {
    parent::preSave($storage);
    if ($this->isNew() || !$this->original instanceof self) {
      return;
    }
    $election = \Drupal::entityTypeManager()->getStorage('verifiable_voting_election')->load($this->electionId());
    if (!$election instanceof ElectionInterface || !$election->isAtLeast('open')) {
      return;
    }
    foreach (['election', 'label', 'stable_id', 'description', 'weight', 'active', 'metadata'] as $field_name) {
      if (!$this->get($field_name)->equals($this->original->get($field_name))) {
        throw new EntityStorageException('Choice data is immutable after its election opens. Create a new election to change the voting definition.');
      }
    }
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
    $fields['label'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Display label'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 255)
      ->setDisplayOptions('form', ['type' => 'string_textfield', 'weight' => -10])
      ->setDisplayConfigurable('form', TRUE);
    $fields['stable_id'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Stable internal identifier'))
      ->setDescription(new TranslatableMarkup('Frozen with the election definition.'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 128)
      ->addConstraint('Regex', ['pattern' => '/^[a-z][a-z0-9_]*$/'])
      ->setDisplayOptions('form', ['type' => 'string_textfield', 'weight' => -9])
      ->setDisplayConfigurable('form', TRUE);
    $fields['description'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Description'))
      ->setDisplayOptions('form', ['type' => 'string_textarea', 'weight' => -8])
      ->setDisplayConfigurable('form', TRUE);
    $fields['weight'] = BaseFieldDefinition::create('integer')
      ->setLabel(new TranslatableMarkup('Display order'))
      ->setDefaultValue(0)
      ->setDisplayOptions('form', ['type' => 'number', 'weight' => -7])
      ->setDisplayConfigurable('form', TRUE);
    $fields['active'] = BaseFieldDefinition::create('boolean')
      ->setLabel(new TranslatableMarkup('Active'))
      ->setDefaultValue(TRUE)
      ->setDisplayOptions('form', ['type' => 'boolean_checkbox', 'weight' => -6])
      ->setDisplayConfigurable('form', TRUE);
    $fields['metadata'] = BaseFieldDefinition::create('map')
      ->setLabel(new TranslatableMarkup('Optional metadata'));
    $fields['created'] = BaseFieldDefinition::create('created')->setLabel(new TranslatableMarkup('Created'));
    $fields['changed'] = BaseFieldDefinition::create('changed')->setLabel(new TranslatableMarkup('Changed'));
    return $fields;
  }

}
