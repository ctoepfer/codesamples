# Verifiable Voting

**Verifiable Voting** is a reusable, domain-neutral Drupal module for administering multiple independent elections or contests and publishing structured election evidence. Its entities, services, provider interfaces, and terminology refer only to elections, choices, credentials, ballots, and evidence.

> Built for judging beer, but likely better and more secure than most of your commercial voting software.

That is documentation personality, not a domain-specific architectural claim. This module is experimental software and **not** certified voting equipment.

| Property | Current V1 position |
| --- | --- |
| Election separation | Implemented through immutable election UUIDs, election-scoped nullifiers, AEAD associated data, frozen manifests, and distinct ordered ledgers. |
| One accepted ballot | Implemented for the bundled non-anonymous development credential provider with a durable unique `(election_uuid, nullifier)` database guard. |
| Ballot privacy | The reference profile encrypts ballot material at rest, but the server can decrypt it. It is **not** end-to-end secrecy. |
| Ballot validity | The reference verifier records server-side pre-encryption validation. It is **not** a zero-knowledge proof. |
| Recorded as cast | The module derives a deterministic receipt from the canonical accepted envelope and publishes a receipt lookup plus public hash-chain ledger. |
| Tamper evidence | Versioned SHA-256 hash chaining detects record mutation, deletion, or reorder during replay. External checkpoint publication is required to make omissions externally detectable. |
| Counted as recorded | The bundled tally is development-only decrypt-and-tally. It is **not** threshold, homomorphic, or independently verifiable. |

## Scope, threat model, and architecture

The module is a reliable **application workflow and evidence-publication layer**, not an assertion that Drupal is the ultimate cryptographic trust boundary. It manages permissions, lifecycle transitions, configuration freezing, transactional acceptance, evidence delivery, and audit exports. Mature end-to-end-verifiable systems instead separate election authority, credential issuer, ballot verifier, trustees, application administrator, and independent monitor roles. ElectionGuard’s public election-record design is the primary architectural reference for that separation. [1] [2]

V1 is appropriate only for development, demonstration, or an explicitly assessed **low-coercion organizational setting**. Encrypting a ballot and displaying a receipt does not make browser voting coercion-resistant. Helios similarly limits web-based voting to settings where coercion is not significant. [3]

| Layer | V1 responsibility | Future production boundary |
| --- | --- | --- |
| Drupal entities and forms | Election configuration, choices, explicit lifecycle confirmations, access control, public manifest, audit export. | Retain as operational and publication infrastructure. |
| Ballot types | `BallotTypeInterface`; V1 supplies bounded approval / choose-up-to-N rules. | Add plurality, ranked, scored, and other types as independently validated plugins. |
| Eligibility | `EligibilityProviderInterface` returns an election-scoped result, nullifier, and safe evidence. | Use a reviewed membership, issuer, or anonymous-credential service. |
| Cryptography | `EncryptionProviderInterface` and `ProofVerifierInterface` prevent storage from assuming one scheme. | Use an isolated, reviewed ballot/proof service; do not implement SNARK mathematics in PHP. |
| Ledger and receipt | RFC 8785 canonical envelope, SHA-256 receipt, transactional ordered hash chain. | Add independently published signed checkpoints, then a defined Merkle transparency-log profile when inclusion proofs are required. |
| Tally and certification | `TallyProviderInterface` separates tally from ballot storage; a reference Ed25519 signer can sign a certification statement. | Use homomorphic aggregation with threshold decryption, or a reviewed mixnet workflow, plus independent verification. |

The module provides `Election`, `Choice`, `BallotAcceptance`, and `LedgerEntry` content entities. The accepted-ballot entity deliberately has no Drupal user ID, name, email address, IP address, session ID, token, request ID, or plaintext ballot field. Security audit context rejects common identity-bearing keys. This limits the module’s own data model; deployments must separately control reverse-proxy logs, access logs, analytics, backups, help-desk records, and browser telemetry.

## Lifecycle and administration

The lifecycle is `draft → open → closed → tallying → certified → archived`; `configured` is available for deployments that separate setup from readiness, and `invalidated` is an auditable terminal state. Opening is blocked until sodium availability, an election UUID, choices, ballot rules, dates, and configured provider checks pass. After opening, choice identity/order and security-relevant election configuration are frozen. Closure stops ballot acceptance. Certification appends a signed statement and stores the final root. Invalidation adds a new public ledger entry rather than deleting evidence.

Administration is located at **Administration → Configuration → Verifiable Voting**. Opening, closing, tallying, certification, archival, and invalidation use an explicit confirmation form. The public and administrative endpoints are intentionally narrow.

