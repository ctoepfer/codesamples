<?php

namespace Drupal\commerce_usio\PluginForm\Usio;

use Drupal\commerce_payment\PluginForm\PaymentMethodAddForm as BasePaymentMethodAddForm;
use Drupal\Core\Cache\CacheableMetadata;
use Drupal\Core\Form\FormStateInterface;

/**
 * Provides the USIO payment method form using Checkout.js.
 *
 * The USIO Checkout.js library renders an embedded iframe that collects card
 * details on USIO's servers. When the user submits the iframe form, USIO
 * posts a one-time token back to this page via window.postMessage. Our JS
 * captures that token, stores it in a hidden field, and re-submits the Drupal
 * form so Commerce can call createPaymentMethod() with the token.
 */
class PaymentMethodAddForm extends BasePaymentMethodAddForm {

  /**
   * {@inheritdoc}
   */
  protected function buildCreditCardForm(array $element, FormStateInterface $form_state): array {
    /** @var \Drupal\commerce_usio\Plugin\Commerce\PaymentGateway\UsioGateway $plugin */
    $plugin = $this->plugin;

    $element['#attributes']['class'][] = 'usio-payment-form';

    // Container that USIO Checkout.js mounts its iframe into.
    $element['usio_checkout_container'] = [
      '#type'       => 'container',
      '#attributes' => [
        'id'              => 'usio-checkout-container',
        'aria-label'      => $this->t('Secure card payment form'),
        'aria-live'       => 'polite',
        'role'            => 'region',
      ],
    ];

    // Accessible error region.
    $element['payment_errors'] = [
      '#type'       => 'markup',
      '#markup'     => '<div id="usio-payment-errors" class="messages messages--error" role="alert" aria-live="assertive" aria-atomic="true" hidden></div>',
      '#weight'     => -200,
      '#allowed_tags' => ['div'],
    ];

    // Hidden fields populated by JS after the token arrives via postMessage.
    $element['usio_token'] = [
      '#type'       => 'hidden',
      '#attributes' => ['id' => 'usio-token'],
    ];
    $element['usio_card_type'] = [
      '#type'       => 'hidden',
      '#attributes' => ['id' => 'usio-card-type'],
    ];
    $element['usio_last4'] = [
      '#type'       => 'hidden',
      '#attributes' => ['id' => 'usio-last4'],
    ];
    $element['usio_exp_month'] = [
      '#type'       => 'hidden',
      '#attributes' => ['id' => 'usio-exp-month'],
    ];
    $element['usio_exp_year'] = [
      '#type'       => 'hidden',
      '#attributes' => ['id' => 'usio-exp-year'],
    ];

    // Load the USIO Checkout.js from the correct environment.
    $mode    = $plugin->getMode();
    $js_lib  = ($mode === 'live') ? 'commerce_usio/checkout_js_production' : 'commerce_usio/checkout_js_sandbox';
    $element['#attached']['library'][] = $js_lib;
    $element['#attached']['library'][] = 'commerce_usio/form';

    $element['#attached']['drupalSettings']['commerceUsio'] = [
      'merchantKey' => $plugin->getMerchantKey(),
      'mode'        => $mode,
    ];

    // Prevent caching — the token is unique per session.
    $cacheability = new CacheableMetadata();
    $cacheability->addCacheableDependency($this->entity);
    $cacheability->setCacheMaxAge(0);
    $cacheability->applyTo($element);

    return $element;
  }

  /**
   * {@inheritdoc}
   */
  protected function validateCreditCardForm(array &$element, FormStateInterface $form_state): void {
    $values = $form_state->getValue($element['#parents']);
    if (empty($values['usio_token'])) {
      $form_state->setError(
        $element,
        $this->t('Payment could not be processed. Please complete the card form and try again.')
      );
    }
  }

  /**
   * {@inheritdoc}
   */
  public function submitCreditCardForm(array $element, FormStateInterface $form_state): void {
    // Token capture is handled by JS + the hidden field; nothing extra needed.
  }

}
