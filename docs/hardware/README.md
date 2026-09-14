# Pacific BrewIO — Hardware Support

This is the **public documentation collection** for **Pacific BrewIO**, a planned open-source project from Pacific Brewing Supplies that packages standardized, safety-conscious hardware support for homebrewing (and adjacent) equipment as small, independently-installable Python libraries.

**Pacific BrewIO does not exist as published packages yet.** Today, everything described here lives inside [BrewPanel](../../brewpanel/)'s `hardware/` module. This directory documents what's actually implemented and tested *right now*, and the plan for extracting it — see [`docs/pacific-brewio-architecture.md`](../pacific-brewio-architecture.md) for the full architecture and migration plan.

## What this directory is — and is not

- **This is the public compatibility promise.** Every claim here has been reviewed against [`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) before landing — technical accuracy, current-model applicability, evidence quality, safety classification, and licensing/provenance are all checked before a fact moves here.
- **This is not the internal research notebook.** Detailed static-analysis findings, raw protocol traces, evidence tiers, and unresolved unknowns live in [`docs/hardware_internal/`](../hardware_internal/README.md), which is intentionally excluded from Git and from public distribution. A public guide describes the *supported library interface and its verified behavior* — it does not reproduce the research that got there.
- **Protocol compatibility is not vendor endorsement.** Documenting how to talk to a Grainfather, a RAPT device, or a Tilt hydrometer does not mean Pacific Brewing Supplies is affiliated with, endorsed by, or partnered with Grainfather, RAPT, Tilt, or any other vendor named in this collection. Trademarks belong to their respective owners.
- **Device support varies by model, hardware revision, and firmware.** A capability confirmed on one unit is not guaranteed on every unit of the same product line. Every status below reflects what has actually been implemented and tested, not what a vendor's marketing claims their product line supports.

## Status vocabulary

| Status | Meaning |
|---|---|
| **Stable** | Implemented, tested against real hardware across multiple firmware/model combinations, and considered safe for routine use within its documented scope. |
| **Experimental** | Implemented and tested, but with limited hardware/firmware coverage, a young API, or both. Expect rough edges; breaking changes are more likely than in Stable. |
| **Read-only** | A qualifier, not a standalone maturity level — this package/capability only reads telemetry; it has no actuator/write path (either because the hardware itself has none, or because write support isn't implemented). |
| **Partial** | Some capabilities are implemented and tested; others (often the higher-risk actuator ones) are not. Read each package's guide for exactly which capability falls in which bucket. |
| **Planned** | Not yet implemented as a working driver, but the shape (capability declarations, configuration schema, discovery behavior) is defined and the underlying protocol research exists. No working connection or read path exists yet. |
| **Research only** | Interoperability research exists, but there's no defined implementation path yet — usually because a vendor's own protocol requires information (a private schema, an authenticated cloud session) that hasn't been obtained. |
| **Unsupported** | Explicitly not supported and not currently planned. |

## Safety expectations

Pacific BrewIO packages that touch actuators (heaters, pumps, timers, firmware) are being designed, from day one, around the safety posture already implemented in BrewPanel's hardware layer: read operations are distinguishable from writes at the type level, every state-changing operation requires explicit confirmation, and installing or importing a package never causes it to scan, connect, or send anything on its own. See [`docs/pacific-brewio-architecture.md`](../pacific-brewio-architecture.md) section on the AI-safe execution model for the full rule set — those rules apply to *every* caller, human or automated, not just AI agents.

**No document in this collection is authorization to operate brewing equipment unsafely.** Read a guide's "Safety and side effects" section before automating anything that heats, pumps, or otherwise actuates real equipment.

## How documentation is promoted

1. A finding starts in [`docs/hardware_internal/`](../hardware_internal/README.md) as static-analysis or open-source-firmware research.
2. Someone implements and tests a driver against real hardware (or, for a fully open-source device, verifies the implementation directly against upstream source).
3. The finding — and *only* the finding relevant to what was actually implemented — goes through [`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md).
4. A public guide (see [`GUIDE_TEMPLATE.md`](GUIDE_TEMPLATE.md)) is written describing the supported interface, not the research trail. Unpublished internal detail is never part of the compatibility promise.

## Current status

Reflects what's implemented and tested in BrewPanel today — nothing here has been packaged as an independent Pacific BrewIO distribution yet (see the architecture doc for the extraction plan). Read/write refers to whether the described capability is telemetry-only or includes actuator control.

| Package (planned name) | Status | Read/Write | Notes |
|---|---|---|---|
| `pacific-brewio-core` | Planned | n/a | Shared capability protocols, value types, and safety-gate concepts. Exists today as `brewpanel.hardware`/`brewpanel.core`; not yet factored into a standalone distribution. |
| `pacific-brewio-simulator` | Experimental | Read/write (simulated hardware only) | Pure-software fake controller. No physical risk. The most complete reference for the intended driver shape. |
| `pacific-brewio-tilt` | Experimental | Read-only | Passive BLE iBeacon listener. No actuator exists on the physical device. |
| `pacific-brewio-ispindel` | Experimental | Read-only | Local HTTP receiver for the device's own "Generic HTTP" telemetry output. No control path exists on the device. |
| `pacific-brewio-grainfather` | Planned | — | Legacy-controller ASCII protocol and telemetry format are fully recovered in internal research; the correctly-shaped stub exists, real implementation is not yet built. |
| `pacific-brewio-rapt` | Planned | — | Official REST API is the intended first implementation target; stub and configuration schema exist. |
| `pacific-brewio-brewpiless` | Planned | — | Protocol is source-verified against the open-source firmware; stub exists, implementation pending. |
| `pacific-brewio-brewblox` | Planned | — | Block-based REST/MQTT API is documented against the open-source service; stub exists, implementation pending. |
| `pacific-brewio-plaato` | Planned | Read-only (once implemented) | Official API is read-only monitoring only; no actuator endpoint is published by the vendor. |
| `pacific-brewio-inkbird` | Research only | — | Platform architecture (Tuya) is understood, but no product-specific data-point schema has been obtained. No implementation path exists without that schema. |

## Index

- [`GUIDE_TEMPLATE.md`](GUIDE_TEMPLATE.md) — the required structure for every future per-device public guide.
- [`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) — the review gate a finding must pass before it's promoted here.
- [`../pacific-brewio-architecture.md`](../pacific-brewio-architecture.md) — package map, distribution plan, dual human/AI interface design, licensing direction.
- [`../AI_INTEGRATION.md`](../AI_INTEGRATION.md) — how an AI agent or automation adapter should integrate with Pacific BrewIO without bypassing its safety model.
- [`../ai-context.md`](../ai-context.md) — a short, stable, retrieval-friendly project summary.
