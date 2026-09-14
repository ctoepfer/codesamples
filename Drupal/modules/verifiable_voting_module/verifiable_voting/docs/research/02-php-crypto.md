# PHP Cryptography and Canonicalization Reuse for Verifiable Voting V1

**Author:** Manus AI  
**Scope:** Reusable PHP cryptography, canonical serialization, ledger, identifier, and secure-random components for a Drupal verifiable-voting V1.  
**Decision posture:** This report evaluates reuse of established APIs and libraries. It does **not** recommend inventing, modifying, or implementing cryptographic primitives.

## Executive conclusion

A defensible minimal V1 baseline is **native PHP `ext-sodium` as an environment requirement**, **PHP `random_bytes()`**, **Drupal core’s `uuid` service for opaque v4 IDs**, **PHP `hash('sha256', ..., true)` for the public ledger chain**, and **one pinned RFC 8785 JSON Canonicalization Scheme (JCS) dependency** for precisely defined signed/hashed JSON. Use `sodium_crypto_sign_detached()` and `sodium_crypto_sign_verify_detached()` for Ed25519 signatures, `sodium_crypto_aead_xchacha20poly1305_ietf_encrypt()` only where V1 has a real confidentiality requirement, and `sodium_crypto_generichash()` only for a separately versioned BLAKE2b use case. PHP documents `ext-sodium` as bundled since PHP 7.2 and exposes Ed25519 signing, BLAKE2b generic hashing, and authenticated-encryption APIs. [1] [2] [3] [4]

**Conclusion:** For a centrally written V1 audit ledger, an ordered **SHA-256 hash chain with signed checkpoints** is preferable to adding a Merkle tree. It is simpler to specify, append, and independently replay, and it serves the primary V1 objective: detect modification, reordering, and removal between a signed checkpoint and subsequent entries. A Merkle tree should be deferred until the product requires compact, per-record inclusion proofs for independent verifiers or public transparency-log consistency proofs. Certificate Transparency demonstrates the added capabilities of a Merkle design, including audit paths and consistency proofs, but it also defines exact tree shape, leaf/node domain separation, and proof verification rules that must be implemented and tested exactly. [5]

This is a **design conclusion**, not a claim that a hash chain alone makes an election verifiable. In particular, a hash chain cannot by itself establish that a captured vote was correctly formed, that the signer or host was uncompromised, that voters can safely verify a receipt without coercion risks, or that a server did not equivocate before checkpoint publication. Those requirements need a separately reviewed voting protocol, key-management plan, operational controls, and an external checkpoint-publication policy.

## Confirmed facts and bounded conclusions

