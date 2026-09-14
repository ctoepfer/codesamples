<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Entity;

use Drupal\Core\Entity\ContentEntityBase;
use Drupal\Core\Entity\EntityChangedTrait;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * Stores one independent election and its frozen cryptographic configuration.
 *
 * @ContentEntityType(
 *   id = "verifiable_voting_election",
 *   label = @Translation("Election"),
 *   label_collection = @Translation("Elections"),
 *   handlers = {
 *     "list_builder" = "Drupal\verifiable_voting\Entity\ListBuilder\ElectionListBuilder",
 *     "form" = {
 *       "add" = "Drupal\verifiable_voting\Form\ElectionForm",
 *       "edit" = "Drupal\verifiable_voting\Form\ElectionForm",
 *       "delete" = "Drupal\Core\Entity\ContentEntityDeleteForm"
 *     },
 *     "access" = "Drupal\Core\Entity\EntityAccessControlHandler"
 *   },
 *   base_table = "verifiable_voting_election",
 *   data_table = "verifiable_voting_election_field_data",
 *   admin_permission = "administer verifiable voting",
 *   entity_keys = {
 *     "id" = "id",
 *     "uuid" = "uuid",
 *     "label" = "title"
 *   },
 *   links = {
 *     "canonical" = "/admin/config/verifiable-voting/elections/{verifiable_voting_election}",
 *     "add-form" = "/admin/config/verifiable-voting/elections/add",
 *     "edit-form" = "/admin/config/verifiable-voting/elections/{verifiable_voting_election}/edit",
 *     "delete-form" = "/admin/config/verifiable-voting/elections/{verifiable_voting_election}/delete",
 *     "collection" = "/admin/config/verifiable-voting/elections"
 *   }
 * )
 */
final class Election extends ContentEntityBase implements ElectionInterface {

  use EntityChangedTrait;

  /**
   * {@inheritdoc}
   */
  public static function lifecycleStates(): array {
    return [
      'draft',
      'configured',
      'open',
      'closed',
      'tallying',
      'certified',
      'archived',
      'invalidated',
    ];
  }

  /**
   * {@inheritdoc}
   */
  public function isAtLeast(string $state): bool {
    $positions = array_flip(self::lifecycleStates());
    $current = (string) $this->get('status')->value;
    return isset($positions[$state], $positions[$current]) && $positions[$current] >= $positions[$state];
  }

  /**
   * {@inheritdoc}
   */
  public function electionUuid(): string {
    return (string) $this->uuid();
  }

  /**
   * {@inheritdoc}
   */
  public function publicManifest(): array {
    $json = (string) $this->get('manifest_json')->value;
    if ($json === '') {
      return [];
    }
    $manifest = json_decode($json, TRUE, 512, JSON_THROW_ON_ERROR);
    return is_array($manifest) ? $manifest : [];
  }

  /**
   * {@inheritdoc}
   */
  public function preSave($storage): void {
    parent::preSave($storage);
    if ($this->isNew() || !$this->original instanceof self || !$this->original->isAtLeast('open')) {
      return;
    }
    $frozen_fields = [
      'title', 'machine_name', 'description', 'protocol_version', 'opens_at', 'closes_at',
      'ballot_type', 'eligibility_provider', 'proof_provider', 'encryption_provider',
      'signature_provider', 'tally_provider', 'ballot_definition',
      'eligibility_configuration', 'proof_configuration', 'encryption_configuration',
      'signature_configuration', 'tally_configuration', 'manifest_json', 'manifest_hash',
    ];
    foreach ($frozen_fields as $field_name) {
      if (!$this->get($field_name)->equals($this->original->get($field_name))) {
        throw new \LogicException('Security-relevant election configuration is immutable after opening. Create a new election or use the explicit invalidation process.');
      }
    }
  }

