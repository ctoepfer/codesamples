# brewconvert

A small Python library and CLI for converting brewing recipe files through a normalized internal model.

## Current support

| Format | Detect | Read | Write | Notes |
| --- | --- | --- | --- | --- |
| BeerXML `.xml` | Yes | Yes | Yes | Preserves common Grainfather-friendly fields such as `DISPLAY_AMOUNT`, `AMOUNT_IS_WEIGHT`, hop stand temperature tags, and water salts as misc additions. |
| BeerSmith BSMX `.bsmx` | Yes | Yes | Draft | The writer emits practical BeerSmith-style XML and should be validated in BeerSmith before production use. |
| BeerJSON `.beerjson` / `.json` | Yes | Yes | Yes | Uses BeerJSON-style measure objects with `value` and `unit`. |
| Brewfather JSON `.json` / `.brewfather` | Yes | Yes | Yes | Accepts API-like objects, single exported recipes, arrays, and backup-style `recipes` containers where common fields are present. |
| BeerTools Pro `.btp` / `.btt` XML | Yes | Yes | Draft | Tested against the included `.btp` sample and written as namespace-qualified BeerTools-like XML. |
| ProMash text export `.txt` / `.promash` | Yes | Pragmatic | Text report | The reader follows the line-oriented headings used by the reference script. The writer emits a readable report, not an undocumented binary file. |

## Install locally

```bash
python -m pip install -e .
```

## CLI examples

```bash
brewconvert inspect tests/fixtures/domo_before.xml
brewconvert inspect tests/fixtures/domo_after.bsmx
brewconvert inspect tests/fixtures/sample.beerjson
brewconvert inspect tests/fixtures/sample.brewfather.json
brewconvert inspect tests/fixtures/test.btp
brewconvert inspect tests/fixtures/sample.promash.txt

brewconvert convert tests/fixtures/domo_before.xml /tmp/out.xml --to beerxml
brewconvert convert tests/fixtures/domo_before.xml /tmp/out.bsmx --to beersmith-bsmx
brewconvert convert tests/fixtures/domo_before.xml /tmp/out.beerjson --to beerjson
brewconvert convert tests/fixtures/domo_before.xml /tmp/out.json --to brewfather-json
brewconvert convert tests/fixtures/domo_before.xml /tmp/out.btp --to beertools-btp
brewconvert convert tests/fixtures/domo_before.xml /tmp/out.promash.txt --to promash-text
```

Supported `--to` values are `beerxml`, `beersmith-bsmx`, `beerjson`, `brewfather-json`, `beertools-btp`, and `promash-text`.

## Library examples

```python
from brewconvert import read_recipes, write_recipes

recipes = read_recipes("tests/fixtures/sample.beerjson")
write_recipes(recipes, "out.xml", format="beerxml", profile="grainfather")
write_recipes(recipes, "out.btp", format="beertools-btp")
```

## Design notes

The converter intentionally uses an internal normalized model instead of treating BeerXML as canonical. Real brewing software adds application-specific fields and quirks, so each importer/exporter preserves unknown or source-specific metadata where practical.

The legacy writers for BeerSmith BSMX, BeerTools Pro XML, and ProMash text are intentionally pragmatic because the target applications use application-specific conventions that are not fully captured by public schemas. Validate those files in the target application before using them as production recipe archives.
