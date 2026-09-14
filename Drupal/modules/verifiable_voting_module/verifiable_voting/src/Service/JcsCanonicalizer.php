<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Service;

use Drupal\verifiable_voting\Contract\CanonicalizerInterface;
use Mmccook\JsonCanonicalizator\JsonCanonicalizatorFactory;

/**
 * Canonicalizes JSON-compatible protocol data using RFC 8785 JCS.
 */
final class JcsCanonicalizer implements CanonicalizerInterface {

  /**
   * {@inheritdoc}
   */
  public function canonicalize(array $data): string {
    $this->assertJsonCompatible($data);
    return JsonCanonicalizatorFactory::getInstance()->canonicalize($data);
  }

  /**
   * Rejects values that cannot have stable cross-language JSON semantics.
   *
   * @param mixed $value
   *   Value under validation.
   */
  private function assertJsonCompatible(mixed $value): void {
    if (is_array($value)) {
      foreach ($value as $key => $child) {
        if (!is_int($key) && !is_string($key)) {
          throw new \InvalidArgumentException('Canonical protocol data must have string or integer array keys.');
        }
        $this->assertJsonCompatible($child);
      }
      return;
    }
    if (is_string($value)) {
      if (!mb_check_encoding($value, 'UTF-8')) {
        throw new \InvalidArgumentException('Canonical protocol strings must be valid UTF-8.');
      }
      return;
    }
    if (is_float($value) && (!is_finite($value))) {
      throw new \InvalidArgumentException('Canonical protocol data cannot contain non-finite numbers.');
    }
    if (is_null($value) || is_bool($value) || is_int($value) || is_float($value)) {
      return;
    }
    throw new \InvalidArgumentException('Canonical protocol data must be JSON-compatible scalars or arrays.');
  }

}
