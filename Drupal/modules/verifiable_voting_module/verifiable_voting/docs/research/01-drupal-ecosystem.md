# Drupal ecosystem reuse assessment for a verifiable voting module

**Subject:** Drupal ecosystem reuse  
**Author:** Manus AI  
**Research snapshot:** 13 September 2026  
**Scope:** This report evaluates Drupal core APIs and contributed projects as dependencies or integrations for a reusable **verifiable voting** module. It does not prescribe or provide application code.

## Executive conclusion

A reusable verifiable-voting module should keep the **authoritative election record, eligibility decision, cast-vote acceptance rule, tally inputs, and audit evidence** in purpose-built module-owned Drupal content entities and services. Drupal core’s Entity API, Typed Data/Entity Validation facilities, configuration system, locking API, and access control model are suitable foundations for that work. Revision-capable content entities are useful for retaining versions, but a revision history alone is not a claim of tamper evidence or independent verification. [1] [2] [3]

**Do not make Voting API, Rate, or Poll an authoritative election dependency.** Voting API is a generic storage and tabulation framework; its project page expressly says it does not expose end-user voting mechanisms. Its currently listed Drupal 9–11 release is beta and the project page says there are no supported stable releases. The current `Vote` entity source is a non-revisionable `ContentEntityBase` with a floating-point `value`, mutable entity lifecycle methods, and derived-result recalculation. Those documented properties can be useful for ordinary rating applications, but they do not establish a domain-specific, append-only, independently verifiable election record. [4] [5] [6]

Rate is a maintained Voting API ecosystem widget and interaction layer, but features such as AJAX voting and vote undo make it a poor authority for final election casting. Poll is a contributed module, not Drupal core; its Drupal 11-compatible line is alpha, while its listed security-covered stable 1.6 release supports only Drupal 9 and 10. Both are therefore unsuitable as a ground-truth election dependency. [7] [8] [9]

Use Key, Encrypt, and optionally Sodium only for a **clearly bounded cryptographic-at-rest integration**. Key has a current stable, security-policy-covered release and supports file, environment, and external key-provider choices. Encrypt standardizes encryption profiles and exposes the `encryption` service; it does not itself supply an encryption method, and it does not support client-side encryption. Sodium is a current, security-policy-covered Encrypt method with a declared dependency chain to Key, Encrypt, Halite, and PHP. These are positive maintenance and ecosystem signals, not a guarantee of ballot secrecy, voter anonymity, election integrity, or cryptographic-verification correctness. [10] [11] [12] [13]

## Decision labels and evidence discipline

This report uses the following terms.

| Label | Meaning in this assessment |
| --- | --- |
| **Authoritative election dependency** | A core capability suitable for the module’s canonical election data, policy, validation, access, and deterministic processing boundary. The label does not mean that Drupal alone proves election correctness. |
| **Optional integration** | A capability that can serve a bounded, replaceable purpose without becoming the source of truth for accepted ballots or final results. |
| **Unsuitable** | The component should not be relied upon for the authoritative election workflow. It may still be useful elsewhere on a site. |

**Confirmed facts** below are tied to the cited project page, documentation, or maintained source. **Conclusions** are the stated engineering judgment from those facts. A grey-shield statement that stable releases are covered by Drupal’s security advisory policy means that project releases meeting the policy can receive advisories. It is not a certification, a vulnerability-free guarantee, or coverage for alpha, beta, release-candidate, development, or unsupported branches. The Security Team’s policy explicitly limits contributed-project advisories to stable releases in supported major branches. [14]

## Reuse and dependency matrix