| Topic | Confirmed evidence | Bounded V1 conclusion |
|---|---|---|
| Native cryptography | `ext-sodium` is bundled from PHP 7.2; PHP documents a native random Ed25519 keypair API, detached sign/verify APIs, BLAKE2b generic hash API, and a preferred XChaCha20-Poly1305 AEAD API. [1] [2] [3] [4] | Require `ext-sodium` at install time. It covers V1 signatures, binary encoding helpers, BLAKE2b, and authenticated encryption without a PHP crypto package. |
| Ed25519 | RFC 8032 specifies EdDSA with Ed25519 and test vectors. It recommends Ed25519 where a 128-bit security level is sufficient and cautions against the prehash variants in most cases. [6] | Sign the exact canonical record bytes directly with Ed25519. Do not substitute an ad hoc “hash then sign” prehash construction. |
| Canonical JSON | RFC 8785 makes JSON hashable by strict primitive serialization, the I-JSON subset, and recursive deterministic property sorting. It requires failure on invalid Unicode and NaN/Infinity. [7] | Canonicalization is a protocol boundary. Use one explicit JCS library and freeze its package version plus test vectors. Do not rely on ordinary `json_encode()` as the signature format. |
| JWS | RFC 7515 fixes a JWS signing input as base64url-encoded protected-header bytes, a period, and base64url payload bytes; RFC 8037 defines `alg: "EdDSA"` for Ed25519 JWS using `OKP` keys. [8] [9] | Direct detached Ed25519 over JCS bytes is smaller and more transparent for an internal ledger. Add JWS only when standards-based token interchange or JWK/JWKS distribution is a real external contract. |
| Secure randomness | PHP says `random_bytes()` produces uniformly selected, cryptographically secure bytes suitable for long-term secrets and throws if no suitable OS source is available. [10] | Use it for nonces and entropy-backed identifiers. Treat exceptions as fatal for the security-sensitive operation; never fall back to `rand()`, timestamps, or a deterministic retry. |
| UUIDs | Drupal core’s PHP UUID generator obtains 16 bytes with `random_bytes()` and constructs a UUID v4. RFC 9562 describes v4 as random/pseudorandom and v7 as time-ordered with random bits. [11] [12] | Reuse Drupal’s injected `uuid` service for opaque V1 record IDs. Do not use an ID as ledger ordering, integrity, or a vote secret. Use the ledger sequence number for ordering. |
| AEAD | PHP calls XChaCha20-Poly1305 the best provided AEAD mode and specifies a fresh 24-byte nonce per message; libsodium says a nonce must never repeat under a key and identifies additional authenticated data (AAD). [3] [13] | Where encryption is genuinely needed, use native XChaCha20-Poly1305 with a `random_bytes(24)` nonce and bind non-secret record metadata as AAD. Store ciphertext, nonce, algorithm/version, and key identifier. |
| Hashes | PHP supports SHA-256 with binary output. PHP sodium’s generic hash is BLAKE2b and supports an optional key. RFC 7693 specifies BLAKE2b and its keyed mode. [14] [4] [15] | Make public audit-chain hashes `SHA-256` for conventional interoperability and unambiguous RFC 6962 alignment if migration occurs. BLAKE2b is a valid native alternative only if explicitly versioned; do not mix algorithms in one chain. |
| Sodium compatibility | `paragonie/sodium_compat` is a pure-PHP `ext-sodium` polyfill that delegates to the extension when present. Its README explicitly states it has not had a formal independent cryptographic audit and notes pure-PHP performance limitations. [16] | Do not include it in the V1 normal path. It is an optional legacy deployment fallback only if a supported deployment cannot require `ext-sodium`; such a deployment needs its own performance and risk approval. |
| Merkle libraries | The reviewed PHP package `pleonasm/merkle-tree` accepts a caller-provided hash callback and documents Bitcoin-style fixed-size tree behavior, not RFC 6962 audit/consistency-proof compatibility. [17] | Do not depend on it for V1. A later Merkle version should choose or build only a well-tested RFC 6962-compatible component and validate standard vectors and proof behavior. |

## Recommended V1 dependency set

### Required runtime platform and Composer dependencies

| Category | Recommended dependency | Pinning and reuse decision | Why it is sufficient for V1 |
|---|---|---|---|
| Native crypto | PHP `ext-sodium` | **Required platform extension**; check `extension_loaded('sodium')` during installation and fail closed if missing. [1] | Native PHP API provides Ed25519, AEAD, BLAKE2b, base64 variants, and constant-time comparison utilities. |
| Canonical serialization | `mmccook/php-json-canonicalization-scheme` | **One Composer dependency, exact reviewed release**. The repository identifies RFC 8785 compliance and tests; its Packagist release is `1.0.0`, PHP `^8.1`, with no runtime dependencies. Its low package maturity signals mean the module should pin, vendor-review, and execute RFC 8785 conformance cases in CI before production use. [18] [19] | It supplies the non-native JCS step needed to turn a constrained JSON data model into deterministic signed bytes. |
| Secure random | PHP `random_bytes()` | **No Composer dependency.** [10] | Provides CSPRNG bytes for encryption nonces and other secrets. |
| UUID | Drupal core `uuid` service | **No Composer dependency** for V1. Core’s default implementation makes v4 UUIDs from `random_bytes(16)`. [11] | Supplies opaque database IDs while keeping ledger ordering in a separate monotonic sequence. |
| Ledger digest | PHP `hash` extension / `hash('sha256', ..., true)` | **No Composer dependency.** SHA-256 is the documented algorithm example and raw-binary output is supported. [14] | Gives a stable, broadly implemented public digest for the chain. |

