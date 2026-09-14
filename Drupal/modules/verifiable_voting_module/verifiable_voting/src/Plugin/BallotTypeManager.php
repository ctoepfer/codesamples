<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Plugin;

use Drupal\Core\Cache\CacheBackendInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Plugin\DefaultPluginManager;

/**
 * Discovers ballot-type plugins.
 */
final class BallotTypeManager extends DefaultPluginManager {

  /**
   * Constructs the ballot type manager.
   */
  public function __construct(\Traversable $namespaces, CacheBackendInterface $cache_backend, ModuleHandlerInterface $module_handler) {
    parent::__construct('Plugin/BallotType', $namespaces, $module_handler, NULL, 'Drupal\\verifiable_voting\\Annotation\\BallotType');
    $this->alterInfo('verifiable_voting_ballot_type_info');
    $this->setCacheBackend($cache_backend, 'verifiable_voting_ballot_type_plugins');
  }

}