| Need | Candidate | Observed evidence | Classification | Reuse recommendation |
| --- | --- | --- | --- | --- |
| Canonical cast records and election-domain history | **Drupal core Content Entity / Entity API** | Core distinguishes content entities from configuration entities; Entity API supports structured fields, validation, access handlers, and revision-capable base classes. `RevisionableContentEntityBase` adds revision log message, owner, and creation time support. [1] [2] | **Authoritative election dependency** | Define election-domain content entities under module ownership. Use revision-capable entities where retaining versions is required, and make the module’s own data/invariant rules—not a generic rating entity—the authority. |
| Data definitions and input constraints | **Core Typed Data and Entity Validation** | Typed Data consistently describes, accesses, and validates available data types. Entity API documentation identifies Entity Validation API and constraints for entity CRUD. [1] [3] | **Authoritative election dependency** | Use typed field definitions and validation constraints for structural rules. Treat them as one enforcement layer; they do not substitute for authorization, transaction, or audit policy. |
| Election policy, reusable defaults, and deployable settings | **Core Configuration API** | Drupal defines configuration as infrequently changed, deployable site information; configuration entities represent lists of settings. `ConfigFactoryInterface::get()` returns immutable configuration, while `getEditable()` is override-free and should not be used for runtime effects. [15] [16] | **Authoritative election dependency** | Keep module settings and reusable policy templates in config. Inject `config.factory` as `ConfigFactoryInterface`; use immutable reads for runtime policy. Do not store changing ballots, cast records, counters, or evidence in configuration. |
| Operational flags and progress markers | **Core State API** | State is a string-keyed store for information that changes frequently or without user intervention; Drupal documents cron timing as an example. [15] [17] | **Optional integration** | Inject `state` as `StateInterface` only for recoverable operational state, such as a last successful maintenance checkpoint. Never treat State as an election ledger, a counter of record, or evidence. |
| Concurrent critical sections | **Core Lock API** | `LockBackendInterface` provides `acquire()`, `wait()`, and `release()` with a finite timeout; locks are request-token scoped and released at request end. [18] | **Authoritative election dependency** | Inject `lock` as `LockBackendInterface` for short contention control around a critical operation. Pair it with durable database constraints/transactions and domain validation; a temporary lock alone is not a durable uniqueness or audit guarantee. |
| Deferred, non-authoritative work | **Core Queue API** | Queues use `QueueFactoryInterface::get()` and `QueueInterface`; core says processing may occur more than once after a lease expiry. Reliable backends provide at-least-once execution and order preservation, not exactly-once processing. [19] [20] | **Optional integration** | Inject `queue` as `QueueFactoryInterface` and use a `QueueWorkerInterface` implementation for projections, notifications, exports, or verification jobs. Make workers idempotent. Do not place initial cast acceptance, canonical tally mutation, or an order-sensitive sole audit step behind a queue. |
| Generic vote/rating schema and aggregation | **drupal/votingapi** | Its stated purpose is standardized storage, retrieval, and tabulation. It does not expose voting mechanisms. The current listed release is `8.x-3.0-beta6` for Drupal 9–11, and the project says it has no supported stable releases. Its current Vote entity uses `ContentEntityBase`, float `value`, a user reference, timestamp, IP hash source, and recalculation hooks. [4] [5] [6] | **Unsuitable** | Do not require `drupal/votingapi` for authoritative elections. If a separate site feature needs ordinary rating data, integrate it outwardly and keep election authority isolated. Do not depend on a beta branch as an election trust boundary. |
| Generic interactive rating controls | **drupal/rate** | Rate 3.3.1 is a listed stable security-policy-covered Drupal 10.2/11 release. It requires Voting API and advertises AJAX voting and undoing votes. [7] [13] | **Optional integration, but unsuitable for authoritative casting** | Do not include Rate in the voting module’s authoritative dependency set. A host site may use it for non-election feedback; election casting needs module-owned workflow and access rules. |
| Multiple-choice site polls | **drupal/poll** (often called “core Poll”) | Poll was removed from Drupal 8 core and continued as a contributed project. Its D11-compatible 2.0.0-alpha5 is alpha; stable 1.6 is security-policy-covered but listed only for Drupal 9/10. [8] [9] [14] | **Unsuitable** | Do not call Poll a core dependency and do not use it as the election authority. Its scope is multiple-choice site polls, not a verifiable-election evidence model. |
| Key material abstraction | **drupal/key** | Key manages sensitive keys and documents configuration, file, environment, and external storage choices. Its 1.22 release is listed stable, security-policy-covered, and compatible with Drupal 9.1–11. [10] [14] | **Optional integration** | If encryption/signing keys are actually required, require `drupal/key:^1.22` (or a version constrained to the host’s supported core range). Use a file, environment, or reviewed external provider; the project page calls its Configuration provider development-only. Do not put production key values in exported config. |
| Encryption-profile abstraction | **drupal/encrypt** | Encrypt requires Key plus at least one EncryptionMethod plugin. It supplies `EncryptService` as the public encrypt/decrypt entry point, while an encryption profile is a config entity linking a key entity and method plugin. It has no client-side encryption support. Its 3.3 release is listed stable, security-policy-covered, and Drupal 10.3/11 compatible. [11] [14] | **Optional integration** | Where a documented threat model requires server-side encryption at rest, require `drupal/encrypt:^3.3`, inject the `encryption` service as `EncryptServiceInterface`, and select profiles by machine name under tightly restricted administration. Do not represent this integration as end-to-end voting or client-side ballot secrecy. |
| Libsodium/Halite encryption method | **drupal/sodium** | Sodium is an Encrypt method using the PHP Sodium extension and Halite. The project page lists version 3.0.2 as stable, security-policy-covered, and Drupal 10.3–12 compatible. The current 3.0.x source `composer.json` declares `php >=8.3`, `drupal/key:^1.0`, `drupal/encrypt:^3.2`, and `paragonie/halite:^5.1`; the project page’s requirements section says PHP 8.1+, so the exact release’s Composer metadata must be the installation authority. [12] [21] [14] | **Optional integration** | Select Sodium only after the host PHP/core matrix is locked and tested. Add `drupal/sodium:^3.0` through Composer rather than separately pinning its transitive Key/Encrypt/Halite dependencies. Resolve the documented PHP-version discrepancy against the chosen release tag and lock file before adoption. |
| Public/consumer entity reads | **Core JSON:API** | JSON:API is a core, zero-configuration HTTP API for Drupal entities. Every entity type and bundle maps to a resource type; it automatically exposes entities and offers no PHP API to change its behavior. It says business rules are outside its scope. [22] [23] | **Optional integration** | Enable only for intentionally exposed entity resources, such as carefully designed public verification artifacts. Treat entity/field access and publication state as the exposure boundary; do not expose cast-record entities for direct generic CRUD and do not rely on JSON:API to implement cast-vote business rules. |
| Command-oriented endpoints and negotiated formats | **Core RESTful Web Services** | REST resources are configuration entities. The REST resource configuration contains enabled HTTP methods, supported authentication providers, and supported formats; the REST resource plugin manager is `plugin.manager.rest`. [24] | **Optional integration** | Prefer a purpose-specific REST resource only when a command endpoint is required and it must apply the module’s own authorization and validation. Configure only needed methods, formats, and authentication. Do not mistake configured transport authentication for election authorization or audit evidence. |
| Operational diagnostics | **Core Logging API / dblog or external PSR-3 logger** | Drupal documents Logging API as object-oriented and PSR-3 compatible. `LoggerChannelFactoryInterface::get($channel)` retrieves a channel, and `addLogger()` attaches PSR-3 loggers. [25] [26] | **Optional integration** | Inject `logger.factory` as `LoggerChannelFactoryInterface` and use a dedicated `verifiable_voting` channel for errors and security-relevant operational events. Route to an operated sink as appropriate. Logs are not the canonical audit trail: the cited API specifies logging interfaces, not immutability, retention, hash chaining, or independent witnessing. Persist required election evidence in module-owned records instead. |