| Route | Purpose | Access |
| --- | --- | --- |
| `/voting/election/{election}/cast` | Bounded approval-ballot form using a credential token. | Public Drupal Form API route; deployments should add a privacy-reviewed anti-abuse control. |
| `/voting/election/{election}/ledger` | Ordered public evidence ledger. | Public, read-only. |
| `/voting/election/{election}/receipt/{receipt}` | Receipt presence, sequence, and ledger-hash lookup. | Public, read-only. |
| `/admin/config/verifiable-voting/elections/{election}/audit-package` | ZIP of `election.json`, `ledger.json`, `ledger-root.json`, `tally.json`, and `certification.json`. | Restricted audit-export permission. |

## Ballot, receipt, and ledger process

The casting service does not trust a client-supplied election status, choice validity, eligibility result, timestamp, sequence number, receipt, or predecessor hash. It reads the election state server-side; validates selections against frozen choice UUIDs; verifies an eligibility assertion; derives an election-specific nullifier; encrypts the canonical ballot; obtains verifier evidence; then uses a database transaction to reserve the nullifier, append a ledger entry, and create an immutable accepted-ballot entity.

The receipt is not a random confirmation number. The accepted envelope is canonicalized with the RFC 8785 JSON Canonicalization Scheme (JCS), hashed with SHA-256, and URL-safe-base64 encoded. RFC 8785 exists precisely to ensure independent implementations can reproduce JSON bytes despite object ordering and representation differences. [4] A changed envelope necessarily gives a changed receipt.

```text
record_hash[n] = SHA-256(
  "verifiable-voting/hash-chain/1\0" || record_hash[n-1] || canonical_record[n]
)
```

V1 selects a simple linear chain over a Merkle tree because it is easy for an independent monitor to replay for a serialized writer. It does **not** offer compact inclusion or consistency proofs. A later transparency-log phase should define RFC 6962-style tree semantics, signed tree heads, independent monitoring, and recovery procedures before making Merkle-related claims. [5] [6]

## Cryptography and key management

The module requires native PHP `ext-sodium` and fails closed if it is absent. It uses sodium’s Ed25519 detached-signature API, specified by RFC 8032, and PHP `random_bytes()` for cryptographic random values. [7] [8] The development encrypted-ballot provider uses XChaCha20-Poly1305 with a fresh 24-byte nonce and election UUID associated data, following libsodium’s authenticated-encryption requirements. [9]

The bundled providers are specifically labeled `development` or `development-trusted-server`. They make functional tests possible but do not establish production election secrecy or verification. The encryption provider can decrypt individual ballots; the proof provider makes no zero-knowledge statement; the eligibility provider is a token issuer that can correlate users; the tally provider decrypts individual ballots; and the signing provider reads a secret from environment only.

```bash
# URL-safe, unpadded base64 encoding of a 64-byte Ed25519 secret key.
VERIFIABLE_VOTING_DEVELOPMENT_SIGNING_SECRET_KEY=...

# URL-safe, unpadded base64 encoding of a 32-byte XChaCha20-Poly1305 key.
VERIFIABLE_VOTING_DEVELOPMENT_BALLOT_KEY=...
```

**Never store a signing or ballot-decryption secret in ordinary Drupal configuration exports.** Production deployments should use separately governed key custody, threshold trustees, documented rotation and compromise procedures, and an external signing or decryption service. Drupal Key and Encrypt may be evaluated for bounded server-side operational secrets, but cannot establish election secrecy or replace threshold governance.

## Eligibility, proof, and ZK roadmap

The development eligibility provider accepts an opaque token only when its SHA-256 digest is present in the election configuration. It returns a deterministic nullifier scoped to the election UUID and returns neither the token nor identity data as ballot evidence. The unique nullifier guard closes the application-level race between simultaneous submissions. This is **not** anonymous credential technology.

The development proof provider states only that this server accepted a structurally valid encrypted envelope after server-side plaintext validation. It is deliberately not named or exported as a ZK proof. The next cryptographic phase should use an external verifier boundary with authenticated transport, strict versioned schemas, resource limits, reproducible artifacts, and published verifier inputs/outputs.

No Circom, circomlib, snarkJS, Semaphore, Groth16, PLONK, FFLONK, or PHP zk-SNARK verifier is a V1 dependency. Circom and circomlib are circuit-development tools, not voting protocols. snarkJS requires artifact pinning, formal statement review, test vectors, reproducible builds, verifier fuzzing, and setup governance before it can support a serious election protocol. [10] [11] A future anonymous-eligibility proof must bind the election UUID, frozen manifest hash, credential-root version, election-specific nullifier, and encrypted-ballot commitment, while preserving atomic nullifier uniqueness.

ElectionGuard, Helios, and Belenios are valuable prior art rather than drop-in dependencies. ElectionGuard documents encrypted ballot evidence, public election records, homomorphic aggregation, and trustee roles. [1] Helios supplies a cast-or-audit reference and a coercion warning. [3] Belenios illustrates role separation and public-board monitoring. [12]

## What this system does **not** prove

A receipt proves only that a receipt-bound accepted envelope appears in the published application ledger. It does **not** prove that a voter’s device represented their intended choice, that a voter was free from coercion, that their device was malware-free, that the credential issuer made an accurate decision, that a network observer cannot correlate an event, that the server did not decrypt a ballot, or that a tally is correct.