The practical V1 Composer addition is therefore **only the audited-and-pinned JCS implementation**. `ext-sodium` is a deploy-time capability rather than a Composer package. This recommendation assumes a current PHP runtime supported by the Drupal deployment and by the selected JCS package; the candidate package states PHP `^8.1`. [19]

### Components deliberately excluded from the minimal set

| Candidate | Evidence | V1 disposition |
|---|---|---|
| `paragonie/sodium_compat` | It provides broad sodium API coverage and delegates to native sodium when available, but is a pure-PHP fallback; maintainers explicitly say it has not received a formal independent cryptographic audit and document potentially slow pure-PHP operation. [16] | **Exclude by default.** Do not turn a modern deployment requirement into an optional crypto downgrade. Consider only for a separately approved legacy compatibility profile. |
| `web-token/jwt-framework` / JWT Framework | The maintained framework documents EdDSA with Ed25519 support; its repository is active and provides a security reporting path. [20] [21] | **Exclude by default.** It is suitable when V1 needs JWS/JWT/JWK interoperability. It is unnecessary if the ledger signs explicitly canonical record bytes and stores raw/base64url signature material. |
| `ramsey/uuid` | The project is a mature UUID library and documents `Uuid::uuid7()` for sortable UUIDv7 values. [22] [23] | **Exclude by default.** Drupal core v4 UUIDs suffice for opaque IDs. A chain sequence number is the authoritative order. Add Ramsey only if a documented external UUIDv7 requirement arises. |
| `pleonasm/merkle-tree` | The repository’s usage delegates hashing to the consumer and describes a Bitcoin-style fixed-size tree. [17] | **Exclude.** It does not provide evidence of the needed RFC 6962 tree and proof semantics. |
| PHP OpenSSL AEAD | PHP exposes AEAD tag/AAD arguments for GCM/CCM, but its `openssl_encrypt()` documentation cautions that its parameter named `passphrase` is not processed by a KDF and is silently padded/truncated. [24] | **Do not select when sodium is available.** XChaCha20-Poly1305 has a focused native API and a 24-byte random-nonce guidance path. |

## Canonical record and signature profile

### What the canonicalization boundary must specify

The V1 specification should define one **logical record schema**, not merely “a JSON object.” Before passing a value to JCS, the module should reject fields outside the permitted schema and types. Relevant RFC 8785 constraints include recursively sorted object properties, preserved array order, ECMAScript-number serialization, invalid-Unicode rejection, and rejection of NaN/Infinity. [7]

Recommended policy conclusions are as follows:

1. Use a **versioned record schema** such as `record_format: "vv-ledger-jcs-1"`. The value is a protocol identifier, not a security primitive.
2. Represent identifiers, times, vote commitments, hash values, public keys, nonces, and signatures as strings in a fixed documented encoding. Use lowercase hexadecimal or unpadded base64url consistently. PHP sodium supports URL-safe no-padding base64 variants. [25]
3. Avoid numeric fields when a decimal string can represent the required business value. This avoids accidental differences caused by the JCS number model. If an integer is necessary, set a bounded range and test the exact canonical bytes.
4. Reject duplicate object keys before a PHP associative array is constructed. JSON objects with duplicate members are not an acceptable unambiguous signed-data input for this profile.
5. Canonicalize the specified logical record **once**. Persist the resulting canonical UTF-8 byte string, or persist enough input plus the canonical bytes/hash to permit an exact re-computation during audit.
6. Establish CI fixtures consisting of RFC 8785 test material, all accepted V1 record variants, Unicode edge cases, and known Ed25519 sign/verify test vectors from RFC 8032. [6] [7]