## Detailed findings and concrete API recommendations

### 1. Election authority: rely on core entities, not a rating framework

**Confirmed facts.** Drupal’s Entity API defines content entities for structured user-facing data and configuration entities for shareable site settings. Its documentation identifies entity validation and explicit field definitions. The revision-capable base class provides revision log message, owner, and time fields in addition to content-entity behavior. [1] [2]

**Conclusion.** The reusable module should own the entity types that represent elections, ballot definitions, eligibility decisions, accepted cast records, tally snapshots, and audit artifacts. This is not an instruction to model them in any particular schema. It establishes an authority boundary: generic rate/poll data must not determine an accepted ballot or final tally.

The recommended core contracts are `Drupal\Core\Entity\EntityTypeManagerInterface` through the `entity_type.manager` service, `Drupal\Core\TypedData` field/data-definition facilities, entity validation constraints, and—where a record genuinely needs historical versions—`Drupal\Core\Entity\RevisionableContentEntityBase`. These are core APIs rather than contributed election dependencies. Revisioning retains entity versions; it does not, by itself, make the data append-only or independently verifiable. That latter statement is a conclusion because the documented class supplies revision metadata but makes no such cryptographic or governance guarantee. [2]

> “VotingAPI helps developers who want to use a standardized API and schema for storing, retrieving and tabulating votes for Drupal content.” Its project page immediately adds that the module “does NOT directly expose any voting mechanisms to end users.” [4]

