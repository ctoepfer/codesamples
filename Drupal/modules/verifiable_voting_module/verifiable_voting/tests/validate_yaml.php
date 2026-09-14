<?php

declare(strict_types=1);

require dirname(__DIR__) . '/vendor/autoload.php';

use Symfony\Component\Yaml\Yaml;

$root = dirname(__DIR__);
$paths = array_merge(
  glob($root . '/*.yml') ?: [],
  glob($root . '/config/install/*.yml') ?: [],
);
foreach ($paths as $path) {
  Yaml::parseFile($path, Yaml::PARSE_CUSTOM_TAGS);
  fwrite(STDOUT, basename($path) . "\n");
}
