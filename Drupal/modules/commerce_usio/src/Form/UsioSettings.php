<?php

namespace Drupal\commerce_usio\Form;

use Drupal\Core\Form\ConfigFormBase;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Url;

/**
 * Global settings page for the Commerce USIO module.
 *
 * Per-gateway credentials are configured on each payment gateway entity at
 * /admin/commerce/config/payment-gateways. This page only exists as an
 * administrative landing point and for any future global settings.
 */
class UsioSettings extends ConfigFormBase {

  /**
   * {@inheritdoc}
   */
  public function getFormId(): string {
    return 'commerce_usio_settings';
  }

  /**
   * {@inheritdoc}
   */
  protected function getEditableConfigNames(): array {
    return ['commerce_usio.settings'];
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state): array {
    $gateways_url = Url::fromRoute('entity.commerce_payment_gateway.collection')->toString();

    $form['info'] = [
      '#type'   => 'markup',
      '#markup' => '<p>' . $this->t(
        'USIO gateway credentials (Merchant ID, Login, Password, Merchant Key) are configured per gateway instance at <a href=":url">Commerce &rsaquo; Payment gateways</a>.',
        [':url' => $gateways_url]
      ) . '</p>',
    ];

    return parent::buildForm($form, $form_state);
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state): void {
    parent::submitForm($form, $form_state);
  }

}