The module does not claim certification, legal validity, public-election readiness, coercion resistance, anonymity, endpoint integrity, traffic-analysis resistance, availability under denial of service, accessibility for every voter, or trustworthiness of server administrators. A deployment must minimize network metadata; disable unnecessary analytics on voting routes; restrict and time-limit logs; review small-cell result disclosure; control backups; publish checkpoints through an independent channel; and obtain appropriate legal and security review.

## Dependency and license policy

The module is free and open-source software under **GPL-2.0-or-later**. `composer.json` declares the SPDX identifier, and [`LICENSE`](LICENSE) contains GPL version 2; the project’s “or later” notice invokes GPLv2 section 9. Direct and transitive Composer package licensing is recorded in [`docs/DEPENDENCY_LICENSES.json`](docs/DEPENDENCY_LICENSES.json).

| Component | Role | License and decision |
| --- | --- | --- |
| Drupal core | Entity, validation, form, database, Lock, Config, and access APIs. | GPL-2.0-or-later; required and compatible. |
| PHP `ext-sodium` / libsodium | Ed25519, XChaCha20-Poly1305, constant-time helpers, and base64url. | Native extension; upstream libsodium is ISC-licensed; required at runtime. |
| `mmccook/php-json-canonicalization-scheme` | Canonical JSON implementation. | MIT; the reviewed development resolution was 1.0.0. Production deployments must commit and review their own Composer lock. |
| PHPUnit | Unit-test runner. | BSD-3-Clause; development-only dependency. |
| Voting API, Rate, Poll | Ratings, reactions, or general polling. | Not required for authoritative ballots, evidence, tally, or certification. |
| Key, Encrypt, Sodium Drupal modules | Optional server-side secret or at-rest-encryption integrations. | Not V1 dependencies; review exact selected release and license first. |
| Circom, circomlib, snarkJS, Semaphore | Future research candidates. | Not V1 dependencies; require pinned license, provenance, and security review. |

The project avoids proprietary, source-available-only, field-of-use-restricted, and non-commercial dependencies. Do not copy cryptographic code, proof circuits, or third-party material into the module without a dedicated provenance, license, maintenance, vector, and assurance review.

## Installation and development

Copy this directory to a Drupal custom-module path such as `web/modules/custom/verifiable_voting`, or add it as a local Composer path repository while it remains in this monorepo. Require the package from the Drupal project, set the two **development-only** environment variables only when exercising the reference providers, enable the module, and clear caches.

```bash
composer require ctoepfer/verifiable_voting:@dev
drush en verifiable_voting -y
drush cr
```

Create an election, create at least two active choices, enter only SHA-256 credential-token digests, and run readiness before opening. The module will reject opening when its sodium, choice, date, provider, or key-availability gates fail. Do not use the reference profile to represent a production, anonymous, or public election.

The module requires PHP 8.1 or later, Drupal 10 or 11, `ext-sodium`, and PHP ZIP support for audit-archive download. Development validation uses the following commands.

```bash
composer install
composer validate --strict
composer audit
find src tests -type f -name '*.php' -print0 | xargs -0 -n1 php -l
vendor/bin/phpunit --testdox tests/src/Unit/ReferenceProfileTest.php
```

The unit tests cover deterministic receipts, changed-envelope receipts, Ed25519 verification, AEAD replay resistance, election-scoped nullifiers, approval-ballot validation, and explicit reference-verifier limitations. A dedicated Drupal kernel fixture and independently operated verifier remain required before any use beyond development.

## References

[1]: https://electionguard.vote/concepts/Verifiability/ "ElectionGuard: Creating a Verifiable Election"
[2]: https://electionguard.vote/develop/Election_Record/ "ElectionGuard Election Record"
[3]: https://vote.heliosvoting.org/faq "Helios Voting FAQ"
[4]: https://www.rfc-editor.org/rfc/rfc8785.html "RFC 8785: JSON Canonicalization Scheme"
[5]: https://csrc.nist.gov/pubs/fips/180-4/upd1/final "NIST FIPS 180-4: Secure Hash Standard"
[6]: https://www.rfc-editor.org/rfc/rfc6962.html "RFC 6962: Certificate Transparency"
[7]: https://www.rfc-editor.org/rfc/rfc8032.html "RFC 8032: Edwards-Curve Digital Signature Algorithm"
[8]: https://www.php.net/manual/en/function.random-bytes.php "PHP random_bytes"
[9]: https://libsodium.gitbook.io/doc/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction "Libsodium XChaCha20-Poly1305 construction"
[10]: https://github.com/iden3/circom "Circom: Circuit Compiler for ZK Proving Systems"
[11]: https://github.com/iden3/snarkjs "snarkJS: JavaScript and WebAssembly zkSNARK and PLONK Implementation"
[12]: https://www.belenios.net/instructions.html "Belenios: Election role instructions"
