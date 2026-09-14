# Pacific BrewIO: Architecture and Migration Plan

**Status: architectural direction, not implemented.** Nothing described here has been extracted into a separate package or repository. This document establishes the target shape for a future extraction of BrewPanel's hardware layer into **Pacific BrewIO**, an independent, open-source project from Pacific Brewing Supplies — and the conventions that make it usable by conventional software engineers and by AI agents equally well, without compromising either.

See [`docs/hardware/README.md`](hardware/README.md) for current, honest per-device status, and [`docs/hardware_internal/README.md`](hardware_internal/README.md) for the research this plan is built on.

## 1. What Pacific BrewIO is

A small shared core plus a set of independently-installable hardware packages, each covering one piece of equipment. Distinct from [BrewPanel](../), which is the application that *uses* Pacific BrewIO (see section 12, "BrewPanel relationship").

### 1.1 Distribution packages

```text
pacific-brewio-core
pacific-brewio-simulator
pacific-brewio-tilt
pacific-brewio-ispindel
pacific-brewio-grainfather
pacific-brewio-rapt
pacific-brewio-brewpiless
pacific-brewio-brewblox
pacific-brewio-plaato
pacific-brewio-inkbird
```

### 1.2 Python namespace (proposed)

```python
from brewio.tilt import TiltScanner
from brewio.grainfather import GrainfatherDevice
```

**These distribution names and this import namespace are proposals, not commitments.** Before any package is published, both need an availability and conflict check: the `pacific-brewio-*` names against PyPI, and the `brewio` top-level import name against PyPI *and* the existing Python package ecosystem generally (a name collision with an unrelated existing `brewio` package would force a rename after the fact, which is far more disruptive than checking first). This check is one of the explicit open decisions listed at the end of this document.

### 1.3 Per-package rules

Every hardware package must:

