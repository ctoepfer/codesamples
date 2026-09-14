# Interchange hardening audit — 2026-09-13

## Scope and baseline

Reviewed the model, units, public dispatch API, detection, CLI, reporting, all
six reader/writer pairs and their exports, both original test modules, and all
six original fixtures (including parsed BSMX and namespace-qualified BeerTools
XML). No `AGENTS.md` exists in codesamples/brewconvert. The enclosing Lumina
agent guide was also inspected; the user's explicit brewconvert-only scope
excludes changes to Lumina's separate implementation log or other projects.

Baseline command, before editing:

```text
PYTHONPATH=brewconvert/src python -m pytest brewconvert/tests -q
11 passed in 0.06s
```

The original suite largely tested detection, collection lengths and file
existence. It did not assert ingredient unit semantics or conversion losses.

## Architecture and root causes

The existing structure is retained: format detection/public dispatch → format
reader → normalized dataclasses → format writer. A shared adapter boundary now
collects diagnostics, validates models, checks profiles, stages output, and
compares reparsed results. No external services, recipe calculations or full
Lumina schema were added.

Confirmed defects:

- Misc/yeast bare `amount` discarded dimension at JSON/BTP/BSMX boundaries;
  BeerXML then serialized it as though already canonical kg/L.
- BeerJSON emitted the placeholder `unit`, while Brewfather omitted the unit.
- BeerXML copied stale display values independently of AMOUNT, hard-coded
  source encoding metadata, and emitted empty optional elements.
- BSMX ignored misc unit codes, hard-coded an output unit, used raw amounts,
  defaulted unsupported phases to boil and unavailable numbers to zero.
- Yeast attenuation averaging had an operator-precedence error and rejected
  a valid zero endpoint.
- Measured BSMX/BTP gravity values were placed in estimated fields, and the
  BSMX writer put targets into measured fields.
- Report objects did not receive adapter warnings; profiles were mostly ignored.
- Unknown/nested fields were inconsistently retained and silently lost on export.
- Numeric `or` fallbacks discarded valid zeroes; ProMash omitted units for misc,
  lost emitted notes, and defaulted mass parsing without reliable unit evidence.
- BeerTools could write a recipe collection that its reader could not accept.

## Implemented changes

- One immutable Decimal quantity model for all additions, exact centralized
  factors, derived physical dimensions/canonical values, provenance and status.
- Legacy constructor compatibility with read-only amount views; mutations now
  replace typed quantities. README documents the Python API implications.
- Canonical BeerXML quantities and display text share one typed source; canonical
  input is never repaired from a conflicting display string. Count/unsafe amounts
  are omitted and reported. UTF-8 and optional-field handling are corrected.
- Explicit standard/Grainfather XML and provisional BSMX profiles, rejection of
  unsupported profile names, and exact JSON Decimal number serialization.
- Original units retained by measure-based formats; source documents and imported
  statistics remain separate from normalized values and measured readings.
- Verified fixture field subsets for native BSMX quantities/equipment targets;
  unresolved native quantities/phases use reported `BC_*` extensions, never an
  invented mass/volume or boil fallback. Attenuation averaging is corrected.
- Shared reader/writer diagnostics, public validation API, CLI validation/report/
  strict options, and staged read-back comparison before replacing output.
- Synthetic Gose fixture and substantive regression tests plus every original
  source fixture converted through every target adapter.

The complete diagnostic-code inventory, severities, thresholds, profile losses
and compatibility details are in [README.md](README.md). This includes quantity
contradictions and ambiguity, invalid/zero/suspicious quantities, count loss,
excessive hop time, inferred/unresolved phases, actual quantity/phase/record/field
loss, mash/sparge merging, dropped evidence and provisional target behavior.

## Verification

Final project checks:

- Pytest: **100 passed**, with 13 expected `UserWarning` emissions from the
  original tests now exercising explicit conversion diagnostics.
- `python -m ruff check brewconvert`: passed using the available resolved rules.
- `python -m ruff format --check brewconvert`: passed.
- `python -m compileall -q brewconvert/src`: passed (syntax/import compilation,
  **not** a static type check).
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir
  /tmp/brewconvert-wheels ./brewconvert`: built `brewconvert-0.1.0-py3-none-any.whl`.
- `git diff --check -- brewconvert`: passed.
- No project static type checker is configured. Attempting `python -m mypy
  --version` found that mypy is unavailable; no static type-check success is claimed.

## Remaining application validation

Grainfather must be checked for nonstandard phase text, hop stands, required
fields on partial recipes, and display formatting. Standard XML intentionally
cannot encode counts or arbitrary phases; ordinary output may be incomplete,
with strict conversion rejecting unsafe mappings.

BSMX remains provisional. Native dry-yeast/count/misc-volume unit codes and
non-boil hop/other phase codes are unverified. `BC_QUANTITY`, `BC_PHASE` and
`BC_EST_FG` preserve information for brewconvert, but may all be ignored by
BeerSmith. Tests independently check native misc ounces after removing quantity
extensions; this still is not evidence of a successful BeerSmith import.

Unmodeled application metadata, measured fields, and unsupported process/style/
ingredient fields remain lossy on export and are reported. Source evidence is
retained in memory, not saved as a separate archival file. BeerJSON/Brewfather
and the legacy writers remain pragmatic format subsets; no schema/application
compatibility certification is implied by an internal round trip.
