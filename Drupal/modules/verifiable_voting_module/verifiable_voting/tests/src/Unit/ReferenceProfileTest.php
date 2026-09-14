<?php

declare(strict_types=1);

namespace Drupal\Tests\verifiable_voting\Unit;

use Drupal\verifiable_voting\Plugin\BallotType\ApprovalBallotType;
use Drupal\verifiable_voting\Service\DevelopmentCredentialEligibilityProvider;
use Drupal\verifiable_voting\Service\DevelopmentEncryptionProvider;
use Drupal\verifiable_voting\Service\DevelopmentProofVerifier;
use Drupal\verifiable_voting\Service\DevelopmentSignatureProvider;
use Drupal\verifiable_voting\Service\JcsCanonicalizer;
use Drupal\verifiable_voting\Service\ReceiptGenerator;
use PHPUnit\Framework\TestCase;

/**
 * Tests deterministic and cryptographic behavior of the reference profile.
 *
 * @group verifiable_voting
 */
final class ReferenceProfileTest extends TestCase {

  /**
   * Restores environment state after each test.
   */
  protected function tearDown(): void {
    putenv('VERIFIABLE_VOTING_DEVELOPMENT_SIGNING_SECRET_KEY');
    putenv('VERIFIABLE_VOTING_DEVELOPMENT_BALLOT_KEY');
    parent::tearDown();
  }

  /**
   * Tests canonical receipts are stable and envelope-bound.
   */
  public function testReceiptIsDeterministicAndEnvelopeBound(): void {
    $generator = new ReceiptGenerator(new JcsCanonicalizer());
    $first = [
      'election_uuid' => 'election-a',
      'nullifier' => 'nullifier-a',
      'ciphertext' => ['algorithm' => 'test', 'ciphertext' => 'a'],
    ];
    $same_different_key_order = [
      'ciphertext' => ['ciphertext' => 'a', 'algorithm' => 'test'],
      'nullifier' => 'nullifier-a',
      'election_uuid' => 'election-a',
    ];
    self::assertSame($generator->generate($first), $generator->generate($same_different_key_order));
    $first['ciphertext']['ciphertext'] = 'b';
    self::assertNotSame($generator->generate($first), $generator->generate($same_different_key_order));
  }

  /**
   * Tests detached Ed25519 signatures reject changed messages.
   */
  public function testDevelopmentEd25519Provider(): void {
    $pair = sodium_crypto_sign_keypair();
    putenv('VERIFIABLE_VOTING_DEVELOPMENT_SIGNING_SECRET_KEY=' . sodium_bin2base64(sodium_crypto_sign_secretkey($pair), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING));
    $provider = new DevelopmentSignatureProvider();
    $message = '{"protocol_version":"verifiable-voting/1"}';
    $signature = $provider->sign($message, []);
    self::assertTrue($provider->verify($message, $signature, []));
    self::assertFalse($provider->verify($message . ' ', $signature, []));
    self::assertSame('Ed25519', $provider->publicMetadata([])['algorithm']);
  }

  /**
   * Tests authenticated encryption binds the encrypted ballot to its election.
   */
  public function testEncryptionPreventsElectionReplayAndTampering(): void {
    putenv('VERIFIABLE_VOTING_DEVELOPMENT_BALLOT_KEY=' . sodium_bin2base64(random_bytes(SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_KEYBYTES), SODIUM_BASE64_VARIANT_URLSAFE_NO_PADDING));
    $provider = new DevelopmentEncryptionProvider(new JcsCanonicalizer());
    $ciphertext = $provider->encrypt('election-a', ['selections' => ['choice-a']], []);
    self::assertSame(['selections' => ['choice-a']], $provider->decrypt('election-a', $ciphertext, []));
    $this->expectException(\InvalidArgumentException::class);
    $provider->decrypt('election-b', $ciphertext, []);
  }

  /**
   * Tests election-scoped opaque credential nullifiers.
   */
  public function testDevelopmentCredentialNullifiersAreElectionScoped(): void {
    $provider = new DevelopmentCredentialEligibilityProvider();
    $configuration = ['accepted_token_hashes' => [hash('sha256', 'opaque-test-token')]];
    self::assertSame([], $provider->validateConfiguration($configuration));
    $first = $provider->verify('election-a', ['token' => 'opaque-test-token'], $configuration);
    $repeat = $provider->verify('election-a', ['token' => 'opaque-test-token'], $configuration);
    $other_election = $provider->verify('election-b', ['token' => 'opaque-test-token'], $configuration);
    self::assertTrue($first['accepted']);
    self::assertSame($first['nullifier'], $repeat['nullifier']);
    self::assertNotSame($first['nullifier'], $other_election['nullifier']);
    self::assertArrayNotHasKey('token', $first['public_evidence']);
  }

  /**
   * Tests initial approval ballot canonicalization and rule enforcement.
   */
  public function testApprovalBallotCanonicalization(): void {
    $ballot_type = new ApprovalBallotType([], 'approval', ['label' => 'Approval']);
    self::assertSame([], $ballot_type->validateDefinition(['max_selections' => 2], [
      ['uuid' => 'choice-a'],
      ['uuid' => 'choice-b'],
    ]));
    self::assertSame(['selections' => ['choice-a', 'choice-b']], $ballot_type->canonicalizePlaintextBallot([
      'selections' => ['choice-b', 'choice-a'],
    ], ['choice-a', 'choice-b'], ['max_selections' => 2]));
    $this->expectException(\InvalidArgumentException::class);
    $ballot_type->canonicalizePlaintextBallot(['selections' => ['choice-a', 'choice-a']], ['choice-a', 'choice-b'], ['max_selections' => 2]);
  }

  /**
   * Tests that the reference proof verifier does not overclaim ZK evidence.
   */
  public function testReferenceProofVerifierLabelsItsLimit(): void {
    $verifier = new DevelopmentProofVerifier();
    $result = $verifier->verify('election-a', ['algorithm' => 'XChaCha20-Poly1305-IETF', 'nonce' => 'nonce', 'ciphertext' => 'ciphertext'], [], []);
    self::assertTrue($result['valid']);
    self::assertStringContainsString('not a zero-knowledge', $result['public_evidence']['warning']);
    self::assertFalse($verifier->verify('election-a', [], [], [])['valid']);
  }

}