- Be installable independently (`pip install pacific-brewio-tilt` works with no other Pacific BrewIO package installed except `pacific-brewio-core`).
- Depend only on `pacific-brewio-core` and its own required transport libraries (e.g. `bleak` for BLE, `aiohttp`/`httpx` for HTTP) — never on another device package.
- Be usable without BrewPanel. BrewPanel is one *consumer* of these packages, not a dependency of them.
- Never import GUI, recipe, session, or application code. A hardware package's only job is discovery, transport, protocol encoding/decoding, connection lifecycle, and normalized readings.
- Include its own tests and its own public guide (`docs/hardware/<device>.md` in this repository today; the package's own `docs/` once extracted).
- Declare its implementation and verification status honestly (see the status vocabulary in `docs/hardware/README.md`).
- Include model/firmware compatibility information (the matrix template in `docs/hardware/GUIDE_TEMPLATE.md`).
- Keep optional dependencies isolated — a transport library is an extra (`pacific-brewio-tilt[ble]`-style, or simply a required dependency of that one small package; it must never become a dependency of `pacific-brewio-core` or of an unrelated device package).
- Avoid coupling to a particular AI provider or framework — see section 4.

This mirrors a pattern already proven inside BrewPanel today: `hardware/` has zero required dependencies, each device's transport library is an optional extra, and `DeviceRegistry.discover()` finds any correctly-shaped plugin without a central list to edit (`brewpanel/src/brewpanel/hardware/registry.py`). Extraction is expected to preserve that shape almost exactly — each `hardware/devices/<id>/` folder becomes (most of) one package.

## 2. Design for humans and AI: a dual interface, one implementation

Pacific BrewIO must be equally good for a software engineer writing normal Python and for an AI agent (or any generic tool/automation system) that needs to *discover* what a device can do before calling it. These are two views of the same underlying operations — never two divergent implementations.

### 2.1 Human-facing typed API

Normal, discoverable Python. No requirement to use a generic command dispatcher, and no requirement to use an AI framework of any kind:

```python
async with TiltScanner(color="red") as scanner:
    reading = await scanner.next_reading()
    print(reading.temperature_c, reading.specific_gravity)
```

Requirements for every package's typed API:

- Full type hints on every public method.
- Dataclasses (or similarly explicit value objects) for every return type — never a bare dict.
- Docstrings on every public class and method.
- Stable method names across releases (a rename is a breaking change, documented as one).
- IDE autocomplete works out of the box — no dynamic attribute magic.
- A predictable async lifecycle (`connect()`/`disconnect()`, or an async context manager, matching `brewpanel.hardware.device.Device`'s existing shape).
- A minimal working example in the package's guide (see `docs/hardware/GUIDE_TEMPLATE.md` section 7).
- Explicit exceptions, not silently-swallowed errors or magic sentinel return values.

### 2.2 Machine-describing interface

Structured metadata describing the *same* typed operations — not a second implementation. Every package should be able to describe, at minimum:

- Driver identity, package name, and schema version.
- Vendor and device family.
- Transport.
- Discovery support (and whether it's automatic or must be explicitly invoked — it must always be the latter; see section 5).
- Configuration schema.
- Capabilities (which standardized read/write operations this device implements).
- Operations: full descriptors, not just names — input schema, output schema, units, read-only vs. state-changing, risk classification, preconditions, authentication requirements, required operator presence, confirmation requirements, idempotency, expected duration, possible errors.
- Telemetry freshness expectations.
- Tested models and firmware.
- Support status.

This metadata is designed to be adaptable — later, outside the scope of this document — to MCP tools, JSON Schema function-calling, OpenAPI, a CLI, Home Assistant, a workflow engine, or any other agent/tool system. **None of those integrations is a dependency of `pacific-brewio-core` or any device package.** MCP, OpenAI, Anthropic, Gemini, and every other vendor-specific agent framework stay entirely outside the core dependency graph; an adapter for any of them is a separate, optional package that depends on Pacific BrewIO, never the reverse.

## 3. Structured operation descriptors

Proposed shape (architectural direction — do not overbuild this in the current documentation milestone; the real implementation will likely need refinement once written against actual driver code):

```python
@dataclass(frozen=True)
class OperationDescriptor:
    operation_id: str
    title: str
    description: str
    input_schema: dict
    output_schema: dict
    read_only: bool
    risk: RiskLevel
    requires_confirmation: bool
    requires_operator_presence: bool
    idempotent: bool
    side_effects: tuple[str, ...]
    preconditions: tuple[str, ...]
    error_codes: tuple[str, ...]
```

**AI agents must not infer safety merely from a method name.** `set_heater` looking dangerous is a human intuition, not a machine-checkable fact — the descriptor is what a generic caller is expected to consult.

### 3.1 Read examples

```python
OperationDescriptor(
    operation_id="tilt.read_latest",
    title="Read latest Tilt reading",
    description="Return the most recently received passive BLE advertisement reading (temperature, specific gravity).",
    input_schema={},
    output_schema={
        "type": "object",
        "properties": {
            "temperature_c": {"type": "number"},
            "specific_gravity": {"type": "number"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
        "required": ["temperature_c", "specific_gravity", "timestamp"],
    },
    read_only=True,
    risk=RiskLevel.READ_ONLY,
    requires_confirmation=False,
    requires_operator_presence=False,
    idempotent=True,
    side_effects=(),
    preconditions=("connected",),
    error_codes=("not_connected", "stale_telemetry"),
)

OperationDescriptor(
    operation_id="ispindel.read_latest",
    title="Read latest iSpindel reading",
    description="Return the most recently received HTTP telemetry payload (temperature, specific gravity, battery).",
    input_schema={},
    output_schema={
        "type": "object",
        "properties": {
            "temperature_c": {"type": "number"},
            "specific_gravity": {"type": "number"},
            "battery_v": {"type": "number"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
        "required": ["temperature_c", "specific_gravity", "timestamp"],
    },
    read_only=True,
    risk=RiskLevel.READ_ONLY,
    requires_confirmation=False,
    requires_operator_presence=False,
    idempotent=True,
    side_effects=(),
    preconditions=("connected",),
    error_codes=("not_connected", "stale_telemetry"),
)

OperationDescriptor(
    operation_id="grainfather.read_status",
    title="Read Grainfather controller status",
    description="Read current/target temperature, timer state, and process state from the controller.",
    input_schema={},
    output_schema={
        "type": "object",
        "properties": {
            "current_temperature_c": {"type": "number"},
            "target_temperature_c": {"type": "number"},
            "heater_on": {"type": "boolean"},
            "pump_on": {"type": "boolean"},
            "timer_active": {"type": "boolean"},
        },
    },
    read_only=True,
    risk=RiskLevel.READ_ONLY,
    requires_confirmation=False,
    requires_operator_presence=False,
    idempotent=True,
    side_effects=(),
    preconditions=("connected",),
    error_codes=("not_connected", "protocol_error"),
)
```

### 3.2 Actuator examples

The whole point of these two examples is that a generic caller can tell, **from the descriptor alone**, that these are dangerous in a way `read_status` is not — without special-casing the method name:

```python
OperationDescriptor(
    operation_id="grainfather.set_target_temperature",
    title="Set Grainfather target temperature",
    description="Change the controller's target temperature setpoint. Does not itself turn the heater on.",
    input_schema={
        "type": "object",
        "properties": {"celsius": {"type": "number", "minimum": 0, "maximum": 105}},
        "required": ["celsius"],
    },
    output_schema={"type": "object", "properties": {"accepted_celsius": {"type": "number"}}},
    read_only=False,
    risk=RiskLevel.HIGH,
    requires_confirmation=True,
    requires_operator_presence=True,
    idempotent=True,  # setting the same value twice has the same effect as once
    side_effects=("changes_setpoint",),
    preconditions=("connected", "controller_state_known", "target_within_safety_bounds"),
    error_codes=(
        "not_connected", "invalid_input", "safety_confirmation_required",
        "safety_confirmation_denied", "unsafe_device_state",
    ),
)

OperationDescriptor(
    operation_id="grainfather.set_heater",
    title="Turn the Grainfather heater on or off",
    description="Directly drives the controller's heating element relay.",
    input_schema={"type": "object", "properties": {"on": {"type": "boolean"}}, "required": ["on"]},
    output_schema={"type": "object", "properties": {"heater_on": {"type": "boolean"}}},
    read_only=False,
    risk=RiskLevel.HIGH,
    requires_confirmation=True,
    requires_operator_presence=True,
    idempotent=True,
    side_effects=("changes_heater_output", "may_boil_liquid"),
    preconditions=(
        "connected",
        "controller_state_known",
        "target_temperature_set",
        "operator_confirmed_liquid_level_safe",
    ),
    error_codes=(
        "not_connected", "safety_confirmation_required", "safety_confirmation_denied",
        "unsafe_device_state", "protocol_error",
    ),
)
```

Every actuator descriptor in Pacific BrewIO is expected to spell out, explicitly: that it's state-changing (`read_only=False`), its risk classification, that it requires confirmation, whether it requires a human physically present, its preconditions, and (where meaningful) safety bounds baked into the input schema itself (e.g. `"maximum": 105` above) rather than left to caller discipline. Expected-state verification (confirming the device actually reached the requested state, not just that the command was accepted) is a precondition/postcondition concern each package's real implementation will need to define concretely — noted here as a requirement, not fully specified.

## 4. Capability manifest

Proposed per-package machine-readable manifest, recommended location within each future distribution:

```text
src/brewio/<device>/manifest.json
```

Or generated from the typed Python metadata (the `OperationDescriptor`s and capability declarations already living in code) if that avoids duplication — **pick one authoritative source and keep the other synchronized mechanically, not by hand.** The recommended direction: typed Python is authoritative (it's what's actually executed and covered by tests), and `manifest.json` is a generated artifact produced by a small build step that introspects the driver's declared capabilities/operations. This mirrors how BrewPanel's `DeviceInfo.capabilities` tuple today is hand-maintained alongside the driver but is at least co-located and reviewed together (`brewpanel/src/brewpanel/hardware/devices/*/__init__.py`) — a generator script is the natural next step once there's a second consumer (a manifest) that must never drift from the code.

```json
{
  "schema_version": "1.0",
  "driver_id": "tilt",
  "display_name": "Tilt Hydrometer",
  "package": "pacific-brewio-tilt",
  "support_status": "experimental",
  "transports": ["ble_advertisement"],
  "discovery": {
    "supported": true,
    "automatic": false
  },
  "capabilities": [
    "temperature.read",
    "gravity.read"
  ],
  "operations": []
}
```

**Do not claim unsupported operations.** An empty `"operations": []` array (as above) is the honest state for a package whose typed API exists but hasn't yet had its operations formally described — that is preferable to a manifest asserting an operation the driver can't actually perform.

Manifests must validate against a versioned JSON Schema (itself part of `pacific-brewio-core`, published alongside the `schema_version` field above) so a consumer can detect an incompatible manifest before trusting its contents.

## 5. AI-safe execution model

These rules apply to a generic automation caller and a human calling the typed API directly — the safety model has exactly one enforcement point, not a human path and a separate AI path.

- Installing a package never enables hardware.
- Importing a module never scans or connects.
- Discovery requires an explicit, bounded call — never automatic, never unbounded.
- Discovery does not connect.
- Connection does not actuate.
- Read operations are clearly distinguishable from writes at the type/descriptor level (`read_only` on `OperationDescriptor`; a distinct capability-protocol family in the typed API — see `brewpanel.hardware.capabilities`'s existing `READ_CAPABILITIES`/`ACTUATOR_CAPABILITIES` split, which this generalizes).
- State-changing operations require explicit invocation — no operation runs as a side effect of an unrelated call.
- High-risk operations require an approval/confirmation context, enforced by the implementation, not by caller convention.
- Operations support dry-run or command planning where meaningful (see section 7).
- A planned command can be inspected before execution.
- Secrets never appear in descriptors, prompts, logs, or returned errors.
- Authorization headers are always redacted before they reach a log, an error, or a descriptor.
- Telemetry includes source and timestamp on every reading.
- Stale telemetry is represented explicitly (a boolean/flag or an explicit "unknown" state), never silently treated as fresh.
- Results include a stable status and error code (section 6), not just a human-readable message.
- Dangerous assumptions fail closed: an operation that can't confirm a precondition refuses rather than proceeding optimistically.
- Unknown device state blocks unsafe writes — an actuator call against a device whose current state hasn't been established is refused, not attempted "to find out."
- Commands support correlation IDs, so a caller (or an audit log) can trace one logical request across retries/async completion.
- Idempotency behavior is declared per operation (`OperationDescriptor.idempotent`), not assumed.
- Every state-changing attempt — approved or denied, succeeded or failed — emits an audit event.
- AI adapters cannot bypass the underlying safety policy. An adapter is a translation layer over the typed implementation; it does not get a privileged code path that skips confirmation or audit behavior (see section 8).

BrewPanel's `hardware.safety.SafetyGate` already implements a meaningful subset of this today (fails closed with no confirmation handler registered, records every approve/deny in an audit log, wraps every actuator method via `@requires_confirmation`) — Pacific BrewIO's extraction target is to generalize that mechanism into `pacific-brewio-core`, not to invent a new one.

## 6. Structured results and errors

A small, stable set of error categories, shared across every package:

```text
not_configured
not_enabled
not_connected
discovery_timeout
device_not_found
authentication_failed
permission_denied
unsupported_operation
unsupported_firmware
stale_telemetry
invalid_input
safety_confirmation_required
safety_confirmation_denied
unsafe_device_state
transport_error
protocol_error
rate_limited
```

Human-facing exceptions stay idiomatic Python (raised, typed, with a normal message) — this list is not a request to replace Python exceptions with error codes everywhere. It's a *parallel*, serializable representation for tools and agents that can't catch a Python exception class:

```json
{
  "ok": false,
  "error": {
    "code": "safety_confirmation_required",
    "message": "Operator confirmation is required before enabling heat.",
    "retryable": false
  }
}
```

**The public result envelope never includes a traceback or a secret.** A Python-level exception may carry a traceback for a developer attached to a debugger; the serialized envelope handed to a tool/agent caller does not.

## 7. Introspection API

Proposed, model-neutral, and returning typed objects that can serialize to JSON:

```python
driver.describe()
driver.get_capabilities()
driver.get_operations()
driver.get_configuration_schema()
driver.get_compatibility()
```

A human developer can ignore all of this and call typed methods directly — introspection exists for callers (agents, generic tools, a future CLI) that need to discover what a device can do before deciding what to call, rather than guessing from documentation or a method name.

## 8. Avoid a universal unsafe executor

This must **not** be the primary API:

```python
await device.execute("some arbitrary command", payload)
```

The preferred human API stays explicit:

```python
await device.get_temperature()
await device.set_target_temperature(67.0, context=approval)
```

If a generic execution adapter is added later specifically to serve agent/tool-calling use cases, it must:

- Accept only registered operation IDs — never a raw/arbitrary command string.
- Validate input against that operation's schema before doing anything else.
- Enforce the same capability and safety policy as the typed API (confirmation, operator presence, risk gating).
- Reject raw protocol commands by default.
- Produce a command plan (see section 5's "dry-run/planning" rule) before executing anything high-risk.
- Use the same typed implementation underneath — an adapter is a thin translation layer, never a second implementation.
- Never bypass confirmation or audit behavior, under any circumstance, including a caller explicitly asking it to.

## 9. Examples optimized for retrieval (proposed structure)

**No example files exist yet in this repository** — creating `examples/tilt/discover.py` today, before `brewio.tilt` exists as an installable package, would produce non-functional code that looks runnable. The proposed structure, for when extraction happens:

```text
docs/hardware/tilt.md
examples/tilt/discover.py
examples/tilt/read.py
examples/tilt/structured_result.py
```

Several small, self-contained examples per package, each stating: what it does, whether it's read-only, required hardware, required configuration, the expected result type, common errors, cleanup behavior, and safety implications — preferred over one large example application, because a small example is what both a human skimming docs and an agent doing retrieval-augmented lookup actually want. Use consistent terminology across every device's examples (the same field names, the same error-code vocabulary, the same phrasing for "this is read-only").

## 10. Licensing and provenance plan

**Intended direction: Apache License 2.0 with a Pacific Brewing Supplies `NOTICE` file, once extraction happens.** This document does not relicense anything today, and no file should be assumed Apache-licensed until it has actually been classified and the extraction has occurred.

Before extraction, every source file that would move into a Pacific BrewIO package must be classified as one of:

- **Original Pacific Brewing Supplies work** — written from scratch for this project.
- **Clean implementation from public documentation** — written by reading a vendor's official, public documentation, with no exposure to decompiled/proprietary source.
- **Original interoperability implementation** — written by independently reverse-engineering observed behavior (e.g. a captured BLE advertisement format), without copying vendor code.
- **Adapted third-party open-source work** — based on or ported from an existing open-source project (e.g. behavior confirmed against BrewPiLess's or iSpindel's own open-source firmware). Requires carrying forward that project's license and attribution correctly, and confirming license compatibility with Apache-2.0 before inclusion.
- **Unknown or requiring review** — provenance hasn't been established yet. Treated as blocked from extraction until classified.

**Do not place copied GPL, custom-licensed, unlicensed, decompiled, or otherwise incompatible code into an Apache-licensed package.** This is a hard rule, not a style preference — several files in `docs/hardware_internal/` explicitly derive from *static analysis of closed-source vendor apps* (Grainfather, RAPT, Plaato, Inkbird, Nespresso, SCiO); none of that is "clean" provenance, and an implementation informed by it needs the "original interoperability implementation" classification (independently reproducing observed *behavior*, not vendor code) — not a claim of "clean implementation from public documentation." The BrewPiLess/Brewblox/iSpindel research, by contrast, is source-verified against those projects' own open-source repositories and carries a different, generally more permissive, provenance story — but still requires an explicit license-compatibility check against Apache-2.0 before anything is adapted.

**Moving a file into a differently-named directory is not a publication or licensing decision.** `docs/hardware_internal/` → `docs/hardware/` is itself a promotion event gated by `docs/hardware/PUBLICATION_CHECKLIST.md`, which now includes provenance review as an explicit line item. Renaming or relocating research never substitutes for that review.

## 11. BrewPanel relationship

A firm ownership boundary, so extraction has a clean seam:

**Pacific BrewIO owns:**

- Hardware discovery
- Transport
- Protocol encoding and decoding
- Device connection lifecycle
- Normalized device readings
- Capability and operation descriptions
- Device-specific errors
- Low-level safety metadata (risk classification, confirmation requirements — the *declaration*, not the operator-facing approval UI)

**BrewPanel owns:**

- Which configured devices are enabled
- Persistent device profiles
- Secret references
- Connection policy
- Runtime orchestration (today: `core.device_manager.DeviceManager`)
- Recipe import
- Brew-session timeline
- Operator GUI
- TV display
- Human approvals (the actual confirmation dialog/workflow — Pacific BrewIO declares that confirmation is *required*; BrewPanel is what actually asks a human)
- Shop-specific limits
- Historical telemetry
- Cross-device coordination

**Closing a browser client must not tear down an application-managed connection needed by another client or an active session.** This is already true in BrewPanel today — `DeviceManager` is owned by `core.app.Application`, not by any GUI page or `Client.on_disconnect` callback (see `brewpanel/README.md`'s "Hardware Control Panel" section, and the concurrent-client verification recorded there) — and is recorded here as a standing architectural constraint that the future BrewPanel/BrewIO split must preserve, not relax.

## 12. Open decisions before any real extraction

- PyPI name availability for all ten `pacific-brewio-*` distributions, and namespace-collision check for the `brewio` top-level import name.
- A concrete decision on typed-metadata-as-source-of-truth for the capability manifest, plus the generator script that produces `manifest.json` from it.
- The actual JSON Schema for manifest validation (section 4) and for `OperationDescriptor` serialization (section 3), versioned from day one.
- A per-file provenance classification pass across everything that would move out of `brewpanel/hardware/` and `docs/hardware_internal/` (section 10) — not started; this document only defines the categories.
- The first real publication-review pass (via `docs/hardware/PUBLICATION_CHECKLIST.md`) for at least one device, to prove the promotion process end-to-end before relying on it for nine more.
- Where the shared core's safety-gate generalization (section 5) actually lives once BrewPanel's `hardware.safety.SafetyGate` has a sibling in `pacific-brewio-core` — including how BrewPanel's own confirmation-dialog UI continues to satisfy the core's `requires_confirmation` contract after the split.
