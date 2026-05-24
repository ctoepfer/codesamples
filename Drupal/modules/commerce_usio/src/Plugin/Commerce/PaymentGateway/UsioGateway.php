<?php

namespace Drupal\commerce_usio\Plugin\Commerce\PaymentGateway;

use Drupal\commerce_payment\CreditCard;
use Drupal\commerce_payment\Entity\PaymentInterface;
use Drupal\commerce_payment\Entity\PaymentMethodInterface;
use Drupal\commerce_payment\Exception\HardDeclineException;
use Drupal\commerce_payment\Exception\InvalidRequestException;
use Drupal\commerce_payment\Exception\PaymentGatewayException;
use Drupal\commerce_payment\Plugin\Commerce\PaymentGateway\OnsitePaymentGatewayBase;
use Drupal\commerce_payment\Plugin\Commerce\PaymentGateway\SupportsCreatingPaymentMethodsInterface;
use Drupal\commerce_payment\Plugin\Commerce\PaymentGateway\SupportsRefundsInterface;
use Drupal\commerce_price\Price;
use Drupal\commerce_usio\UsioPhpSdk\Client;
use Drupal\Core\Form\FormStateInterface;
use GuzzleHttp\ClientInterface;
use Psr\Log\LoggerInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Provides the USIO onsite payment gateway.
 *
 * @CommercePaymentGateway(
 *   id = "usio_gateway",
 *   label = "USIO",
 *   display_label = "Credit / Debit Card (USIO)",
 *   forms = {
 *     "add-payment-method" = "Drupal\commerce_usio\PluginForm\Usio\PaymentMethodAddForm",
 *   },
 *   payment_method_types = {"credit_card"},
 *   credit_card_types = {
 *     "amex", "dinersclub", "discover", "jcb", "maestro", "mastercard", "visa",
 *   },
 *   requires_billing_information = TRUE,
 * )
 */
class UsioGateway extends OnsitePaymentGatewayBase implements SupportsCreatingPaymentMethodsInterface, SupportsRefundsInterface {

  /**
   * The HTTP client.
   *
   * @var \GuzzleHttp\ClientInterface
   */
  protected ClientInterface $httpClient;