  /**
   * {@inheritdoc}
   */
  public static function baseFieldDefinitions(EntityTypeInterface $entity_type): array {
    $fields = parent::baseFieldDefinitions($entity_type);

    $fields['title'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Title'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 255)
      ->setDisplayOptions('form', ['type' => 'string_textfield', 'weight' => -10])
      ->setDisplayConfigurable('form', TRUE);

    $fields['machine_name'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Machine name'))
      ->setDescription(new TranslatableMarkup('Stable administrative slug. It is frozen when the election opens.'))
      ->setRequired(TRUE)
      ->setSetting('max_length', 64)
      ->addConstraint('Regex', ['pattern' => '/^[a-z][a-z0-9_]*$/'])
      ->setDisplayOptions('form', ['type' => 'string_textfield', 'weight' => -9])
      ->setDisplayConfigurable('form', TRUE);

    $fields['description'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Description'))
      ->setDisplayOptions('form', ['type' => 'string_textarea', 'weight' => -8])
      ->setDisplayConfigurable('form', TRUE);

    $fields['protocol_version'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Protocol version'))
      ->setRequired(TRUE)
      ->setDefaultValue('verifiable-voting/1')
      ->setSetting('max_length', 64);

    $fields['status'] = BaseFieldDefinition::create('list_string')
      ->setLabel(new TranslatableMarkup('Lifecycle status'))
      ->setRequired(TRUE)
      ->setDefaultValue('draft')
      ->setSetting('allowed_values', array_combine(self::lifecycleStates(), self::lifecycleStates()));

    $fields['opens_at'] = BaseFieldDefinition::create('timestamp')
      ->setLabel(new TranslatableMarkup('Opens at'))
      ->setDescription(new TranslatableMarkup('Optional scheduled opening time, expressed as UTC.'))
      ->setDisplayOptions('form', ['type' => 'datetime_timestamp', 'weight' => 10])
      ->setDisplayConfigurable('form', TRUE);

    $fields['closes_at'] = BaseFieldDefinition::create('timestamp')
      ->setLabel(new TranslatableMarkup('Closes at'))
      ->setDescription(new TranslatableMarkup('Optional scheduled closing time, expressed as UTC.'))
      ->setDisplayOptions('form', ['type' => 'datetime_timestamp', 'weight' => 11])
      ->setDisplayConfigurable('form', TRUE);

    foreach ([
      'ballot_type' => 'Ballot type',
      'eligibility_provider' => 'Eligibility provider',
      'proof_provider' => 'Proof verifier',
      'encryption_provider' => 'Encryption provider',
      'signature_provider' => 'Signature provider',
      'tally_provider' => 'Tally provider',
    ] as $field_name => $label) {
      $fields[$field_name] = BaseFieldDefinition::create('string')
        ->setLabel(new TranslatableMarkup($label))
        ->setRequired(TRUE)
        ->setSetting('max_length', 128);
    }

    foreach ([
      'ballot_definition' => 'Ballot definition',
      'eligibility_configuration' => 'Eligibility configuration',
      'proof_configuration' => 'Proof verifier configuration',
      'encryption_configuration' => 'Encryption configuration',
      'signature_configuration' => 'Signature configuration',
      'tally_configuration' => 'Tally configuration',
    ] as $field_name => $label) {
      $fields[$field_name] = BaseFieldDefinition::create('map')
        ->setLabel(new TranslatableMarkup($label));
    }

    $fields['manifest_json'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Frozen canonical election manifest'));
    $fields['manifest_hash'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Frozen manifest hash'))
      ->setSetting('max_length', 128);
    $fields['ledger_final_root'] = BaseFieldDefinition::create('string')
      ->setLabel(new TranslatableMarkup('Final ledger root'))
      ->setSetting('max_length', 128);
    $fields['final_tally'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Final tally artifact'));
    $fields['certified_at'] = BaseFieldDefinition::create('timestamp')
      ->setLabel(new TranslatableMarkup('Certified at'));
    $fields['certification_signature'] = BaseFieldDefinition::create('string_long')
      ->setLabel(new TranslatableMarkup('Certification signature'));

    $fields['created'] = BaseFieldDefinition::create('created')
      ->setLabel(new TranslatableMarkup('Created'));
    $fields['changed'] = BaseFieldDefinition::create('changed')
      ->setLabel(new TranslatableMarkup('Changed'));

    return $fields;
  }

}
