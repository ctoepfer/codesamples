# Architecture Research Decision Record: Verifiable Voting Drupal Module

| Field | Decision |
|---|---|
| **Status** | Proposed V1 architecture, pending implementation assurance gates |
| **Scope** | A reusable Drupal module for a constrained verifiable-voting pilot |
| **Primary decision** | Use Drupal as the authoritative workflow and public-evidence application layer, while isolating election cryptography, private key custody, proof verification, and decryption from Drupal. |
| **V1 deployment claim** | Suitable only for a non-binding, organizational, low-coercion pilot after the listed review gates. It is **not** a certification, public-election, coercion-resistance, or anonymity claim. |

## Decision and rationale

The module will be built on **Drupal core entities, validation, configuration, transactions, and locks**, rather than generic poll or rating modules. Drupal owns the business record of an election, the approved configuration, workflow transitions, authorization decisions, and publication of selected public evidence. Core’s Entity API, Typed Data, and validation facilities provide an appropriate basis for structured, revision-capable domain records, but neither revisions nor logs create tamper-evident election evidence by themselves. [1] [2]

V1 will use a **separately deployed cryptographic component** for encrypted-ballot construction, ballot-validity evidence, cryptographic admission verification, homomorphic aggregation, and threshold-decryption evidence. Drupal/PHP is therefore application infrastructure and a verifier/publisher of externally produced evidence, not the cryptographic trust boundary. This split follows the useful architectural direction of ElectionGuard-style election records: freeze the election definition, retain encrypted ballot and tally evidence, and enable independent reproduction rather than asking a single web application to be trusted. [16] [17]

The public evidence ledger will use a versioned canonical record format, SHA-256 hash chaining, and Ed25519-signed checkpoints. RFC 8785 JSON Canonicalization Scheme (JCS) bytes make the signed message reproducible across implementations. A hash chain is selected over a Merkle tree for V1 because a single, ordered Drupal writer can replay it simply; it does **not** provide third-party inclusion or consistency proofs. Checkpoints must be independently published, and the final record must be reproduced by independently operated monitors before a final result is represented as verified. [12] [13] [15] [23]

> **Architecture boundary.** A successful Drupal transaction and a signed public-ledger checkpoint establish application-record integrity only within the declared trust model. They do not alone establish ballot secrecy, cast-as-intended verification, recorded-as-cast verification, correct tallying, eligibility, or election legitimacy. Those properties require the specified external evidence, independent verification, governance, and operational controls.

## Exact V1 boundary

V1 is intentionally narrow. It supports one frozen election manifest with **simple binary or approval contests with bounded selections**. A voter either casts an encrypted ballot through the approved flow or chooses a challenge/spoil path where supported by the selected cryptographic component. The system publishes a tracker and a canonical public record containing the frozen manifest, protocol/profile versions, public keys and key history, accepted ballot evidence, ledger checkpoints, tally artifacts, and final verification inputs. The tally design is limited to an additive homomorphic aggregate with threshold decryption; trustees must not decrypt individual cast ballots. [16] [17] [18]

V1 may be used only where its operating environment is explicitly assessed as low coercion. It has no support for write-ins, ranked or graded ballots, weighted voting, revoting, mixnets, anonymous zero-knowledge eligibility, mobile-device assurance, or public-election suitability. Helios likewise warns that browser-based online voting is appropriate only in limited, low-coercion circumstances; this record treats that limitation as a deployment constraint, not as a problem solved by encryption or a public ledger. [19]

Before opening an election, the installation must freeze the manifest, contest constraints, approved protocol and verifier version, JCS package version, hash/signature algorithms, public-key identifiers, endpoint schema, retention schedule, and checkpoint publication channels. Changes after opening require a new election or a formally versioned, publicly recorded abort/restart procedure. Drupal configuration is appropriate for deployable policy and defaults, not mutable ballots, counters, evidence, or private keys.

## System split and authoritative records

