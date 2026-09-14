<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Form;

use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\Core\Form\ConfirmFormBase;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Url;
use Drupal\verifiable_voting\Entity\ElectionInterface;
use Drupal\verifiable_voting\Service\ElectionLifecycleManager;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Requires explicit confirmation for security-sensitive lifecycle changes.
 */
final class ElectionTransitionForm extends ConfirmFormBase implements ContainerInjectionInterface {

  /**
   * The lifecycle manager.
   */
  public function __construct(private readonly ElectionLifecycleManager $lifecycleManager) {}

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container): self {
    return new self($container->get('verifiable_voting.lifecycle_manager'));
  }

  /**
   * Provides a route title.
   */
  public function title(ElectionInterface $verifiable_voting_election, string $operation): string {
    return ucfirst($operation) . ': ' . $verifiable_voting_election->label();
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId(): string {
    return 'verifiable_voting_transition_confirmation';
  }

  /**
   * {@inheritdoc}
   */
  public function getQuestion(): string {
    return $this->t('Confirm @operation for %title?', [
      '@operation' => $this->operation(),
      '%title' => $this->election()->label(),
    ]);
  }

  /**
   * {@inheritdoc}
   */
  public function getDescription(): string {
    return $this->t('This lifecycle operation is security-sensitive. The action, current public ledger state, and result will be recorded without a voter-to-ballot linkage.');
  }

  /**
   * {@inheritdoc}
   */
  public function getConfirmText(): string {
    return $this->t('Confirm @operation', ['@operation' => $this->operation()]);
  }

  /**
   * {@inheritdoc}
   */
  public function getCancelUrl(): Url {
    return $this->election()->toUrl('collection');
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state, ?ElectionInterface $verifiable_voting_election = NULL, ?string $operation = NULL): array {
    return parent::buildForm($form, $form_state);
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state): void {
    try {
      $this->lifecycleManager->transition($this->election(), $this->operation());
      $this->messenger()->addStatus($this->t('Election lifecycle transition completed.'));
    }
    catch (\Throwable $exception) {
      $this->logger('verifiable_voting')->error('Election lifecycle transition failed: @message', ['@message' => $exception->getMessage()]);
      $this->messenger()->addError($this->t('The lifecycle transition was not completed. Review readiness and audit records.'));
    }
    $form_state->setRedirectUrl($this->election()->toUrl('collection'));
  }

  /**
   * Returns the route election.
   */
  private function election(): ElectionInterface {
    $election = $this->getRouteMatch()->getParameter('verifiable_voting_election');
    if (!$election instanceof ElectionInterface) {
      throw new \LogicException('Election route parameter is missing.');
    }
    return $election;
  }

  /**
   * Returns the route operation.
   */
  private function operation(): string {
    return (string) $this->getRouteMatch()->getParameter('operation');
  }

}
