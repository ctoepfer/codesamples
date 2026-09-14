<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Form;

use Drupal\Core\Entity\ContentEntityForm;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Datetime\DrupalDateTime;
use Drupal\verifiable_voting\Entity\ElectionInterface;

/**
 * Creates and edits security-reviewed election definitions.
 */
final class ElectionForm extends ContentEntityForm {

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state): array {
    /** @var \Drupal\verifiable_voting\Entity\ElectionInterface $election */
    $election = $this->entity;
    $locked = $election->isAtLeast('open');

    $form['warning'] = [
      '#type' => 'status_messages',
      '#weight' => -100,
    ];
    $form['scope'] = [
      '#type' => 'item',
      '#title' => $this->t('Security boundary'),
      '#markup' => $this->t('The bundled providers are a development and trusted-server reference profile. They do not provide anonymous credentials, end-to-end ballot secrecy, coercion resistance, or independently verifiable zero-knowledge proofs.'),
      '#weight' => -99,
    ];
    $form['title'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Title'),
      '#required' => TRUE,
      '#default_value' => $election->label(),
      '#disabled' => $locked,
    ];
    $form['machine_name'] = [
      '#type' => 'machine_name',
      '#title' => $this->t('Machine name'),
      '#required' => TRUE,
      '#default_value' => $election->get('machine_name')->value,
      '#machine_name' => ['exists' => [$this, 'machineNameExists']],
      '#disabled' => $locked,
    ];
    $form['description'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Description'),
      '#default_value' => $election->get('description')->value,
      '#disabled' => $locked,
    ];
    $form['opens_at'] = [
      '#type' => 'datetime',
      '#title' => $this->t('Scheduled opening (UTC)'),
      '#default_value' => $election->get('opens_at')->value ? DrupalDateTime::createFromTimestamp((int) $election->get('opens_at')->value) : NULL,
      '#disabled' => $locked,
    ];
    $form['closes_at'] = [
      '#type' => 'datetime',
      '#title' => $this->t('Scheduled closing (UTC)'),
      '#default_value' => $election->get('closes_at')->value ? DrupalDateTime::createFromTimestamp((int) $election->get('closes_at')->value) : NULL,
      '#disabled' => $locked,
    ];
    $form['ballot_type'] = [
      '#type' => 'select',
      '#title' => $this->t('Ballot type'),
      '#options' => ['approval' => $this->t('Approval / choose up to N')],
      '#default_value' => $election->get('ballot_type')->value ?: 'approval',
      '#disabled' => $locked,
    ];
    $form['max_selections'] = [
      '#type' => 'number',
      '#title' => $this->t('Maximum selections'),
      '#min' => 1,
      '#required' => TRUE,
      '#default_value' => $election->get('ballot_definition')->max_selections ?? 1,
      '#disabled' => $locked,
    ];
    foreach ([
      'eligibility_provider' => 'development_credential',
      'proof_provider' => 'development_proof',
      'encryption_provider' => 'development_xchacha20poly1305',
      'signature_provider' => 'development_ed25519',
      'tally_provider' => 'development_decrypt_tally',
    ] as $field => $default) {
      $form[$field] = [
        '#type' => 'hidden',
        '#value' => $election->get($field)->value ?: $default,
      ];
    }
    $eligibility_configuration = $election->get('eligibility_configuration')->first()?->getValue() ?? [];
    $encryption_configuration = $election->get('encryption_configuration')->first()?->getValue() ?? [];
    $signature_configuration = $election->get('signature_configuration')->first()?->getValue() ?? [];
    $form['credential_token_hashes'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Development credential token SHA-256 digests'),
      '#description' => $this->t('Enter one lowercase hexadecimal SHA-256 digest per line. Plaintext credentials are never stored in the election definition or ballot records.'),
      '#default_value' => implode("\n", $eligibility_configuration['accepted_token_hashes'] ?? []),
      '#disabled' => $locked,
    ];
    $form['encryption_key_id'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Development encryption key identifier'),
      '#description' => $this->t('This public label identifies the environment-provided key. It is not secret key material.'),
      '#default_value' => $encryption_configuration['key_id'] ?? 'development-ballot-key',
      '#disabled' => $locked,
    ];
    $form['signature_key_id'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Development signing key identifier'),
      '#description' => $this->t('This public label identifies the environment-provided signing key. It is not secret key material.'),
      '#default_value' => $signature_configuration['key_id'] ?? 'development-ed25519',
      '#disabled' => $locked,
    ];

    return parent::buildForm($form, $form_state);
  }

  /**
   * Checks machine-name uniqueness among election records.
   */
  public function machineNameExists(string $machine_name): bool {
    $query = $this->entityTypeManager->getStorage('verifiable_voting_election')->getQuery()->accessCheck(FALSE);
    $query->condition('machine_name', $machine_name);
    if (!$this->entity->isNew()) {
      $query->condition('id', $this->entity->id(), '<>');
    }
    return (bool) $query->count()->execute();
  }

  /**
   * {@inheritdoc}
   */
  public function validateForm(array &$form, FormStateInterface $form_state): void {
    parent::validateForm($form, $form_state);
    $open = $form_state->getValue('opens_at');
    $close = $form_state->getValue('closes_at');
    if ($open instanceof DrupalDateTime && $close instanceof DrupalDateTime && $close->getTimestamp() <= $open->getTimestamp()) {
      $form_state->setErrorByName('closes_at', $this->t('Closing time must be later than opening time.'));
    }
    $hashes = preg_split('/\R/', trim((string) $form_state->getValue('credential_token_hashes'))) ?: [];
    foreach ($hashes as $hash) {
      if (!preg_match('/^[a-f0-9]{64}$/D', trim($hash))) {
        $form_state->setErrorByName('credential_token_hashes', $this->t('Each development credential digest must be a lowercase hexadecimal SHA-256 value.'));
        break;
      }
    }
  }

  /**
   * {@inheritdoc}
   */
  public function save(array $form, FormStateInterface $form_state): int {
    /** @var \Drupal\verifiable_voting\Entity\ElectionInterface $election */
    $election = $this->entity;
    if (!$election->isAtLeast('open')) {
      $election->set('title', $form_state->getValue('title'));
      $election->set('machine_name', $form_state->getValue('machine_name'));
      $election->set('description', $form_state->getValue('description'));
      foreach (['opens_at', 'closes_at'] as $field) {
        $value = $form_state->getValue($field);
        $election->set($field, $value instanceof DrupalDateTime ? $value->getTimestamp() : NULL);
      }
      $election->set('ballot_type', $form_state->getValue('ballot_type'));
      $election->set('ballot_definition', ['max_selections' => (int) $form_state->getValue('max_selections')]);
      foreach (['eligibility_provider', 'proof_provider', 'encryption_provider', 'signature_provider', 'tally_provider'] as $field) {
        $election->set($field, $form_state->getValue($field));
      }
      $hashes = preg_split('/\R/', trim((string) $form_state->getValue('credential_token_hashes'))) ?: [];
      $election->set('eligibility_configuration', ['accepted_token_hashes' => array_values(array_filter(array_map('trim', $hashes)))]);
      $election->set('proof_configuration', []);
      $election->set('encryption_configuration', ['key_id' => (string) $form_state->getValue('encryption_key_id')]);
      $election->set('signature_configuration', ['key_id' => (string) $form_state->getValue('signature_key_id')]);
      $election->set('tally_configuration', []);
    }
    $result = $election->save();
    $this->messenger()->addStatus($this->t('Election %title has been saved.', ['%title' => $election->label()]));
    $form_state->setRedirectUrl($election->toUrl('collection'));
    return $result;
  }

}