| Concern | Drupal module responsibility | External component or principal | V1 rule |
|---|---|---|---|
| Election administration | Define, validate, freeze, and publish the manifest; enforce workflow transitions and role access. | Election authority approves the manifest. | Manifest and protocol profile are immutable after opening. |
| Eligibility and one-vote control | Consume only a narrowly scoped authorization result and atomically prevent reuse of its one-time identifier. | Credential/eligibility authority validates voter eligibility. | V1 does not claim anonymous eligibility or cryptographic unlinkability from the eligibility authority. |
| Ballot formation and cast-as-intended evidence | Present the workflow and store the returned evidence reference. | Cryptographic client/service constructs encrypted ballots and any challenge/spoil or well-formedness evidence. | Drupal must not accept an opaque “valid” flag without a versioned, independently verifiable artifact. |
| Admission-proof verification | Enforce a fixed request/attestation schema and retain the acceptance decision. | Dedicated verifier service, selected only after production-assurance review. | No PHP Groth16/PLONK verifier and no bespoke SNARK circuit in V1. |
| Canonical evidence ledger | Allocate a durable monotonic sequence; append module-owned evidence records transactionally; canonicalize and publish records. | Independent monitors retain and replay the record. | A database revision, queue, or application log is not a substitute for public evidence. |
| Checkpoint signing | Verify signatures and publish signed checkpoints. | Isolated signing service or governed key custodian holds the checkpoint private key. | Drupal must not be the sole holder of a checkpoint-signing secret. |
| Tally and decryption | Publish input set, aggregate artifacts, trustee evidence, and verifier output. | Cryptographic tally component and independent threshold trustees. | Individual cast ballots are never decrypted. |
| Public verification | Provide read-only evidence access and tracker UI. | Independently operated verifier/monitor reproduces the tally. | A Drupal “verified” label is insufficient without reproducible artifacts. |

The module’s canonical records should be module-owned content entities such as `Election`, `ElectionManifest`, `BallotAcceptance`, `LedgerEntry`, `Checkpoint`, `TallyArtifact`, `TrusteeArtifact`, and `VerificationRun`. Their field definitions must distinguish public evidence, restricted operational metadata, and confidential data. Entity revisions preserve operational history, but the canonical evidence sequence, prior digest, current digest, record version, and signature/checkpoint reference are the protocol-level audit inputs.

Drupal must allocate the ledger sequence and append the evidence record in the same durable transaction that records acceptance. Database uniqueness constraints and state-transition checks are required. `LockBackendInterface` is only a short-lived concurrency aid because its lease is temporary; it cannot replace transactional integrity. [1] Core queues may produce duplicate work after a lease expires, so notifications, exports, projections, and checkpoint publication must be idempotent and must never be the sole authority for casting or tallying. [3]

## Dependency and reuse matrix

