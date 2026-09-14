<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Form;

use Drupal\Core\Entity\ContentEntityForm;
use Drupal\Core\Form\FormStateInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;

/**
 * Creates and edits choices before an election is opened.
 */
final class ChoiceForm extends ContentEntityForm {

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state): array {
    $choice = $this->entity;
    $election = $choice->get('election')->entity;
    $locked = $election instanceof ElectionInterface && $election->isAtLeast('open');
    $form['election'] = [
      '#type' => 'entity_autocomplete',
      '#title' => $this->t('Election'),
      '#target_type' => 'verifiable_voting_election',
      '#default_value' => $election,
      '#required' => TRUE,
      '#disabled' => $locked,
    ];
    $form['label'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Display label'),
      '#default_value' => $choice->get('label')->value,
      '#required' => TRUE,
      '#disabled' => $locked,
    ];
    $form['stable_id'] = [
      '#type' => 'machine_name',
      '#title' => $this->t('Stable internal identifier'),
      '#default_value' => $choice->get('stable_id')->value,
      '#required' => TRUE,
      '#disabled' => $locked,
      '#machine_name' => ['exists' => [$this, 'stableIdExists']],
    ];
    $form['description'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Description'),
      '#default_value' => $choice->get('description')->value,
      '#disabled' => $locked,
    ];
    $form['weight'] = [
      '#type' => 'number',
      '#title' => $this->t('Display order'),
      '#default_value' => $choice->get('weight')->value,
      '#disabled' => $locked,
    ];
    $form['active'] = [
      '#type' => 'checkbox',
      '#title' => $this->t('Active'),
      '#default_value' => $choice->get('active')->value,
      '#disabled' => $locked,
    ];
    return parent::buildForm($form, $form_state);
  }

  /**
   * Checks stable identifiers within an election.
   */
  public function stableIdExists(string $stable_id): bool {
    $query = $this->entityTypeManager->getStorage('verifiable_voting_choice')->getQuery()->accessCheck(FALSE);
    $query->condition('stable_id', $stable_id);
    if (!$this->entity->isNew()) {
      $query->condition('id', $this->entity->id(), '<>');
    }
    return (bool) $query->count()->execute();
  }

  /**
   * {@inheritdoc}
   */
  public function save(array $form, FormStateInterface $form_state): int {
    $choice = $this->entity;
    $choice->set('election', $form_state->getValue('election'));
    $choice->set('label', $form_state->getValue('label'));
    $choice->set('stable_id', $form_state->getValue('stable_id'));
    $choice->set('description', $form_state->getValue('description'));
    $choice->set('weight', (int) $form_state->getValue('weight'));
    $choice->set('active', (bool) $form_state->getValue('active'));
    $result = $choice->save();
    $this->messenger()->addStatus($this->t('Choice %label has been saved.', ['%label' => $choice->label()]));
    $form_state->setRedirect('entity.verifiable_voting_election.collection');
    return $result;
  }

}