> RFC 8785 states that hashing and signing need an invariant representation, and defines JCS using strict primitive serialization, I-JSON constraints, and deterministic property sorting. [7]

### Direct detached Ed25519 signature, not JWS, for the V1 ledger

For each checkpoint, sign a clearly versioned byte message that includes a domain-separation label, election namespace, ledger sequence range, terminal chain hash, hash algorithm identifier, canonicalization/profile identifier, key identifier, and checkpoint time. This is a protocol-level message format whose fields must be specified and tested; it is **not** a new cryptographic primitive. Use native detached signing and verification. PHP documents that the signer API returns a detached signature and that the verifier takes the signature, message, and Ed25519 public key and returns a Boolean. [2] [26]

Ed25519 is appropriate for this recommendation because PHP sodium exposes the required keypair/sign/verify APIs and RFC 8032 defines the algorithm and test vectors. The recommendation does **not** claim that Ed25519 removes private-key custody, authorization, side-channel, or key-rotation risks. Store private signing keys outside ordinary Drupal configuration and database exports, use a key identifier in every checkpoint, and retain old public keys so historical checkpoints stay verifiable. RFC 8032 identifies private-key secrecy as fundamental and discusses side-channel considerations. [6]

Use JWS only if a verifier needs a standard JOSE envelope. RFC 7515 signs a defined base64url header-and-payload input, and RFC 8037 maps `EdDSA` with an Ed25519 `OKP` key into that ecosystem. That is a sound interoperability option, but it introduces JOSE header validation, algorithm allowlisting, key representation, and serialization decisions that the V1 internal ledger otherwise does not need. [8] [9]

## Encryption and secret handling profile

Encryption is not a substitute for ledger integrity or ballot-verification design. Encrypt only fields whose confidentiality is explicitly required by the system’s data model, and do not encrypt public chain-link fields that independent verifiers need to replay.

For a V1 confidential payload, use `sodium_crypto_aead_xchacha20poly1305_ietf_encrypt()` with a 256-bit key generated and managed outside business logic, a fresh `random_bytes(24)` nonce, and AAD that binds non-secret envelope metadata such as `format`, `election_id`, `record_id`, and `key_id`. PHP identifies this mode as preferred and says the nonce must be 24 bytes and unique per message/key; the libsodium documentation further says nonce reuse under the same key must never occur and that the tag authenticates both ciphertext and AAD. [3] [13]

Persist the algorithm/profile identifier, nonce, ciphertext-with-tag, key identifier, and canonical AAD representation. Decrypt only after AEAD authentication succeeds. Do not derive an encryption key by passing a human passphrase to `openssl_encrypt()`; the PHP documentation says that parameter is only padded or truncated and no key derivation function is used. [24]

## Hash selection and ledger design

### SHA-256 versus BLAKE2b

Use **SHA-256** for V1 public ledger links and checkpoints. PHP supports `hash('sha256', $bytes, true)` and NIST specifies SHA algorithms for producing digests that detect message changes. [14] [27] This is a compatibility-oriented choice, not a statement that BLAKE2b is unsuitable. BLAKE2b is standardized in RFC 7693, optimized for 64-bit platforms, can produce 1–64 byte outputs, and PHP sodium exposes it through `sodium_crypto_generichash()`, including a keyed mode. [15] [4]

Use BLAKE2b only where the protocol explicitly needs a BLAKE2b digest or keyed MAC and records `hash_alg: "blake2b-256"` (or an exact equivalent) in the versioned profile. Do not call an unkeyed hash a MAC. Do not change algorithms partway through a chain without an explicit migration checkpoint that binds the old terminal digest and new profile.

### V1 append-only hash chain

