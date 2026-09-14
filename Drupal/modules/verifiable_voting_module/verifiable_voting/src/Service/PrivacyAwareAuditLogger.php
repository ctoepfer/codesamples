<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\Core\Database\Connection;
use Drupal\Core\Datetime\TimeInterface;
use Psr\Log\LoggerInterface;

/**
 * Stores a restricted audit trail that rejects identity-bearing context keys.
 */
final class PrivacyAwareAuditLogger {

  /**
   * Keys that must never be retained in the security audit context.
   */
  private const FORBIDDEN_KEYS = [
    'uid', 'user_id', 'username', 'email', 'name', 'ip', 'ip_address',
    'session', 'session_id', 'cookie', 'authorization', 'token', 'password',
    'credential', 'raw_credential', 'request_id', 'user_agent', 'referer',
  ];

  /**
   * Constructs the audit logger.
   */
  public function __construct(
    private readonly Connection $database,
    private readonly TimeInterface $time,
    private readonly JcsCanonicalizer $canonicalizer,
    private readonly LoggerInterface $logger,
  ) {}

  /**
   * Records a security event after filtering prohibited keys.
   *
   * @param array<string, mixed> $context
   *   Non-identifying event context.
   */
  public function log(string $event_type, ?string $election_uuid = NULL, array $context = []): void {
    $this->assertPrivacySafe($context);
    $this->database->insert('verifiable_voting_security_audit')->fields([
      'election_uuid' => $election_uuid,
      'event_type' => $event_type,
      'context_json' => $this->canonicalizer->canonicalize($context),
      'created' => $this->time->getRequestTime(),
    ])->execute();
    $this->logger->notice('Security event {event_type} recorded for election {election_uuid}.', [
      'event_type' => $event_type,
      'election_uuid' => $election_uuid ?? 'none',
    ]);
  }

  /**
   * Rejects nested identity-bearing context keys and unbounded secret values.
   *
   * @param array<string, mixed> $context
   *   Audit context.
   */
  private function assertPrivacySafe(array $context): void {
    foreach ($context as $key => $value) {
      $normalized = strtolower((string) $key);
      if (in_array($normalized, self::FORBIDDEN_KEYS, TRUE)) {
        throw new \InvalidArgumentException(sprintf('Audit context key "%s" is prohibited by the privacy policy.', $key));
      }
      if (is_array($value)) {
        $this->assertPrivacySafe($value);
      }
    }
  }

}