| Need | Decision | Reuse / implementation boundary | V1 controls and exclusion rationale |
|---|---|---|---|
| Canonical election domain records | **Adopt** | Drupal core Content Entity API, Typed Data, validation, Config API, and Lock API. [1] [2] | Module-owned schema, transactional state machine, durable constraints, and explicit access checks. Revision history is not tamper evidence. |
| Operational state and background work | **Use narrowly** | State API for recoverable markers; Queue API for idempotent exports, notifications, and projections. [3] | Never store the election ledger, cast authority, tally inputs, or evidence solely in State or Queue. |
| Generic voting, ratings, and poll modules | **Do not require** | `drupal/votingapi`, `drupal/rate`, and `drupal/poll` remain outside the authoritative path. [4] [5] [6] | Their generic mutable interaction models and project maturity do not establish election evidence. Rate may be used only for unrelated non-election site features. |
| Public evidence HTTP reads | **Adopt selectively** | Read-only JSON:API exposure for reviewed entity resources, or purpose-specific REST resources. [9] | No generic CRUD for casting, acceptance, or tally. Configure minimal methods, formats, authentication, and entity/field access. |
| Operational observability | **Adopt, non-authoritative** | `logger.factory` and Drupal logging. | Logs assist diagnosis only; they provide no immutable retention, cryptographic linkage, or independent witnessing. |
| JCS serialization | **Adopt with control** | One exact-pinned `mmccook/php-json-canonicalization-scheme` Composer release. [12] | Pin the reviewed version in `composer.lock`; run upstream tests, RFC 8785 fixtures, and protocol-byte fixtures in continuous integration. |
| Signatures and secure random | **Require** | Native PHP `ext-sodium` for Ed25519 verification/signatures and PHP `random_bytes()`; Drupal UUID v4 only for opaque identifiers. [10] [11] [13] | Installation fails closed without `ext-sodium`. A separate monotonic ledger sequence, not UUID order, determines canonical order. |
| Hash chain | **Adopt** | `hash('sha256', $bytes, true)` over versioned canonical bytes. [15] | Preserve raw binary digests and algorithm version. Do not mix hash algorithms in a chain. |
| Confidential fields at rest | **Conditional** | XChaCha20-Poly1305 only where a documented threat model requires it; optional Key + Encrypt integration for server-side key abstraction. [7] [8] [14] | Use a fresh 24-byte nonce, authenticated metadata, key ID, and encryption-profile version. This is not end-to-end ballot secrecy. Production key material is not exported Drupal configuration. |
| Election cryptography and proof checks | **External required** | Narrow, authenticated verifier and cryptographic ballot/tally service. [16] [17] [21] | Fix schemas, resource limits, protocol versions, and signed attestations. Publish raw artifacts for local/offline independent verification. |
| Zero-knowledge circuits and anonymous membership | **Defer** | No Circom, circomlib, snarkJS, Semaphore, Groth16, PLONK, or FFLONK dependency in V1. [24] [25] [26] | A future use requires a formal statement, artifact pinning, ceremony/SRS evidence where applicable, circuit review, reproducible builds, fuzzing, and independent vectors. |
| Merkle transparency proofs | **Defer** | No generic PHP Merkle dependency. [23] | Reconsider only when compact independently verifiable inclusion and consistency proofs are a stated requirement. |
| JOSE and compatibility libraries | **Defer / conditional** | No default `web-token/jwt-framework`, `paragonie/sodium_compat`, or `ramsey/uuid`. | Add only for a documented interoperability or legacy-platform requirement after a separate review. |

## Cryptographic and publication protocol

Each public ledger entry must have a protocol version, immutable election identifier, monotonic sequence, entry type, canonical payload, prior digest, current SHA-256 digest, public-key identifier where applicable, and an evidence locator. The digest is computed over a precisely versioned byte layout; signatures are detached Ed25519 signatures over JCS-canonicalized, versioned record or checkpoint messages. Ed25519 detached signing and verification are provided by native sodium, while RFC 8032 supplies the underlying algorithm specification. [10] [13]

A checkpoint binds a ledger position and digest to the election and protocol version. Its signer identity, public key, key history, timestamp source, publication channels, and signature must be published. At least one channel must be independently controlled from the Drupal deployment. The expected monitor procedure is to retrieve the published record, re-canonicalize entries, recompute the chain, verify checkpoint signatures, validate ballot/tally artifacts using the selected external verifier, and reproduce the result. A checkpoint is evidence of the signing key’s statement; it is not proof that the signer was honest or that an omitted record never existed before independent publication.

The authoritative private key material for ballot decryption belongs to separately governed trustees. Key generation, share custody, rotation, compromise response, destruction, trust anchors, and ceremony records require a documented key-management plan. NIST guidance treats key management as a lifecycle discipline, not merely encrypted storage. [22] Drupal Key and Encrypt may protect bounded server-side operational secrets when justified, but cannot replace trustee separation or establish end-to-end secrecy. [7] [8]

## Security claims, non-goals, and operational gates