A V1 ledger entry should bind its **sequence number**, **previous entry digest**, **record-format identifier**, **canonical record bytes (or its explicit SHA-256 digest)**, and **event type/election namespace** under an unambiguous, length-delimited protocol encoding. Domain-separate the entry type from checkpoints, for example with fixed ASCII labels specified by the protocol. The module should invoke PHP’s existing SHA-256 implementation rather than implement SHA-256 or a custom hash function. [14]

The database must enforce the expected predecessor and monotonic sequence in one transaction or equivalent serialized append operation. That is an application integrity control, not a cryptographic property. Periodically create a signed checkpoint as described above and publish or deliver it to an independently controlled durable location. A checkpoint signed only by the same mutable application environment gives useful post-incident evidence but does not independently prevent a fully compromised signer or operator from creating a different history.

### Why a hash chain is better than a Merkle tree in V1

A hash chain provides a single ordered commitment that a verifier can replay from the genesis value to a signed terminal checkpoint. It has constant-size state at append time and naturally commits to order. Its limitation is that verifying one specific entry usually requires the relevant chain segment or a trusted checkpointed index; it does not provide logarithmic-size inclusion proofs.

A Merkle tree has a different value proposition. RFC 6962 specifies a binary SHA-256 tree, with `0x00`-prefixed leaf hashes and `0x01`-prefixed internal-node hashes, so leaf and node domains differ. It defines audit paths for inclusion and consistency proofs for append-only history. Those proofs enable an external party to verify an entry or compare roots without downloading every entry. [5]

V1 should choose the chain because the stated baseline is a Drupal module with a central writer, not a public transparency service. The minimal dependency set contains no evidence-backed PHP component that offers the precise RFC 6962 construction plus inclusion and consistency proofs. The reviewed Merkle package is instead a callback-driven, Bitcoin-style fixed-size tree. [17] If a later release promises voter-facing inclusion receipts or third-party transparency monitoring, use a separately designed Merkle-log profile with exact RFC 6962-style vectors, proof verification, root signing, root distribution, and equivocation monitoring. Do not retrofit a generic Merkle library into the V1 chain.

## Dependency/reuse matrix