Voting API’s maintained source reinforces the scope difference. Its current `Vote` entity has a generic numeric floating-point value, ordinary content-entity base class, a vote source described as an IP hash, and post-save/post-delete result recalculation. It does not identify itself as a revisionable entity type in that definition. These facts do not prove that Voting API is defective; they do show that it is a generic rating substrate rather than a verified-election protocol or immutable authority. The recommendation is therefore **not to add `drupal/votingapi`** to the authoritative module dependency graph. [6]

Rate depends on Voting API and offers flexible, AJAX-only widgets and undo behavior. Those documented features fit user feedback; they are a poor fit for an authority boundary where the module must make a precise and auditable acceptance decision. Rate can remain a site-level, non-election integration. [7]

Poll has similarly limited scope. Its project calls itself a module for multiple-choice topic polls and the authoritative Drupal change record confirms that Poll left core in Drupal 8. The stated current D11-compatible branch is alpha. Avoid representing its dependency as “core Poll” or treating it as an election engine. [8] [9]

### 2. Validation, configuration, state, and concurrency

**Validation.** Use Typed Data and Entity Validation for values that can be locally validated from a data definition or record. The Typed Data API is explicitly a low-level descriptive, access, and validation API. Treat this as structural validation; domain authorization and event ordering require the module’s own policy services and persistence controls. [3]

**Configuration.** Use `config.factory` (`ConfigFactoryInterface`) for module settings and deployable reusable policy. Drupal’s classification guidance says configuration is relatively infrequent site information and says that information needing deployment from development to live is probably configuration. It also distinguishes configuration from frequently changing state and editor-created content. This supports configuration for feature flags, policy templates, reference settings, and default behavior—not cast votes, running counters, or per-election mutable records. [15] [16]

Inject `ConfigFactoryInterface` rather than using static access. Read runtime settings through `get()`, which returns immutable configuration. The core interface explicitly warns that `getEditable()` should not be used for configuration with runtime effects because it is loaded override-free. For lists of module-owned deployable policies, use a configuration-entity API rather than encoding a growing list in ad hoc simple configuration. [16]

**State.** Use `state` (`StateInterface`) for non-authoritative, recoverable operational markers only. The State API is key-value persistence for information that changes frequently or without user action. If loss or alteration of a value would change election acceptance or result correctness, it does not belong in State. [15] [17]

**Concurrency.** Use `lock` (`LockBackendInterface`) for a short-lived contention boundary. The exact interface exposes `acquire($name, $timeout)`, `wait()`, and `release()`, while noting that locks are cleaned up on a request-token basis. Therefore a lock should complement, not replace, durable uniqueness/integrity controls. This is a conclusion drawn from the interface’s temporary-lock semantics. [18]

### 3. Queues: background processing only, and idempotently

Core’s Queue API is appropriate for work that can be retried safely: generating a public verification projection, producing a signed export, notifying a participant, or recomputing a non-authoritative view. Inject `queue` as `QueueFactoryInterface`, obtain a named `QueueInterface`, and process it through a `QueueWorkerInterface` plugin. [19] [20]

> Drupal documents that when a consumer dies, a leased queue item becomes available again and “the processing code should be aware that an item might be handed over for processing more than once.” [20]

