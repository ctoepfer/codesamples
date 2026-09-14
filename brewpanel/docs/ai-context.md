# Pacific BrewIO — AI context summary

A short, stable reference for an AI agent, retrieval system, or new contributor that needs the essential facts without reading the full architecture document. Public facts only — nothing here depends on `docs/hardware_internal/`. If a claim would require citing internal research, it doesn't belong in this file.

## What Pacific BrewIO is

A planned open-source project from Pacific Brewing Supplies: a small shared core plus independently-installable Python packages, one per piece of homebrewing hardware. **Not published yet.** Today it exists only as the `hardware/` module inside [BrewPanel](../), which is the application that will consume these packages once extracted.

## Package map

```text
pacific-brewio-core          shared protocols, value types, safety-gate concepts
pacific-brewio-simulator     pure-software fake controller, no physical hardware
pacific-brewio-tilt          Tilt Hydrometer, passive BLE, read-only
pacific-brewio-ispindel      iSpindel, local HTTP receiver, read-only
pacific-brewio-grainfather   Grainfather legacy controller, planned
pacific-brewio-rapt          RAPT devices via official REST API, planned
pacific-brewio-brewpiless    BrewPiLess, open-source firmware, planned
pacific-brewio-brewblox      Brewblox/BrewPi Spark, planned
pacific-brewio-plaato        Plaato, official API, read-only once implemented
pacific-brewio-inkbird       Inkbird, research only — no implementation path yet
```

Proposed import namespace: `brewio.<device>` (e.g. `from brewio.tilt import TiltScanner`) — **not yet checked for name availability or conflicts.**

Current implementation status, package independence rules, and everything else in this list is defined authoritatively in [`docs/pacific-brewio-architecture.md`](pacific-brewio-architecture.md); this file only summarizes it.

## Core concepts

- **Typed API and machine-describing metadata are one implementation, not two.** Every operation is callable as normal typed Python and describable via introspection (`driver.describe()`, `driver.get_capabilities()`, `driver.get_operations()`).
- **`OperationDescriptor`** is the unit of machine-readable operation metadata: schema, read-only/write, risk level, confirmation and operator-presence requirements, preconditions, error codes.
- **Capability manifest** (`manifest.json` per package) declares what a driver actually supports — never an aspirational list.
- **Structured error codes** are shared across every package (`not_connected`, `discovery_timeout`, `safety_confirmation_required`, `unsafe_device_state`, and others — full list in the architecture doc) so failures are machine-actionable, not just human-readable strings.

## Safety rules that apply to every caller, human or automated

- Installing a package never enables hardware; importing a module never scans or connects.
- Discovery is explicit and bounded, and never connects on its own.
- Reads and writes are distinguishable at the type/descriptor level.
- State-changing operations never run as a side effect of an unrelated call.
- High-risk operations require an approval/confirmation context enforced by the implementation itself.
- Secrets never appear in descriptors, prompts, logs, or returned errors.
- Every state-changing attempt — approved, denied, succeeded, or failed — is audited.
- An AI adapter is a translation layer over the typed API; it cannot bypass confirmation or audit behavior. See [`docs/AI_INTEGRATION.md`](AI_INTEGRATION.md) for the full integration path.

The full rule set (20 rules) lives in the architecture doc's AI-safe execution model section.

## Status-word meanings

| Status | Meaning |
|---|---|
| Stable | Verified on real hardware across multiple firmware/model combinations; safe for routine use within documented scope. |
| Experimental | Implemented and tested, limited coverage or a young API; breaking changes more likely. |
| Read-only | Qualifier: no actuator/write path exists, on the hardware or in the implementation. |
| Partial | Some capabilities implemented and tested; others (often actuators) are not. |
| Planned | Shape defined, protocol research exists, no working driver yet. |
| Research only | Interoperability research exists but no implementation path yet (e.g. missing a private schema or authenticated session). |
| Unsupported | Explicitly not supported and not currently planned. |

## BrewPanel vs. Pacific BrewIO

Pacific BrewIO owns discovery, transport, protocol, connection lifecycle, normalized readings, capability/operation descriptions, device errors, and low-level safety metadata. BrewPanel owns enabled-device configuration, secrets, connection policy, orchestration, recipes, sessions, the GUI, human approvals, and cross-device coordination. Full boundary in the architecture doc's "BrewPanel relationship" section.

## Authoritative documents

- [`docs/pacific-brewio-architecture.md`](pacific-brewio-architecture.md) — full architecture, package independence rules, `OperationDescriptor` worked examples, capability manifest shape, AI-safe execution model, error codes, licensing/provenance plan, BrewPanel ownership boundary.
- [`docs/AI_INTEGRATION.md`](AI_INTEGRATION.md) — how to build an adapter without bypassing safety.
- [`docs/hardware/README.md`](hardware/README.md) — public per-device status and the documentation-promotion process.
- [`docs/hardware/GUIDE_TEMPLATE.md`](hardware/GUIDE_TEMPLATE.md) — required structure for a public per-device guide.
- [`docs/hardware/PUBLICATION_CHECKLIST.md`](hardware/PUBLICATION_CHECKLIST.md) — the review gate a finding must pass before publication.
- [`docs/hardware_internal/README.md`](hardware_internal/README.md) — internal research collection (not public, not authoritative for compatibility claims).
