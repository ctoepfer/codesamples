# brewconvert

A focused Python interchange and semantic validation library for brewing recipes.
Every adapter reads/writes the same normalized model. It does not scale entire
recipes, recalculate brewing statistics, or implement the Lumina recipe schema.

## Install and use

```bash
python -m pip install -e .
brewconvert inspect tests/fixtures/gose.beerjson
brewconvert validate recipe.xml
brewconvert validate recipe.xml --strict
brewconvert convert input.xml output.xml --to beerxml --profile grainfather --report
brewconvert convert input.xml output.bsmx --to beersmith-bsmx --report
brewconvert convert input.beerjson output.xml --to beerxml --strict --report
```

Warnings are always visible. `--report` also prints details of clean conversions.
`validate --strict` and `convert --strict` return exit status **2** for contradictions,
invalid/missing quantities, unsafe unit/phase ambiguity, unsupported count/native
quantity mappings, and detected quantity/phase loss. Advisory warnings alone do
not fail strict mode. A failed strict conversion leaves an existing destination
unchanged. Every export is staged and read back before writing the destination.
This checks our adapters; it does **not** verify an application's import behavior
or certify compliance with a complete format schema.

## Typed quantities

All four ingredient addition classes have `quantity: Quantity | None`.
`Quantity` stores a Decimal `value`, the original `unit` spelling, a derived
`kind` (`mass`, `volume`, `count`, or `unknown`), `si_value` and `si_unit`,
`source_field`, `original_display`, raw `evidence`, and a status of `explicit`,
`inferred`, or `ambiguous`. Invalid values remain inspectable and are reported;
writers omit unsafe amounts instead of inventing zeroes.

| Dimension | Supported units |
| --- | --- |
| Mass | kg, g, lb, oz |
| Volume | L, mL, US gal, qt (US liquid), US fl oz |
| Count | package, sachet, tablet, count (item/each aliases) |

Common aliases are recognized, including `l`, `ml`, `lbs`, `gal`, `fl oz`, and
`pkg`. Gallons and fluid ounces are **US**, not imperial. Bare quantities, unknown
units, and the old placeholder `"unit"` remain ambiguous. Package, sachet and
tablet counts are not interchangeable and never acquire a kilogram/liter value.
Mass and volume conversion requires an explicit physical unit; no density or
package size is guessed.

```python
from brewconvert import ConversionReport, read_recipes, write_recipes
from brewconvert.model import MiscAddition, Quantity, Recipe

salt = MiscAddition("Sea salt", quantity=Quantity("2.92", "oz"), use="Boil")
assert salt.quantity.kind == "mass"
assert str(salt.quantity.si_value) == "0.08278060752500"
recipe = Recipe("Gose", miscs=[salt])
report = ConversionReport("model", "beerxml")
write_recipes([recipe], "gose.xml", format="beerxml", report=report)
print(report.text())

# Carry import evidence and warnings through to the export report.
report = ConversionReport("beerxml", "beersmith-bsmx")
recipes = read_recipes("input.xml", report=report)
write_recipes(recipes, "output.bsmx", report=report, strict=True)
```

Use strings or Decimal for exact entered values. `q.to("g")` returns a Decimal;
`q.scaled("1.5")` returns a new immutable quantity. Conversion factors are
centralized in `model/units.py`. JSON is read with Decimal number tokens and written
with exact Decimal numbers, not quoted strings or intermediate floats. XML quantity
fields use Decimal formatting. BSMX native ounce/fluid-ounce fields use 12 decimal
places. Other legacy numeric recipe fields remain floats.

### Compatibility with 0.1 callers

Existing constructors accept `amount_kg=` for hops/fermentables and `amount=`,
`amount_is_weight=`, `display_amount=` for misc/yeast. A legacy amount with an
explicit weight flag means kg (`True`) or L (`False`). Without that flag it is
ambiguous, even if a display string appears plausible. Prefer `quantity=`; when
provided, it is authoritative over legacy constructor arguments.