The module may claim only that it implements the reviewed V1 workflow and publishes the specified evidence once the release gates are met. It must **not** claim certification, legal validity, public-election readiness, coercion resistance, endpoint integrity, universal accessibility, anonymity, resistance to traffic analysis, prevention of eligibility fraud, or availability under denial-of-service. Cryptographic controls do not cure malware on the voter device, compromised administrator accounts, insecure credential issuance, coercion, operational collusion, or an unavailable service. Independent role separation is therefore required among credential authority, ballot acceptance, trustees, Drupal administrators, verifier operators, and monitors. Belenios provides a useful operational reference for this division of duties, but does not confer assurance on this implementation. [20]

The V1 production gate requires a written threat model; fixed cryptographic/profile versions; a review of the external verifier and its resource limits; signed test vectors for valid and invalid ballot/evidence cases; end-to-end replay tests; key ceremonies and trustee procedures; access-control tests; incident, abort, and recovery procedures; independent monitor rehearsal; and a documented deployment assessment for coercion, privacy, availability, and applicable legal requirements. Privileged service endpoints require authenticated TLS, endpoint-level authorization, strict schema validation, and size/time/resource limits. [21]

## Privacy and linkability review

V1 treats privacy as a data-flow risk rather than inferring it from encryption. Encrypted ballots prevent neither correlation nor coercion by themselves. The following review is a pre-opening requirement and must identify actual controllers, processors, logs, retention periods, and release thresholds for the deployment.

| Data flow or artifact | Linkability / disclosure risk | Required V1 control | Residual limitation that must be disclosed |
|---|---|---|---|
| Eligibility event to ballot submission | A session, account, authorization identifier, IP address, timestamp, or support record can connect a voter to a tracker or ciphertext. | Keep credential authority and ballot/evidence operations separate; use one-time opaque authorization identifiers; do not place voter identity in public evidence; minimize and time-limit operational logs. | **No anonymity or cryptographic unlinkability claim.** A trusted authority or colluding services may correlate events. |
| Public tracker and receipt | A tracker may prove that an encrypted ballot was recorded; screenshots, timing, or a voter’s device may become coercion material. | Publish only the minimum tracker/evidence fields; explain the receipt model; prohibit use in high-coercion contexts. | V1 is not coercion-resistant and does not prevent vote-selling or forced voting. |
| Public ledger ordering and timestamps | Sequence, timing, contest choice pattern, and small cohorts can identify or infer voter behavior. | Avoid publishing identity, request metadata, precise unnecessary timestamps, and user-agent/network data; apply an approved release policy and aggregation thresholds. | Metadata and small-cell inference remain possible, especially for small elections. |
| Encrypted ballot, proof, and tally artifacts | Persistent ciphertexts and malformed or version-distinct artifacts may support future correlation or parsing attacks. | Freeze schemas; validate strictly in the external verifier; publish only reviewed public fields; version all cryptographic artifacts. | Encryption does not conceal network metadata or protect against endpoint compromise. |
| Drupal logs, analytics, backups, and support tickets | Operational systems can retain identity-to-submission correlations beyond the election. | Disable unnecessary analytics on voting routes; segregate and restrict logs; encrypt justified confidential fields; test backup access and deletion/retention procedures. | Administrators with authorized access remain a trust and governance risk. |
| Tally publication | Small totals or contest combinations may reveal preferences. | Predefine minimum reporting thresholds, suppression/aggregation rules, and publication timing. | Suppression can reduce transparency and may be insufficient in very small populations. |
| Trustee and administrator metadata | Key-ceremony, access, and service telemetry can expose participants or create targeting risks. | Least privilege, separate principals, protected administrative records, and incident procedures. | Governance and insider-risk controls remain necessary. |

## Later phases and explicit deferrals

A subsequent phase may evaluate anonymous eligibility using a scoped nullifier and membership proof only after a voting-specific protocol review. The public inputs would need to bind the exact election context, frozen manifest, credential-root version, nullifier scope, nullifier, and encrypted-ballot commitment; nullifier uniqueness would need an atomic durable constraint. Semaphore is a general anonymous-interaction protocol, not a complete election system, so its adoption would not eliminate the required election-design review. [26]

