# Integrating an AI agent or automation adapter with Pacific BrewIO

This document is for whoever builds an adapter between Pacific BrewIO and an AI agent, workflow engine, MCP server, or any other automation caller. **Read [`docs/pacific-brewio-architecture.md`](pacific-brewio-architecture.md) first** — this document assumes its terminology (`OperationDescriptor`, capability manifest, the AI-safe execution model, structured error codes) and walks through how those pieces fit together end to end. It also assumes the status described there: none of this is implemented or published yet. This is the intended integration path for when it is.

## The core idea

There is exactly one implementation of every operation — the typed Python API. An AI adapter never gets a separate, more permissive code path. It calls into the same driver, subject to the same safety gate, producing the same audit trail, as a human calling the typed method directly. If an adapter design requires bypassing confirmation, operator-presence checks, or precondition validation "just for automation," that design is wrong — fix the adapter, not the safety model.

## The integration path, step by step

### 1. Start from the typed API

Every Pacific BrewIO package exposes a normal, typed, documented Python API (`docs/pacific-brewio-architecture.md` section 2.1). An adapter is built on top of this, not instead of it.

### 2. Use introspection to discover what's available

Before an adapter can expose anything to an agent, it needs to know what exists:

```python
driver.describe()
driver.get_capabilities()
driver.get_operations()
driver.get_configuration_schema()
driver.get_compatibility()
```

This is how an adapter builds its own tool list, function-calling schema, or MCP tool registry — by asking the driver, not by hardcoding per-device knowledge into the adapter.

### 3. Read schemas and manifests, don't hardcode device knowledge

Each package's capability manifest (`src/brewio/<device>/manifest.json`, or the equivalent generated from typed metadata — see the architecture doc section 4) declares supported operations, transports, and status. An adapter that hardcodes "Tilt supports temperature and gravity" instead of reading this from the manifest will silently drift out of date the moment the driver's real capabilities change.

### 4. Translate each capability into an `OperationDescriptor`

Every exposed operation carries a full descriptor — not just a name and a docstring:

```python
OperationDescriptor(
    operation_id="tilt.read_latest",
    title="Read latest Tilt reading",
    ...
    read_only=True,
    risk=RiskLevel.READ_ONLY,
    requires_confirmation=False,
    requires_operator_presence=False,
    ...
)
```

An adapter surfaces this descriptor's fields to whatever it's built for — an MCP tool's `inputSchema`, an OpenAI function-calling `parameters` block, a workflow engine's step definition — rather than inventing its own metadata format. The descriptor is the one place risk, confirmation, and precondition information lives; don't let any of that leak into free-text tool descriptions where an agent has to *infer* rather than *read* it.

### 5. Return structured results, not just success/failure

Every call an adapter makes returns something serializable an agent can reason about programmatically:

```json
{
  "ok": true,
  "result": {
    "temperature_c": 19.4,
    "specific_gravity": 1.052,
    "timestamp": "2026-08-16T14:03:11Z"
  }
}
```

or, on failure:

```json
{
  "ok": false,
  "error": {
    "code": "stale_telemetry",
    "message": "No reading received in the last 5 minutes.",
    "retryable": true
  }
}
```

### 6. Use the shared error-code vocabulary

Map every failure to one of the codes defined in the architecture doc (`not_connected`, `discovery_timeout`, `safety_confirmation_required`, `unsafe_device_state`, and the rest). An agent — or a human debugging an agent's behavior — should never have to pattern-match a free-text error string to know what happened.

### 7. Carry safety metadata all the way through

`risk`, `requires_confirmation`, and `requires_operator_presence` on an `OperationDescriptor` are not adapter-optional decorations. If an adapter drops them when translating to a tool schema, the agent calling that tool has no way to know it's about to actuate a heater. Every adapter must preserve this metadata in whatever schema/tool format it emits.

### 8. Route confirmation through an approval context, not around it

A `requires_confirmation=True` operation needs an approval context supplied by the caller before it will execute — in BrewPanel today, this is `hardware.safety.SafetyGate`, which fails closed with no confirmation handler registered. An adapter integrating with an agent has two honest options:

- Require a human-in-the-loop step before the adapter will invoke a confirmation-required operation (the agent proposes, a human approves, then the adapter calls through).
- Implement its own confirmation handler that applies a real, auditable policy (e.g. "never auto-approve `risk=HIGH`") — never a handler that always approves.

There is no third option where the adapter simply omits the confirmation step to make automation smoother.

### 9. Never let secrets reach the agent

Connection secrets (API keys, tokens, credentials) are referenced by opaque `SecretRef` values, resolved only inside the driver/transport layer. A descriptor, a manifest, a log line, or a returned error must never contain a raw secret value — this applies identically whether the consumer is a human reading logs or an agent reading a tool result. Authorization headers are redacted before they reach any of those surfaces.

### 10. Emit an audit event for every state-changing attempt

Every actuator invocation — approved or denied, succeeded or failed — should produce an audit record, with enough context (operation ID, correlation ID, outcome, who/what approved it) to reconstruct what an agent did after the fact. This is not optional for automated callers; if anything it matters more for them, since an agent's decision process is less inspectable after the fact than a human's.

### 11. Building an adapter without bypassing safety — the summary rule

If you remember one thing from this document: **an adapter is a translation layer, never a second implementation.** Every rule above falls out of that one constraint. If your adapter design would let an agent do something the typed API and its safety gate wouldn't allow a human caller to do without confirmation, the design is wrong, not the safety gate.

## What this document does not cover

- A specific MCP server implementation for Pacific BrewIO — none exists yet.
- Framework-specific integration code for any particular AI vendor or agent SDK — Pacific BrewIO's core has no dependency on any of them (see the architecture doc section 1.3's independence rules), and this document doesn't add one either.
- Internal protocol research — nothing here should ever require reading `docs/hardware_internal/`. If an adapter needs internal research to function, something has gone wrong with the public interface it should be built against instead.

See [`docs/ai-context.md`](ai-context.md) for a short, stable summary suitable for pasting into an agent's system context.