  /**
   * The logger.
   *
   * @var \Psr\Log\LoggerInterface
   */
  protected LoggerInterface $logger;

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    $instance = parent::create($container, $configuration, $plugin_id, $plugin_definition);
    $instance->httpClient = $container->get('http_client');
    $instance->logger = $container->get('logger.channel.commerce_usio');
    return $instance;
  }

  // ---------------------------------------------------------------------------
  // Configuration
  // ---------------------------------------------------------------------------

  /**
   * {@inheritdoc}
   */
  public function defaultConfiguration(): array {
    return [
      'merchant_id'  => '',
      'login'        => '',
      'password'     => '',
      'merchant_key' => '',
      'terminal_id'  => '',
    ] + parent::defaultConfiguration();
  }

  /**
   * {@inheritdoc}
   */
  public function buildConfigurationForm(array $form, FormStateInterface $form_state): array {
    $form = parent::buildConfigurationForm($form, $form_state);

    $form['merchant_id'] = [
      '#type'          => 'textfield',
      '#title'         => $this->t('Merchant ID'),
      '#description'   => $this->t('Your USIO Merchant ID (e.g. 0000000001).'),
      '#default_value' => $this->configuration['merchant_id'],
      '#required'      => TRUE,
    ];

    $form['login'] = [
      '#type'          => 'textfield',
      '#title'         => $this->t('API Login / User ID'),
      '#description'   => $this->t('Your USIO API Login or User ID (e.g. API0000000001).'),
      '#default_value' => $this->configuration['login'],
      '#required'      => TRUE,
    ];

    $password_set = !empty($this->configuration['password']);
    $form['password'] = [
      '#type'        => 'password',
      '#title'       => $this->t('API Password'),
      '#description' => $password_set
        ? $this->t('A password is already stored. Leave blank to keep it, or enter a new value to replace it. <strong>Warning:</strong> this value is stored in the database. For production use, supply it via an environment variable (see README).')
        : $this->t('Your USIO API Password. <strong>Warning:</strong> stored in the database — use an environment variable for production.'),
    ];

    $form['merchant_key'] = [
      '#type'          => 'textfield',
      '#title'         => $this->t('Merchant Key (client-side)'),
      '#description'   => $this->t('Your USIO Merchant Key / ApiKey used to initialise Checkout.js on the client.'),
      '#default_value' => $this->configuration['merchant_key'],
      '#required'      => TRUE,
    ];

    $form['terminal_id'] = [
      '#type'          => 'textfield',
      '#title'         => $this->t('Terminal ID'),
      '#description'   => $this->t('Optional. Your USIO Terminal ID.'),
      '#default_value' => $this->configuration['terminal_id'],
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function submitConfigurationForm(array &$form, FormStateInterface $form_state): void {
    parent::submitConfigurationForm($form, $form_state);

    if (!$form_state->getErrors()) {
      $values = $form_state->getValue($form['#parents']);
      $this->configuration['merchant_id']  = $values['merchant_id'];
      $this->configuration['login']        = $values['login'];
      $this->configuration['merchant_key'] = $values['merchant_key'];
      $this->configuration['terminal_id']  = $values['terminal_id'];
      // Only overwrite the password when a new one is supplied.
      if (!empty($values['password'])) {
        $this->configuration['password'] = $values['password'];
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Stored payment methods (SupportsStoredPaymentMethodsInterface)
  // ---------------------------------------------------------------------------

  /**
   * {@inheritdoc}
   */
  public function createPaymentMethod(PaymentMethodInterface $payment_method, array $payment_details): void {
    $required = ['usio_token'];
    foreach ($required as $key) {
      if (empty($payment_details[$key])) {
        throw new InvalidRequestException(sprintf('$payment_details must contain the %s key.', $key));
      }
    }

    $token = $payment_details['usio_token'];

    // Store card display data when the JS passes it along.
    if (!empty($payment_details['usio_card_type'])) {
      $mapped = $this->mapCreditCardType($payment_details['usio_card_type']);
      $payment_method->set('card_type', $mapped);
    }
    if (!empty($payment_details['usio_last4'])) {
      $payment_method->set('card_number', $payment_details['usio_last4']);
    }
    if (!empty($payment_details['usio_exp_month']) && !empty($payment_details['usio_exp_year'])) {
      $payment_method->set('card_exp_month', $payment_details['usio_exp_month']);
      $payment_method->set('card_exp_year', $payment_details['usio_exp_year']);
      $expires = CreditCard::calculateExpirationTimestamp(
        $payment_details['usio_exp_month'],
        $payment_details['usio_exp_year']
      );
      $payment_method->setExpiresTime($expires);
    }

    $payment_method->setRemoteId($token);
    $payment_method->save();
  }

  /**
   * {@inheritdoc}
   */
  public function deletePaymentMethod(PaymentMethodInterface $payment_method): void {
    // USIO tokens are single-use; no remote deletion needed.
    $payment_method->delete();
  }

  // ---------------------------------------------------------------------------
  // Payment processing
  // ---------------------------------------------------------------------------

  /**
   * {@inheritdoc}
   */
  public function createPayment(PaymentInterface $payment, $capture = TRUE): void {
    $this->assertPaymentState($payment, ['new']);

    $payment_method = $payment->getPaymentMethod();
    if (!$payment_method instanceof PaymentMethodInterface) {
      throw new PaymentGatewayException('Payment method not found.');
    }

    $token = $payment_method->getRemoteId();
    if (empty($token)) {
      throw new InvalidRequestException('USIO payment token is missing from the payment method.');
    }

    $order   = $payment->getOrder();
    $amount  = number_format((float) $payment->getAmount()->getNumber(), 2, '.', '');

    $payload = [
      'Token'  => $token,
      'Amount' => $amount,
    ];

    // Attach billing profile fields required by USIO.
    $billing_profile = $order->getBillingProfile();
    if ($billing_profile && !$billing_profile->get('address')->isEmpty()) {
      /** @var \Drupal\address\Plugin\Field\FieldType\AddressItem $address */
      $address = $billing_profile->get('address')->first();
      $payload['FirstName'] = $address->getGivenName();
      $payload['LastName']  = $address->getFamilyName();
      $payload['Address1']  = $address->getAddressLine1();
      if ($address->getAddressLine2()) {
        $payload['Address2'] = $address->getAddressLine2();
      }
      $payload['City']    = $address->getLocality();
      $payload['State']   = $address->getAdministrativeArea();
      $payload['Zip']     = $address->getPostalCode();
      $payload['Country'] = $address->getCountryCode();
    }

    // Attach customer email if available.
    $owner = $order->getCustomer();
    if ($owner && $owner->isAuthenticated()) {
      $payload['EmailAddress'] = $owner->getEmail();
    }

    $client   = $this->getUsioClient();
    $response = $client->submitTokenPayment($payload);

    if (!$response) {
      throw new PaymentGatewayException('No response received from the USIO payment gateway.');
    }

    $status = strtolower($response['Status'] ?? '');

    if ($status !== 'success') {
      $message = $this->mapErrorCode($response['Message'] ?? '');
      $this->logger->warning('USIO payment failed for order @order: @msg', [
        '@order' => $order->id(),
        '@msg'   => $message,
      ]);
      throw HardDeclineException::createForPayment($payment, $message);
    }

    $payment->setRemoteId($response['Confirmation'] ?? '');
    $payment->setRemoteState($response['Status']);
    $payment->setState($capture ? 'completed' : 'authorization');
    $payment->save();
  }

  // ---------------------------------------------------------------------------
  // Refunds (SupportsRefundsInterface)
  // ---------------------------------------------------------------------------

  /**
   * {@inheritdoc}
   */
  public function refundPayment(PaymentInterface $payment, Price $amount = NULL): void {
    $this->assertPaymentState($payment, ['completed', 'partially_refunded']);
    $amount = $amount ?: $payment->getAmount();
    $this->assertRefundAmount($payment, $amount);

    $refund_amount = number_format((float) $amount->getNumber(), 2, '.', '');
    $payload = [
      'TransactionID' => $payment->getRemoteId(),
      'Amount'        => $refund_amount,
    ];

    $client   = $this->getUsioClient();
    $response = $client->refundPayment($payload);

    if (!$response || strtolower($response['Status'] ?? '') !== 'success') {
      $message = $this->mapErrorCode($response['Message'] ?? '');
      $this->logger->warning('USIO refund failed for payment @id: @msg', [
        '@id'  => $payment->id(),
        '@msg' => $message,
      ]);
      throw new PaymentGatewayException($message);
    }

    $old_refunded  = $payment->getRefundedAmount();
    $new_refunded  = $old_refunded->add($amount);

    if ($new_refunded->lessThan($payment->getAmount())) {
      $payment->setState('partially_refunded');
    }
    else {
      $payment->setState('refunded');
    }

    $payment->setRefundedAmount($new_refunded);
    $payment->save();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Returns an initialised USIO API client.
   */
  protected function getUsioClient(): Client {
    return new Client(
      $this->httpClient,
      $this->logger,
      [
        'merchant_id' => $this->configuration['merchant_id'],
        'login'       => $this->configuration['login'],
        'password'    => $this->configuration['password'],
        'terminal_id' => $this->configuration['terminal_id'],
        'mode'        => $this->getMode(),
      ]
    );
  }

  /**
   * Returns the configured merchant key for client-side use.
   */
  public function getMerchantKey(): string {
    return $this->configuration['merchant_key'] ?? '';
  }

  /**
   * Maps a USIO card-type string to a Commerce credit card type ID.
   */
  protected function mapCreditCardType(string $card_type): string {
    $map = [
      'visa'       => 'visa',
      'mastercard' => 'mastercard',
      'mc'         => 'mastercard',
      'amex'       => 'amex',
      'discover'   => 'discover',
      'diners'     => 'dinersclub',
      'dinersclub' => 'dinersclub',
      'jcb'        => 'jcb',
      'maestro'    => 'maestro',
    ];
    $normalised = strtolower($card_type);
    return $map[$normalised] ?? 'visa';
  }

  /**
   * Maps a USIO error code to a human-readable message.
   */
  protected function mapErrorCode(string $code): string {
    $map = [
      '5000' => 'Security violation.',
      '5001' => 'System failure.',
      '5011' => 'Operation not valid on this card type.',
      '5012' => 'Operation not available on this transaction type.',
      '5050' => 'Invalid amount.',
      '5051' => 'Invalid bank account type.',
      '5053' => 'Invalid email address.',
      '5054' => 'Invalid first name.',
      '5055' => 'Invalid last name.',
      '5056' => 'Invalid address.',
      '5057' => 'Invalid address line 2.',
      '5058' => 'Invalid city.',
      '5059' => 'Invalid state.',
      '5060' => 'Invalid ZIP code.',
      '5063' => 'Invalid card number.',
      '5064' => 'Invalid credit card type.',
      '5065' => 'Invalid expiration date.',
      '5066' => 'Invalid CVV.',
      '5078' => 'Invalid account number.',
      '5079' => 'Invalid routing number.',
      '5086' => 'Card brand not supported.',
      '5087' => 'Invalid payment type.',
      '5096' => 'Invalid SEC code.',
      '5150' => 'Error generating token.',
      '5151' => 'Invalid ACH account type.',
      '5152' => 'Invalid token.',
    ];
    return $map[$code] ?? $this->t('An error occurred with the payment gateway (code: @code).', ['@code' => $code]);
  }

}