The Queue API also distinguishes reliable from non-reliable backends, but even a reliable backend is documented in at-least-once terms. Thus queues are **not** a durable exactly-once election-casting mechanism or the sole serialization point for a final tally. Queue consumers should be idempotent, and the canonical record must be committed before any optional queued projection is emitted. The idempotence recommendation is the direct engineering consequence of core’s documented duplicate-processing possibility. [20]

### 4. REST and JSON:API: expose evidence deliberately, not ballot CRUD

JSON:API is a strong optional read/API integration because it is in core, maps each entity type and bundle to a resource type, and automatically exposes entity resources. That automatic entity exposure is a reason for restraint: only enable and authorize it for resources that are intentionally safe to disclose. JSON:API supports entity revisions in its HTTP interface, but its own architecture notes that querying a collection of revisions is not yet possible. It also says it does not supply business rules such as account actions. [22] [23]

For a public verification surface, JSON:API may be considered only for explicit, read-only verification artifacts after field/entity access, cacheability, and data minimization are reviewed. Do not expose internal cast records, identity-bearing values, or generic write operations merely because the module has entities. This is a recommendation based on JSON:API’s automatic entity mapping and stated lack of business-rule support. [22] [23]

When an external caller needs a command endpoint rather than CRUD, core REST is the more bounded optional integration. `RestResourceConfig` contains the resource’s methods, formats, and authentication providers, and its resource plugin manager service is `plugin.manager.rest`. Use a purpose-specific, tightly configured resource that delegates to the module’s authority layer; do not treat REST configuration or authentication selection as proof of eligibility or final auditability. [24]

### 5. Key management and encryption: bounded at-rest protection

**Key** is the recommended abstraction if the module needs a key held outside normal configuration. It has a current 1.22 stable security-policy-covered release for Drupal 9.1–11. Its own documentation categorizes configuration storage as development-only, file and environment providers as better, and an external key-management solution as best. That page supports a concrete operational recommendation: production key material should not live in exported configuration, and the host should choose and operate an appropriate external/file/environment provider. [10]

**Encrypt** is suitable as the encryption-profile layer. It requires Key and an encryption method plugin, and it publishes `EncryptService` as the encrypt/decrypt entry point. The service contract is `Drupal\encrypt\EncryptServiceInterface`, exposed as the `encryption` service. Its encryption profiles are config entities that bind a method to a Key entity; the actual key value remains with the Key provider. Encrypt also warns that users with its administrative permission can decrypt arbitrary text using profiles through the test form, so that permission belongs only to a very restricted administrative role. [11]

**Sodium** is an optional method plugin when the host has selected libsodium/Halite through the module’s supported stack. The project page describes symmetric encryption/decryption using the PHP Sodium extension and Halite. Its current 3.0.x source declares dependencies on Key, Encrypt, Halite 5.1+, and PHP >=8.3, while the project requirements page says PHP 8.1+. Treat the Composer metadata for the exact chosen release tag and the locked dependency graph as authoritative for installation compatibility; do not assume the documentation and development branch always have the same PHP floor. [12] [21]

The recommended dependency sets are deliberately small:

| Deployment profile | Composer-level recommendation | Why |
| --- | --- | --- |
| **Authoritative election core** | Drupal core only, constrained to the host’s maintained core line; no `drupal/votingapi`, `drupal/rate`, or `drupal/poll` requirement | Keeps the election authority on module-owned entities and core APIs. |
| **Server-side at-rest encryption, no prescribed method** | `drupal/key:^1.22` and `drupal/encrypt:^3.3`, subject to the site’s core range | Adds key abstraction and encryption profiles without hard-wiring a crypto method. [10] [11] |
| **Server-side at-rest encryption using Sodium** | `drupal/sodium:^3.0` after verifying the selected release’s PHP/core requirements; allow Composer to resolve `drupal/key`, `drupal/encrypt`, and `paragonie/halite` | Sodium source already declares this dependency chain. Pinning duplicate transitive constraints independently creates unnecessary conflict risk. [12] [21] |

