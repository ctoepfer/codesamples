# Guide template

Copy this structure for every new public hardware guide (e.g. `docs/hardware/tilt.md`). Fill in only what's actually implemented and verified — an empty or "not yet available" section is more honest than a plausible-sounding placeholder. See [`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) before publishing any section that originates from `docs/hardware_internal/`.

A public guide describes the **supported Pacific BrewIO interface and its verified behavior**. It is not a copy of the internal research notebook — link to further reading in vendor documentation or upstream open-source repositories instead of reproducing raw protocol traces here.

---

## 1. Overview

One or two paragraphs: what the device is, what role it plays in a brew, and what this package lets you do with it. No marketing language, no vendor claims restated as fact.

## 2. Supported devices/models

The exact product(s) this package targets. If model/hardware-revision behavior differs, say so here rather than in a footnote.

## 3. Support status

One of: Stable, Experimental, Read-only, Partial, Planned, Research only, Unsupported (see `docs/hardware/README.md` for definitions). State it plainly, in one sentence, with a one-line reason.

## 4. Tested library/package versions

The exact Pacific BrewIO package version(s) this guide was verified against. A guide that drifts from the installed package version is worse than no guide.

## 5. Tested hardware and firmware matrix

| Model | Hardware revision | Firmware | Tested operations | Status | Notes |
|---|---|---|---|---|---|
| | | | | | |

Leave rows genuinely empty (not filled with placeholder text) until a real unit has been tested.

## 6. Installation

```bash
pip install pacific-brewio-<device>
```

Note any required system-level dependency (a BLE adapter, a specific OS package) here.

## 7. Minimal read-only example

The smallest possible working example that only reads telemetry. This is the first thing a new user (human or AI) should be able to copy-paste and run safely.

## 8. Configuration

What has to be configured before first use (an address, a listener port, credentials) and how. Cross-reference the package's `ConfigField`/capability-manifest schema rather than duplicating it by hand.

## 9. Discovery behavior

Whether discovery is supported, what it returns, how long it runs, and — explicitly — that discovery never connects or saves anything on its own. If discovery isn't available for this device, say why (see the internal `Discoverer` classes' documented reasons for the pattern to follow).

## 10. Available capabilities

Which standardized capabilities (temperature, gravity, battery, RSSI, target-temperature control, heater/cooler/pump control, timer control, ...) this device actually implements. Do not list a capability the driver doesn't implement yet.

## 11. Units and normalized values

Confirm: internal values are metric (Celsius, specific gravity) regardless of the device's native wire units; conversion to a display unit is the caller's responsibility.

## 12. Connection lifecycle

Connect/disconnect semantics specific to this device (e.g. "BLE scan starts on connect and runs until disconnect" or "a local HTTP listener starts on connect and stays bound until disconnect").

## 13. Structured errors

Which of the shared error codes (see `docs/AI_INTEGRATION.md`) this device's operations can raise, and what triggers each one.

## 14. Safety and side effects

For every state-changing capability: risk classification, confirmation requirement, whether operator presence is required, and any safety bounds enforced. If the device has none (read-only hardware), say so explicitly rather than leaving the section blank.

## 15. AI/automation metadata

A pointer to this device's capability manifest (or a note that one doesn't exist yet), and anything AI-integration-specific worth calling out (e.g. "this device requires a bounded discovery window; do not poll continuously").

## 16. Known limitations

Stated plainly. A missing capability, an unconfirmed firmware behavior, a device-model gap — whatever is actually true today.

## 17. Troubleshooting

Common failure modes and what they usually mean, phrased in terms of the structured error codes where possible.

## 18. Vendor relationship/disclaimer

State plainly that this is independent, unofficial interoperability support — not affiliated with, endorsed by, or supported by the vendor. Name the vendor's trademarks as theirs.

## 19. License and attribution

This package's license (see the licensing section of `docs/pacific-brewio-architecture.md`), and attribution for any upstream open-source project the implementation is based on or adapted from.

## 20. Links to official vendor documentation

Direct links to whatever official documentation the vendor publishes, so a reader can verify claims independently.