| Need | Option | Status | Reuse decision | Evidence-based reason |
|---|---|---|---|---|
| Ed25519 signing and verification | PHP `ext-sodium` | **Adopt / required** | Native `sodium_crypto_sign_*` APIs | PHP documents native random Ed25519 keypair and detached sign/verify; RFC 8032 supplies algorithm definition and test vectors. [2] [26] [6] |
| Legacy sodium runtime fallback | `paragonie/sodium_compat` | **Conditional / not V1 default** | Use only under approved legacy profile | It transparently uses ext-sodium when installed but is a pure-PHP fallback; maintainers disclose no formal independent crypto audit and note performance trade-offs. [16] |
| Signed JSON canonical bytes | `mmccook/php-json-canonicalization-scheme` | **Adopt with controls** | One pinned Composer dependency, source/test review | Repository states RFC 8785 compliance and includes tests. Packagist shows one stable release, PHP `^8.1`, no runtime dependencies, and low adoption signals. [18] [19] |
| Direct signature envelope | Detached Ed25519 over JCS bytes | **Adopt** | Native sodium; document byte format | Avoids unneeded JOSE dependency while preserving direct verification of the specified record bytes. [2] [26] |
| JOSE token/interchange envelope | `web-token/jwt-framework` | **Defer / conditional** | Add only for explicit JWS/JWT/JWK contract | Framework documents EdDSA for Ed25519 and is maintained, but V1 internal ledger need not carry a JWS container. [20] [21] |
| Secure random bytes | PHP `random_bytes()` | **Adopt / required** | Native PHP | PHP labels it cryptographically secure and suitable for long-term secrets, with OS CSPRNG sources and failure exceptions. [10] |
| Opaque record identifiers | Drupal `uuid` service | **Adopt** | Core reuse | Drupal core uses `random_bytes(16)` to create UUID v4. No third-party UUID package is needed when ordering is a distinct ledger field. [11] |
| Sortable UUIDs | `ramsey/uuid` v7 | **Defer / conditional** | Add only for external UUIDv7 requirement | Ramsey documents UUIDv7 as time-ordered and sortable. This does not replace an authoritative ledger sequence. [23] [12] |
| Public ledger link digest | PHP `hash('sha256', ..., true)` | **Adopt** | Native PHP | SHA-256 is widely specified and PHP supports raw binary digest output. [14] [27] |
| BLAKE2b digest or keyed MAC | `sodium_crypto_generichash()` | **Conditional** | Native sodium when protocol mandates BLAKE2b | It is BLAKE2b with optional key and variable output, but SHA-256 is selected for V1 public chain interoperability. [4] [15] |
| Confidential payload encryption | XChaCha20-Poly1305 in `ext-sodium` | **Adopt when needed** | Native sodium AEAD | PHP marks it preferred; a fresh 24-byte nonce and AAD are part of the documented API contract. [3] [13] |
| AES-GCM fallback | PHP OpenSSL AEAD | **Do not select by default** | Only for a documented interoperability constraint | PHP supports AEAD tag/AAD but exposes error-prone key/IV parameter behavior; sodium is already required. [24] |
| Append-only commitment | SHA-256 hash chain plus Ed25519 checkpoints | **Adopt** | Application protocol using native hash/sign APIs | Simpler V1 replay and ordered history; requires transactional append and independent checkpoint publication. |
| Inclusion and consistency proofs | RFC 6962-style Merkle tree | **Defer** | No generic PHP tree package in V1 | RFC 6962 provides value when succinct proofs are required; reviewed PHP package does not demonstrate compatible proof semantics. [5] [17] |

## Implementation guardrails and acceptance criteria

The following are **recommendations**, derived from the evidence and the V1 scope rather than direct statements by a source.

| Area | V1 acceptance criterion |
|---|---|
| Dependency control | Lock exact Composer versions and commit `composer.lock`. Review the canonicalizer source and run its upstream tests plus local RFC 8785/V1 vectors in CI. Treat an upstream update as a compatibility change, not an automatic patch. |
| Native capability | Installation fails if `ext-sodium` or `random_bytes()` is unavailable. Do not silently select OpenSSL or a pure-PHP polyfill. |
| Signatures | All signature verification selects keys from a trusted local key-id allowlist. It rejects unknown key IDs, wrong profile IDs, noncanonical payloads, malformed encodings, and any non-Ed25519 algorithm. |
| Canonicalization | The canonicalizer accepts only validated V1 schemas. CI asserts byte-for-byte expected output for all signed record fixtures, including Unicode and number boundary cases. |
| Ledger mutation | Appends serialize on election/ledger scope, enforce a unique monotonic sequence, bind predecessor digest, and retain signed checkpoints. Administrative corrections append compensating events rather than alter past canonical bytes. |
| Key custody | Private signing and encryption keys are not placed in source control, Drupal config export, application logs, or ordinary database rows. The protocol provides key IDs and a documented rotation/revocation process. |
| Encryption | Every AEAD envelope records nonce, ciphertext-with-tag, key ID, and algorithm/profile version. A nonce is generated once per message/key and never reused. |
| Audit | An independent verifier can obtain the public key history, genesis specification, canonicalization/profile specification, ledger records or defined export, and signed checkpoints to replay verification. |

## Caveats outside the library decision

This report narrows the reusable cryptographic building blocks. It does not certify the voting system, provide a cryptographic protocol proof, or resolve election-law, ballot secrecy, coercion resistance, accessibility, eligibility, client compromise, insider risk, denial of service, or operational governance. The most important residual risk is key and server trust: correctly using Ed25519, SHA-256, JCS, and AEAD does not make a compromised vote-capture application trustworthy.

