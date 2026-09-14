<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Form;

use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Form\FormBase;
use Drupal\Core\Form\FormStateInterface;
use Drupal\verifiable_voting\Entity\ElectionInterface;
use Drupal\verifiable_voting\Service\BallotIntakeService;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Collects one approval ballot without persisting identity-bearing fields.
 */
final class BallotCastForm extends FormBase implements ContainerInjectionInterface {

  /**
   * Constructs the casting form.
   */
  public function __construct(
    private readonly BallotIntakeService $ballotIntake,
    private readonly EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container): self {
    return new self(
      $container->get('verifiable_voting.ballot_intake'),
      $container->get('entity_type.manager'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId(): string {
    return 'verifiable_voting_ballot_cast';
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state, ?ElectionInterface $verifiable_voting_election = NULL): array {
    if (!$verifiable_voting_election instanceof ElectionInterface) {
      throw new \LogicException('Election route parameter is missing.');
    }
    if ((string) $verifiable_voting_election->get('status')->value !== 'open') {
      $form['message'] = ['#markup' => $this->t('This election is not open for ballot acceptance.')];
      return $form;
    }
    $choices = $this->entityTypeManager->getStorage('verifiable_voting_choice')->getQuery()
      ->accessCheck(TRUE)
      ->condition('election', $verifiable_voting_election->id())
      ->condition('active', TRUE)
      ->sort('weight')
      ->sort('uuid')
      ->execute();
    $options = [];
    foreach ($this->entityTypeManager->getStorage('verifiable_voting_choice')->loadMultiple($choices) as $choice) {
      $options[(string) $choice->uuid()] = $choice->label();
    }
    $maximum = (int) ($verifiable_voting_election->get('ballot_definition')->max_selections ?? 1);
    $form['privacy_notice'] = [
      '#type' => 'item',
      '#title' => $this->t('Important privacy and verification notice'),
      '#markup' => $this->t('The reference profile accepts a server-validated encrypted ballot. Its receipt can show inclusion in the published ledger, but it does not prove that this device represented your intent, prevent coercion, or provide anonymous credentials or end-to-end ballot secrecy.'),
    ];
    $form['selections'] = [
      '#type' => 'checkboxes',
      '#title' => $this->t('Select up to @maximum option(s)', ['@maximum' => $maximum]),
      '#options' => $options,
      '#required' => TRUE,
    ];
    $form['credential_token'] = [
      '#type' => 'password',
      '#title' => $this->t('Election credential'),
      '#description' => $this->t('This value is used only for eligibility verification and is not stored with the accepted ballot.'),
      '#required' => TRUE,
      '#autocomplete' => 'off',
    ];
    $form['election_id'] = ['#type' => 'hidden', '#value' => $verifiable_voting_election->id()];
    $form['actions']['submit'] = ['#type' => 'submit', '#value' => $this->t('Cast ballot')];
    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function validateForm(array &$form, FormStateInterface $form_state): void {
    $election = $this->electionFromState($form_state);
    $selected = array_values(array_filter($form_state->getValue('selections'), static fn($value): bool => $value !== 0 && $value !== '0' && $value !== ''));
    $maximum = (int) ($election->get('ballot_definition')->max_selections ?? 1);
    if (count($selected) < 1 || count($selected) > $maximum) {
      $form_state->setErrorByName('selections', $this->t('Select between one and @maximum options.', ['@maximum' => $maximum]));
    }
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state): void {
    $election = $this->electionFromState($form_state);
    $selections = array_values(array_filter($form_state->getValue('selections'), static fn($value): bool => is_string($value) && $value !== ''));
    try {
      $result = $this->ballotIntake->accept($election, ['selections' => $selections], ['token' => (string) $form_state->getValue('credential_token')]);
      $this->messenger()->addStatus($this->t('Your ballot was accepted. Save this receipt: @receipt', ['@receipt' => $result['display_receipt']]));
      $this->messenger()->addStatus($this->t('Receipt lookup URL: @url', ['@url' => '/voting/election/' . $election->id() . '/receipt/' . $result['receipt']]));
    }
    catch (\Throwable) {
      $this->messenger()->addError($this->t('The ballot was not accepted. Do not assume a ballot was cast; consult the public ledger or contact an election administrator through an approved channel.'));
    }
    $form_state->setRedirect('verifiable_voting.ledger', ['verifiable_voting_election' => $election->id()]);
  }

  /**
   * Retrieves the entity chosen by the route-hidden form value.
   */
  private function electionFromState(FormStateInterface $form_state): ElectionInterface {
    $election = $this->entityTypeManager->getStorage('verifiable_voting_election')->load((int) $form_state->getValue('election_id'));
    if (!$election instanceof ElectionInterface) {
      throw new \LogicException('Election is unavailable.');
    }
    return $election;
  }

}