Neither Key, Encrypt, nor Sodium makes a Drupal server a client-side cryptographic voting system. Encrypt explicitly says it does not currently support client-side encryption. The modules are appropriate only after a documented threat model says which server-held data requires at-rest protection, who can decrypt it, and how key rotation, backup, recovery, and access review will be operated. [11]

### 6. Logging and audit records must be separate

Drupal logging should be used for observability. Inject `logger.factory` as `LoggerChannelFactoryInterface` and use a module-specific channel such as `verifiable_voting`; the factory returns a registered logger for that channel and supports additional PSR-3 loggers. Core documents the framework as object-oriented and PSR-3 compatible. [25] [26]

That supports operational diagnostics, alerting, and incident investigation. It does **not** establish a canonical election audit trail. The cited logging interfaces make no promise of immutable retention, cryptographic linkage, independent publication, or external witnessing. The conclusion is that required audit evidence must be persisted as module-owned, access-controlled records and any public verification projection must be generated from those records rather than from dblog/syslog entries. A site may independently route logs to a managed external sink, but that operational choice is outside what core’s logging API guarantees. [25] [26]

## Maintenance and security signals

The following is a source-bounded snapshot, not a prediction of future maintenance.

| Component | Current project-page signal observed | Bounded interpretation |
| --- | --- | --- |
| Voting API | 8.x-3.0-beta6 listed for Drupal 9–11; page says stable releases are covered but there are currently no supported stable releases. [4] | The active candidate is beta, and the Security Team policy excludes beta releases from advisories. Do not make it an election trust dependency. [14] |
| Rate | 3.3.1 is listed stable, security-policy-covered, Drupal 10.2/11; project page shows source, maintainers, and CI status. [7] | A positive project-maintenance signal for its stated widget scope, not evidence that Rate supplies election-grade authority. |
| Poll | 2.0.0-alpha5 supports Drupal 9–11; 1.6 is stable/security-covered but Drupal 9/10 only. [9] | Drupal 11 use selects an alpha, which does not receive Drupal Security Team advisories under the stated policy. [14] |
| Key | 1.22 is listed stable/security-policy-covered for Drupal 9.1–11. [10] | Positive security-process and release signal; provider configuration still determines where key material resides. |
| Encrypt | 3.3 is listed stable/security-policy-covered for Drupal 10.3/11. [11] | Positive release signal; security depends additionally on the selected method, key provider, permissions, and external libraries. |
| Sodium | 3.0.2 is listed stable/security-policy-covered; project calls it feature-complete with maintenance fixes only. [12] | Stable, covered component with a limited maintenance posture; installation also depends on the PHP extension and Halite external library. |

Drupal’s policy is especially important for encryption dependencies: security advisories are issued only for Drupal.org-hosted projects, and the policy says it does **not** issue advisories for external libraries required by a contributed project. Composer update/advisory processes must therefore cover external packages such as Halite independently of Drupal project coverage. [14]

## Final recommendations

1. **Make the module’s own content entities and domain services the authority.** Adopt core Entity API, Typed Data/Entity Validation, `entity_type.manager`, `config.factory`, and `lock` as the baseline integration contracts. Use revision-capable entities when version history is needed, but do not overstate revisions as tamper-proof evidence. [1] [2] [3] [16] [18]

2. **Exclude `drupal/votingapi`, `drupal/rate`, and `drupal/poll` from authoritative requirements.** Their documented generic rating/poll scope, mutable interaction patterns, and release-state evidence do not support treating them as a verifiable-election trust boundary. Rate may be a non-election UI integration; Voting API and Poll should not define cast records or final results. [4] [6] [7] [8] [9]

3. **Use Config for deployable policy, State only for operational state, and Queue only for idempotent background work.** No accepted cast, authoritative counter, tally input, or required audit artifact should depend only on State or queued execution. [15] [17] [20]

4. **Expose external interfaces deliberately.** Use JSON:API only for intentionally public/readable entity resources with reviewed entity and field access. Use a purpose-specific core REST resource for command behavior when needed; configure minimum methods, formats, and authentication, then apply module-owned authorization and validation. [22] [23] [24]