Legacy amount/display attributes are now **read-only derived views**. To change
an amount, replace `addition.quantity`; assigning `addition.amount` or
`addition.amount_kg` raises `AttributeError`. Missing, invalid, ambiguous and
count quantities have no legacy SI amount. Dataclass serialization now includes
`quantity` rather than bare amount fields. `write_recipes` now returns its
`ConversionReport` (previously `None`). `read_recipes` still returns a recipe list.
Both APIs and direct adapter `read`/`write` functions accept `report=` and
`strict=`. Without a supplied report, diagnostics are emitted as Python
`UserWarning`s. `validate_recipes(recipes)` returns a report; `ValidationError`
is raised for strict failures.

## BeerXML canonical quantities

[BeerXML 1.0](https://www.beerxml.com/beerxml.htm) defines fermentable and hop
`AMOUNT` in kilograms. Misc and yeast use kilograms when `AMOUNT_IS_WEIGHT` is
true and liters when false. `DISPLAY_AMOUNT` is a descriptive extension: it must
not replace a valid canonical amount, even when that canonical amount looks wrong.

The reader keeps canonical and display evidence separately. Missing/invalid
weight flags and conflicting dimensions produce unsafe diagnostics. Numeric
disagreement beyond `max(0.000001 kg/L, 1% of canonical value)` produces an
`amount-contradiction` warning; a factor of ten also produces `magnitude-change`.
Both output fields are generated from the typed quantity, never from an unrelated
old display string. Original conflicting evidence remains in memory and the report.

The observed Gose failure copied entered numbers across unit boundaries:
`2.92 oz` salt became about `2.92 g`, `5.83 oz` coriander became about `5.83 g`,
and `29.17 lb` raspberries became `29.17 kg`. The corrected path multiplies the
entered amounts by exact factors `0.028349523125 kg/oz` and `0.45359237 kg/lb`.
Tests derive expected values independently from those factors and use an explicit
`1e-8 kg/L` round-trip tolerance. No rounded illustrative conversion is hard-coded.

BeerXML has **no count quantity**. A Whirlfloc tablet or yeast package therefore
produces an unsafe `count-unsupported` loss warning, and its `AMOUNT` is omitted.
Ordinary output can consequently be incomplete for applications requiring that
field; strict export refuses it. Supplying a known measured tablet mass is an
explicit caller decision, not a converter inference.

Output is UTF-8, retaining names, ° symbols, en/em dashes, `CO₂`, `5.2–5.4`, and
`3–4 weeks`. The reader honors an XML source's encoding declaration and records
it accurately. Unavailable optional BeerXML fields and empty containers are omitted.

## Formats and target profiles

| `--to` | `--profile` | Behavior and known losses |
| --- | --- | --- |
| `beerxml` | `standard` (default) | Canonical SI; consistent display amounts; only supported misc/hop phase enum values emitted. Unknown/sparge/packaging phases are omitted with explicit loss warnings. No count encoding. |
| `beerxml` | `grainfather` | Same SI values; misc/yeast mass below 1 kg displayed in g, other misc/yeast quantities in kg/L; hop displays in g. Retains nonstandard misc/hop phase text such as Sparge and Hop Stand, warning that applications may ignore it. |
| `beersmith-bsmx` | `beersmith-bsmx` (default) | **Provisional** native field subset plus clearly named `BC_*` brewconvert extensions; details below. |
| `beerjson` | `standard` (default) | BeerJSON-style measures preserve original units and dimensions, including explicit counts; timing text is retained. This is not full BeerJSON schema validation. |
| `brewfather-json` | default / `export` | Explicit amount/unit pairs and phase strings; default writes one recipe object or a collection, `export` always wraps a `recipes` collection. Application-specific fields are not replayed. |
| `beertools-btp` | default only | Draft namespace-qualified XML with typed quantity measures. Supports recipe collections; measured gravity readings stay separate from estimates. Other application metadata, some ingredient/style fields and extended mash fields are lossy. |
| `promash-text` | default only | Pragmatic readable text, not binary ProMash. Explicit ingredient quantities are parsed; misc phases and Unicode notes survive the emitted report dialect. Yeast metadata/timing, arbitrary hop phases, some style/ingredient/mash fields are lossy and reported. |

Unsupported profile names are rejected instead of ignored. No separate
BeerSmith-specific BeerXML profile is offered: the fixtures do not justify a
verified quirk distinct from standard BeerXML. Use standard BeerXML and validate
the resulting import in BeerSmith.

### BSMX limitations

The paired Domo fixtures support ounce-based grain/hop quantities and misc
`F_M_UNITS=2` with `F_M_IMPORT_AS_WEIGHT=1`. Misc phase codes 0/1/5 map to
Boil/Mash/Sparge. Unknown unit/phase codes are retained as ambiguous evidence,
not treated as kilograms or defaulted to boil. Liquid `F_Y_AMOUNT` is interpreted
as US fluid ounces with an **inferred-unit** warning. Native hop code 0 is
interpreted as Boil with an **inferred-phase** warning; other codes remain
unresolved. The source fixture itself includes inconsistent import evidence,
so these mappings do not establish application compatibility.

The writer uses native equipment fields for target batch/boil volumes, boil time
and efficiency, rather than writing targets into measured fields. Desired OG is
separate from measured OG. Estimated FG uses `BC_EST_FG`. `BC_QUANTITY` preserves
exact typed quantities for brewconvert, and `BC_PHASE` preserves phase text.
Dry-yeast mass, package counts, and miscellaneous volumes lack verified native
mappings: only their extensions are written, with unsafe loss warnings. Likewise,
unverified phases are not given invented native boil codes. BeerSmith may ignore
**all** `BC_*` extensions. Internal round trips are not proof of BeerSmith support.
The provisional writer warning remains on every export. Native count/dry-yeast
unit codes, phase enums, hop stands, and all extension behavior need validation
in BeerSmith before production use.

## Source evidence and conversion reports

Each addition retains its source fields. Readers also retain the original recipe
XML/text or JSON object under `source_metadata["document"]`, and record unmodeled
fields in `unknown_fields` where practical. These are **in-memory evidence**, not
an archival sidecar and not silently replayed over edited normalized values.
Reports flag that raw source evidence, nested application metadata and unknown
fields are not emitted, even on same-format conversions.

`measured_values` retains actual/source measurement fields separately;
`calculated_values` retains imported statistics where identified. Normalized
estimated fields never fall back to measured readings. No local recalculation
occurs. Writers report measured data they cannot emit. Water salts stay separate
list entries; name equality never merges mash and sparge additions. Missing
phase mappings are reported rather than substituted with Boil.

All semantic warnings include recipe, ingredient/field, source, interpretation,
target, and reason. Reports expose `warnings`, the unsafe subset `errors`, and
`notes`. The implemented diagnostic codes are:

- Input: `missing-quantity`, `invalid-quantity`, `ambiguous-unit`, `inferred-unit`,
  `ingredient-dimension`, `ambiguous-display`, `invalid-display`,
  `dimension-contradiction`, `amount-contradiction`, `magnitude-change`,
  `zero-culture`, `culture-dimension`, `suspicious-quantity`, `hop-time`,
  `inferred-phase`, `ambiguous-phase`.
- Target support/evidence: `count-unsupported`, `native-quantity-unsupported`,
  `native-phase-unsupported`, `provisional-writer`, `bsmx-extensions`,
  `source-document`, `unsupported-source`, `source-evidence`, `measured-values`.
- Actual write/read comparison: `recipe-loss`, `ingredient-loss`, `quantity-loss`,
  `magnitude-change`, `phase-loss`, `salt-phase-merge`, `field-loss`,
  `ingredient-field-loss`, `style-loss`, `mash-loss`.

Post-write quantity comparisons use `max(1e-8 kg/L, 1e-7 relative)` tolerance.
Count value/unit and phase comparisons are exact (phase casing ignored).
Suspicious-quantity thresholds are advisory heuristics: fruit above 1 kg/L of
batch, named salts/spices/finings or dry cultures above 0.01 kg/L, and liquid
cultures above 10% of batch volume. When batch size is absent, thresholds assume
20 L. These are unit-error signals, not brewing recommendations.

## Development and verification

```bash
PYTHONPATH=src python -m pytest tests -q
python -m ruff check .
python -m ruff format --check .
python -m compileall -q src
```

Baseline before this change: **11 tests passed**. The expanded suite includes the
synthetic Gose fixture, explicit quantity/dimension assertions, count and yeast
regressions, native BSMX ounce checks independent of extensions, strict CLI/file
preservation tests, Unicode, invalid values, source evidence, and a 6×6 fixture
conversion matrix. See [AUDIT.md](AUDIT.md) for the audit and verification record.
