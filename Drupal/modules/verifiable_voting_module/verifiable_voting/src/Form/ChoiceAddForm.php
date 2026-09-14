<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Form;

use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Form\FormBase;
use Drupal\Core\Form\FormStateInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Adds a stable choice to one election before voting opens.
 */
final class ChoiceAddForm extends FormBase implements ContainerInjectionInterface {

  /**
   * Constructs the add form.
   */
  public function __construct(private readonly EntityTypeManagerInterface $entityTypeManager) {}

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container): self {
    return new self($container->get('entity_type.manager'));
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId(): string {
    return 'verifiable_voting_choice_add';
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state, ?ElectionInterface $verifiable_voting_election = NULL): array {
    if (!$verifiable_voting_election instanceof ElectionInterface) {
      throw new \LogicException('Election route parameter is missing.');
    }
    if ($verifiable_voting_election->isAtLeast('open')) {
      $form['message'] = ['#markup' => $this->t('Choices are immutable after an election opens.')];
      return $form;
    }
    $form['label'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Display label'),
      '#required' => TRUE,
    ];
    $form['stable_id'] = [
      '#type' => 'machine_name',
      '#title' => $this->t('Stable internal identifier'),
      '#required' => TRUE,
      '#machine_name' => ['exists' => [$this, 'stableIdExists']],
    ];
    $form['description'] = ['#type' => 'textarea', '#title' => $this->t('Description')];
    $form['weight'] = ['#type' => 'number', '#title' => $this->t('Display order'), '#default_value' => 0];
    $form['active'] = ['#type' => 'checkbox', '#title' => $this->t('Active'), '#default_value' => TRUE];
    $form['election_id'] = ['#type' => 'hidden', '#value' => $verifiable_voting_election->id()];
    $form['actions']['submit'] = ['#type' => 'submit', '#value' => $this->t('Add choice')];
    return $form;
  }

  /**
   * Checks uniqueness within the election selected by the route form.
   */
  public function stableIdExists(string $stable_id): bool {
    $election = $this->getRouteMatch()->getParameter('verifiable_voting_election');
    if (!$election instanceof ElectionInterface) {
      return TRUE;
    }
    return (bool) $this->entityTypeManager->getStorage('verifiable_voting_choice')->getQuery()
      ->accessCheck(FALSE)
      ->condition('election', $election->id())
      ->condition('stable_id', $stable_id)
      ->count()
      ->execute();
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state): void {
    $election = $this->entityTypeManager->getStorage('verifiable_voting_election')->load((int) $form_state->getValue('election_id'));
    if (!$election instanceof ElectionInterface || $election->isAtLeast('open')) {
      throw new \DomainException('Choices cannot be added to this election.');
    }
    $choice = $this->entityTypeManager->getStorage('verifiable_voting_choice')->create([
      'election' => $election->id(),
      'label' => $form_state->getValue('label'),
      'stable_id' => $form_state->getValue('stable_id'),
      'description' => $form_state->getValue('description'),
      'weight' => (int) $form_state->getValue('weight'),
      'active' => (bool) $form_state->getValue('active'),
    ]);
    $choice->save();
    $this->messenger()->addStatus($this->t('Choice %label was added.', ['%label' => $choice->label()]));
    $form_state->setRedirect('entity.verifiable_voting_election.collection');
  }

}