Before a production election, commission an independent security and protocol review that covers the complete election flow, receipt design, data retention, deployment architecture, signing-key custody, administrator separation of duties, incident response, checkpoint publication, and independent verifier implementation. The cited specifications establish API and format facts; the recommendations in this report are scoped engineering conclusions for V1.

## References

[1]: https://www.php.net/manual/en/sodium.installation.php "PHP manual: Sodium installation"
[2]: https://www.php.net/manual/en/function.sodium-crypto-sign-detached.php "PHP manual: sodium_crypto_sign_detached"
[3]: https://www.php.net/manual/en/function.sodium-crypto-aead-xchacha20poly1305-ietf-encrypt.php "PHP manual: sodium_crypto_aead_xchacha20poly1305_ietf_encrypt"
[4]: https://www.php.net/manual/en/function.sodium-crypto-generichash.php "PHP manual: sodium_crypto_generichash"
[5]: https://www.rfc-editor.org/rfc/rfc6962.html "RFC 6962: Certificate Transparency"
[6]: https://www.rfc-editor.org/rfc/rfc8032.html "RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)"
[7]: https://www.rfc-editor.org/rfc/rfc8785.html "RFC 8785: JSON Canonicalization Scheme (JCS)"
[8]: https://www.rfc-editor.org/rfc/rfc7515.html "RFC 7515: JSON Web Signature (JWS)"
[9]: https://www.rfc-editor.org/rfc/rfc8037.html "RFC 8037: CFRG Elliptic Curve Diffie-Hellman and Signatures in JOSE"
[10]: https://www.php.net/manual/en/function.random-bytes.php "PHP manual: random_bytes"
[11]: https://git.drupalcode.org/project/drupal/-/raw/11.x/core/lib/Drupal/Component/Uuid/Php.php "Drupal core: PHP UUID v4 generator"
[12]: https://www.rfc-editor.org/rfc/rfc9562.html "RFC 9562: Universally Unique IDentifiers (UUIDs)"
[13]: https://libsodium.gitbook.io/doc/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction "Libsodium documentation: XChaCha20-Poly1305 construction"
[14]: https://www.php.net/manual/en/function.hash.php "PHP manual: hash"
[15]: https://www.rfc-editor.org/rfc/rfc7693.html "RFC 7693: The BLAKE2 Cryptographic Hash and Message Authentication Code (MAC)"
[16]: https://github.com/paragonie/sodium_compat "paragonie/sodium_compat repository and README"
[17]: https://github.com/pleonasm/merkle-tree "pleonasm/merkle-tree repository and README"
[18]: https://github.com/mmccook/php-json-canonicalization-scheme "mmccook/php-json-canonicalization-scheme repository and README"
[19]: https://packagist.org/packages/mmccook/php-json-canonicalization-scheme "Packagist: mmccook/php-json-canonicalization-scheme"
[20]: https://web-token.spomky-labs.com/the-components/signed-tokens-jws/signature-algorithms.md "JWT Framework documentation: Signature Algorithms"
[21]: https://github.com/web-token/jwt-framework "web-token/jwt-framework repository"
[22]: https://github.com/ramsey/uuid "ramsey/uuid repository"
[23]: https://uuid.ramsey.dev/en/stable/rfc4122/version7.html "ramsey/uuid documentation: Version 7 UUIDs"
[24]: https://www.php.net/manual/en/function.openssl-encrypt.php "PHP manual: openssl_encrypt"
[25]: https://www.php.net/manual/en/function.sodium-bin2base64.php "PHP manual: sodium_bin2base64"
[26]: https://www.php.net/manual/en/function.sodium-crypto-sign-verify-detached.php "PHP manual: sodium_crypto_sign_verify_detached"
[27]: https://csrc.nist.gov/pubs/fips/180-4/upd1/final "NIST FIPS 180-4: Secure Hash Standard"
