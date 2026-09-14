<?php

declare(strict_types=1);

namespace Drupal\verifiable_voting\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\verifiable_voting\Entity\ElectionInterface;
use Drupal\verifiable_voting\Service\AuditExporter;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\Response;

/**
 * Streams a portable ZIP audit package to authorized administrators.
 */
final class AuditExportController extends ControllerBase {

  /**
   * Constructs the controller.
   */
  public function __construct(private readonly AuditExporter $auditExporter) {}

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container): self {
    return new self($container->get('verifiable_voting.audit_exporter'));
  }

  /**
   * Returns the election's audit package as a ZIP archive.
   */
  public function download(ElectionInterface $verifiable_voting_election): Response {
    if (!class_exists(\ZipArchive::class)) {
      throw new \RuntimeException('The PHP ZIP extension is required for audit package download.');
    }
    $filename = tempnam(sys_get_temp_dir(), 'verifiable-voting-audit-');
    if ($filename === FALSE) {
      throw new \RuntimeException('Unable to allocate a temporary audit archive.');
    }
    $archive = new \ZipArchive();
    if ($archive->open($filename, \ZipArchive::OVERWRITE) !== TRUE) {
      throw new \RuntimeException('Unable to create the audit archive.');
    }
    foreach ($this->auditExporter->buildFiles($verifiable_voting_election) as $path => $contents) {
      $archive->addFromString($path, $contents);
    }
    $archive->close();
    $contents = file_get_contents($filename);
    unlink($filename);
    if ($contents === FALSE) {
      throw new \RuntimeException('Unable to read the completed audit archive.');
    }
    return new Response($contents, 200, [
      'Content-Type' => 'application/zip',
      'Content-Disposition' => 'attachment; filename="verifiable-voting-' . $verifiable_voting_election->id() . '-audit.zip"',
      'Cache-Control' => 'no-store',
    ]);
  }

}
