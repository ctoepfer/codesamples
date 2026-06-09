<?php

namespace Drupal\commerce_usio\UsioPhpSdk;

use GuzzleHttp\ClientInterface;
use GuzzleHttp\Exception\RequestException;
use Psr\Log\LoggerInterface;

/**
 * Lightweight HTTP client for the USIO Checkout 2.0 REST API.
 *
 * Server-side calls authenticate via MerchantID + Login + Password embedded
 * in every request body. The base URLs differ between sandbox and production:
 *   Sandbox:    https://devcheckout.usiopay.com/2.0/
 *   Production: https://checkout.usiopay.com/2.0/
 *
 * All methods return the decoded JSON response array on success, or NULL when
 * the HTTP request fails or the response cannot be decoded.
 */
class Client {

  const SANDBOX_BASE    = 'https://devcheckout.usiopay.com/2.0/';
  const PRODUCTION_BASE = 'https://checkout.usiopay.com/2.0/';

  /** @var \GuzzleHttp\ClientInterface */
  protected ClientInterface $httpClient;

  /** @var \Psr\Log\LoggerInterface */
  protected LoggerInterface $logger;

  /** @var array */
  protected array $config;

  /**
   * @param \GuzzleHttp\ClientInterface $http_client
   * @param \Psr\Log\LoggerInterface $logger
   * @param array $config
   *   Keys: merchant_id, login, password, terminal_id, mode.
   */
  public function __construct(ClientInterface $http_client, LoggerInterface $logger, array $config) {
    $this->httpClient = $http_client;
    $this->logger     = $logger;
    $this->config     = $config;
  }

  // ---------------------------------------------------------------------------
  // Public API methods
  // ---------------------------------------------------------------------------

  /**
   * Processes a payment using a USIO Checkout.js one-time token.
   *
   * Required payload keys: Token, Amount.
   * Recommended additional keys: FirstName, LastName, Address1, City, State,
   *   Zip, Country, EmailAddress.
   *
   * @param array $payload
   *
   * @return array|null
   */
  public function submitTokenPayment(array $payload): ?array {
    $payload = $this->addCredentials($payload);
    return $this->post('SubmitTokenPayment', $payload);
  }

  /**
   * Queries the status of a previous transaction.
   *
   * @param string $confirmation_id
   *   The Confirmation value returned by submitTokenPayment().
   *
   * @return array|null
   */
  public function getPaymentStatus(string $confirmation_id): ?array {
    $payload = $this->addCredentials(['Confirmation' => $confirmation_id]);
    return $this->post('GetPaymentStatus', $payload);
  }

  /**
   * Requests a full or partial refund for a completed transaction.
   *
   * Required payload keys: TransactionID, Amount.
   *
   * @param array $payload
   *
   * @return array|null
   */
  public function refundPayment(array $payload): ?array {
    $payload = $this->addCredentials($payload);
    return $this->post('RefundTransaction', $payload);
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  /**
   * Returns the base URL for the configured mode.
   */
  protected function baseUrl(): string {
    return ($this->config['mode'] ?? 'sandbox') === 'live'
      ? self::PRODUCTION_BASE
      : self::SANDBOX_BASE;
  }

  /**
   * Merges server-side credentials into a request payload.
   *
   * Environment variables take precedence over the stored config values,
   * so production secrets can be kept out of the database entirely:
   *   USIO_MERCHANT_ID, USIO_LOGIN, USIO_PASSWORD, USIO_TERMINAL_ID
   */
  protected function addCredentials(array $payload): array {
    $payload['MerchantID'] = getenv('USIO_MERCHANT_ID') ?: $this->config['merchant_id'];
    $payload['Login']      = getenv('USIO_LOGIN')       ?: $this->config['login'];
    $payload['Password']   = getenv('USIO_PASSWORD')    ?: $this->config['password'];

    $terminal = getenv('USIO_TERMINAL_ID') ?: ($this->config['terminal_id'] ?? '');
    if (!empty($terminal)) {
      $payload['TerminalID'] = $terminal;
    }

    return $payload;
  }

  /**
   * Executes a POST request and returns the decoded JSON body.
   *
   * @param string $endpoint
   *   Path relative to the base URL (e.g. 'SubmitTokenPayment').
   * @param array $payload
   *   Data to JSON-encode as the request body.
   *
   * @return array|null
   */
  protected function post(string $endpoint, array $payload): ?array {
    $url = $this->baseUrl() . $endpoint;

    try {
      $response = $this->httpClient->request('POST', $url, [
        'json'    => $payload,
        'headers' => [
          'Accept'       => 'application/json',
          'Content-Type' => 'application/json',
          'cache-control' => 'no-cache',
        ],
        'timeout' => 30,
      ]);

      $body = (string) $response->getBody();

      if (empty($body)) {
        $this->logger->error('USIO API: Empty response body from @endpoint.', ['@endpoint' => $endpoint]);
        return NULL;
      }

      $decoded = json_decode($body, TRUE);

      if (json_last_error() !== JSON_ERROR_NONE) {
        // Do not log the raw body — it may contain PII (names, addresses).
        $this->logger->error('USIO API: JSON decode error from @endpoint — @err.', [
          '@endpoint' => $endpoint,
          '@err'      => json_last_error_msg(),
        ]);
        return NULL;
      }

      return $decoded;
    }
    catch (RequestException $e) {
      // Log only the HTTP status code and endpoint, never the request/response
      // body, which carries credentials and customer PII.
      $status = $e->hasResponse() ? $e->getResponse()->getStatusCode() : 0;
      $this->logger->error('USIO API: Request to @endpoint failed (HTTP @status).', [
        '@endpoint' => $endpoint,
        '@status'   => $status,
      ]);
      return NULL;
    }
    catch (\Exception $e) {
      $this->logger->error('USIO API: Unexpected error calling @endpoint — @class.', [
        '@endpoint' => $endpoint,
        '@class'    => get_class($e),
      ]);
      return NULL;
    }
  }

}