A separate research phase may evaluate PLONK or another proof system only after publishing the formal circuit statement, reviewing every circuit dependency, pinning compiler and proving artifacts, documenting SRS/ceremony evidence, obtaining reproducible builds and independent test vectors, fuzzing verifier boundaries, and commissioning an appropriate assurance review. Groth16 remains deferred unless a circuit-specific ceremony is governed. FFLONK is excluded from security-critical use while its implementation is designated beta. [24] [25]

A later transparency-log phase may replace or supplement the linear hash chain with an RFC 6962-style Merkle construction when third-party inclusion and consistency proofs are explicit requirements. That phase must define proof semantics, tree-head signing, storage consistency, verifier behavior, and recovery procedures; a generic Merkle library is not evidence of compatible election-audit proofs. [23]

## Decision outcome

This record selects a deliberately conservative V1: **Drupal is the reusable workflow and evidence-publication module; external, independently reviewable components carry the cryptographic election boundary; and public evidence plus independent monitoring are mandatory for any verifiability representation.** The resulting module is reusable because its Drupal domain model, protocol profile, evidence schema, and service boundary can be retained while cryptographic services evolve. Its deployment suitability remains contingent on the stated threat model, privacy review, key governance, independent verification, and jurisdiction-specific assessment.

## References

[1]: https://www.drupal.org/docs/drupal-apis/entity-api "Drupal Entity API"
[2]: https://www.drupal.org/docs/drupal-apis/typed-data-api "Drupal Typed Data API"
[3]: https://api.drupal.org/api/drupal/core%21core.api.php/group/queue/11.x "Drupal Queue operations"
[4]: https://www.drupal.org/project/votingapi "Voting API project"
[5]: https://www.drupal.org/project/rate "Rate project"
[6]: https://www.drupal.org/project/poll "Poll project"
[7]: https://www.drupal.org/project/key "Key project"
[8]: https://www.drupal.org/project/encrypt "Encrypt project"
[9]: https://api.drupal.org/api/drupal/core%21modules%21jsonapi%21jsonapi.api.php/group/jsonapi_architecture/11.x "Drupal JSON:API Architecture"
[10]: https://www.php.net/manual/en/sodium.installation.php "PHP Sodium installation"
[11]: https://www.php.net/manual/en/function.random-bytes.php "PHP random_bytes"
[12]: https://www.rfc-editor.org/rfc/rfc8785.html "RFC 8785: JSON Canonicalization Scheme"
[13]: https://www.rfc-editor.org/rfc/rfc8032.html "RFC 8032: Edwards-Curve Digital Signature Algorithm"
[14]: https://libsodium.gitbook.io/doc/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction "Libsodium XChaCha20-Poly1305 construction"
[15]: https://csrc.nist.gov/pubs/fips/180-4/upd1/final "NIST FIPS 180-4: Secure Hash Standard"
[16]: https://electionguard.vote/concepts/Verifiability/ "ElectionGuard: Creating a Verifiable Election"
[17]: https://electionguard.vote/spec/ "ElectionGuard Official Specifications"
[18]: https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=905908 "Performance Requirements for End-to-End Verifiable Elections"
[19]: https://vote.heliosvoting.org/faq "Helios Voting FAQ"
[20]: https://www.belenios.net/instructions.html "Belenios: Who Does What During a Belenios Election?"
[21]: https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html "OWASP REST Security Cheat Sheet"
[22]: https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final "NIST SP 800-57 Part 1 Rev. 5: Recommendation for Key Management"
[23]: https://www.rfc-editor.org/rfc/rfc6962.html "RFC 6962: Certificate Transparency"
[24]: https://github.com/iden3/circom "Circom: Circuit Compiler for ZK Proving Systems"
[25]: https://github.com/iden3/snarkjs "snarkJS: JavaScript and WebAssembly zkSNARK and PLONK Implementation"
[26]: https://github.com/semaphore-protocol/semaphore "Semaphore: a Zero-Knowledge Protocol for Anonymous Interactions"