5. **Make Key/Encrypt/Sodium an optional, threat-model-driven profile.** For server-side encryption at rest, use Key plus Encrypt, and choose Sodium only after reconciling the exact Composer release’s PHP/core requirements. Keep production key material out of configuration and strictly limit encryption-administration privileges. [10] [11] [12] [21]

6. **Separate operational logging from audit evidence.** Use `logger.factory` and a dedicated channel for observability. Persist required election evidence independently in module-owned records; do not claim dblog, syslog, revisions, queues, or encryption profiles alone supply a verifiable audit trail. [2] [20] [25] [26]

## References

[1]: https://www.drupal.org/docs/drupal-apis/entity-api "Entity API | Drupal.org"
[2]: https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Entity%21RevisionableContentEntityBase.php/class/RevisionableContentEntityBase/11.x "RevisionableContentEntityBase class | Drupal API"
[3]: https://www.drupal.org/docs/drupal-apis/typed-data-api "Typed Data API | Drupal.org"
[4]: https://www.drupal.org/project/votingapi "Voting API project | Drupal.org"
[5]: https://www.drupal.org/drupal-security-team/security-advisory-process-and-permissions-policy "Security advisory process and permissions policy | Drupal.org"
[6]: https://git.drupalcode.org/project/votingapi/-/raw/8.x-3.x/src/Entity/Vote.php "Voting API Vote entity source, 8.x-3.x | Drupal GitLab"
[7]: https://www.drupal.org/project/rate "Rate project | Drupal.org"
[8]: https://www.drupal.org/node/2116417 "Modules and themes removed from core in Drupal 8 | Drupal.org"
[9]: https://www.drupal.org/project/poll "Poll project | Drupal.org"
[10]: https://www.drupal.org/project/key "Key project | Drupal.org"
[11]: https://www.drupal.org/project/encrypt "Encrypt project | Drupal.org"
[12]: https://www.drupal.org/project/sodium "Sodium project | Drupal.org"
[13]: https://git.drupalcode.org/project/rate/-/blob/3.3.x/composer.json "Rate 3.3.x Composer manifest | Drupal GitLab"
[14]: https://www.drupal.org/drupal-security-team/security-advisory-process-and-permissions-policy "Drupal Security Team security advisory process and permissions policy"
[15]: https://www.drupal.org/docs/drupal-apis/configuration-api/overview-of-configuration-vs-other-types-of-information "Overview of Configuration versus other types of information | Drupal.org"
[16]: https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Config%21ConfigFactoryInterface.php/interface/ConfigFactoryInterface/11.x "ConfigFactoryInterface | Drupal API"
[17]: https://api.drupal.org/api/drupal/core%21core.api.php/group/state_api/11.x "State API | Drupal API"
[18]: https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Lock%21LockBackendInterface.php/interface/LockBackendInterface/11.x "LockBackendInterface | Drupal API"
[19]: https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Queue%21QueueFactoryInterface.php/interface/QueueFactoryInterface/11.x "QueueFactoryInterface | Drupal API"
[20]: https://api.drupal.org/api/drupal/core%21core.api.php/group/queue/11.x "Queue operations | Drupal API"
[21]: https://git.drupalcode.org/project/sodium/-/blob/3.0.x/composer.json "Sodium 3.0.x Composer manifest | Drupal GitLab"
[22]: https://www.drupal.org/docs/core-modules-and-themes/core-modules/jsonapi-module "JSON:API module | Drupal core documentation"
[23]: https://api.drupal.org/api/drupal/core%21modules%21jsonapi%21jsonapi.api.php/group/jsonapi_architecture/11.x "JSON:API Architecture | Drupal API"
[24]: https://api.drupal.org/api/drupal/core%21modules%21rest%21src%21Entity%21RestResourceConfig.php/class/RestResourceConfig/11.x "RestResourceConfig class | Drupal API"
[25]: https://www.drupal.org/docs/drupal-apis/logging-api "Logging API | Drupal.org"
[26]: https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Logger%21LoggerChannelFactoryInterface.php/interface/LoggerChannelFactoryInterface/11.x "LoggerChannelFactoryInterface | Drupal API"
