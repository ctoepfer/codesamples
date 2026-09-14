import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

import pytest
from brewconvert.cli import main
from brewconvert.model import (
    FermentableAddition,
    HopAddition,
    MiscAddition,
    Quantity,
    Recipe,
    YeastAddition,
)
from brewconvert.report import compare_recipes

from brewconvert import (
    ConversionReport,
    ValidationError,
    read_recipes,
    validate_recipes,
    write_recipes,
)

FIXTURES = Path(__file__).parent / "fixtures"
TOL = Decimal("1e-8")  # kg/L across text format serialization


def read(path, **kwargs):
    return read_recipes(path, report=ConversionReport(), **kwargs)


def write(recipes, path, **kwargs):
    report = ConversionReport()
    write_recipes(recipes, path, report=report, **kwargs)
    return report


@pytest.mark.parametrize(
    "unit,value,si,kind",
    [
        ("kg", "1", "1", "mass"),
        ("g", "1000", "1", "mass"),
        ("lb", "1", "0.45359237", "mass"),
        ("oz", "1", "0.028349523125", "mass"),
        ("L", "1", "1", "volume"),
        ("mL", "1000", "1", "volume"),
        ("US gal", "1", "3.785411784", "volume"),
        ("qt", "1", "0.946352946", "volume"),
        ("US fl oz", "1", "0.0295735295625", "volume"),
    ],
)
def test_exact_units(unit, value, si, kind):
    q = Quantity(value, unit)
    assert q.si_value == Decimal(si)
    assert q.kind == kind
    assert q.to(unit) == Decimal(value)
    assert q.scaled("0.1").scaled("10").si_value == q.si_value


@pytest.mark.parametrize("unit", ["package", "sachet", "tablet", "count"])
def test_count_separate(unit):
    q = Quantity(1, unit)
    assert q.kind == "count" and q.si_value is None
    with pytest.raises(ValueError):
        q.to("kg")
    with pytest.raises(ValueError):
        q.to("L")


def test_compatibility():
    m = MiscAddition("salt", amount=0.02, amount_is_weight=True)
    y = YeastAddition("liquid", amount=0.125, amount_is_weight=False)
    assert m.quantity == Quantity(0.02, "kg", source_field="legacy amount")
    assert y.quantity.kind == "volume" and y.amount == 0.125
    assert MiscAddition("untyped", amount=1).quantity.status == "ambiguous"
    with pytest.raises(AttributeError):
        m.amount = 2
    m.quantity = Quantity(20, "g")
    assert m.amount == 0.02
    assert FermentableAddition("malt", amount_kg=5).quantity.si_value == 5


@pytest.mark.parametrize("profile", [None, "standard", "grainfather"])
def test_gose_canonical_roundtrip(tmp_path, profile):
    recipes = read(FIXTURES / "gose.beerjson")
    path = tmp_path / "out.xml"
    write(recipes, path, profile=profile)
    result = read(path)[0]
    root = ET.parse(path).getroot()
    expected = [
        Decimal("2.92") * Decimal("0.028349523125"),
        Decimal("5.83") * Decimal("0.028349523125"),
    ]
    for i, value in enumerate(expected):
        q = result.miscs[i].quantity
        assert abs(q.si_value - value) <= TOL
        assert abs(q.to("oz") - Decimal(["2.92", "5.83"][i])) <= TOL
        node = root.findall(".//MISC")[i]
        display = Quantity.parse(node.findtext("DISPLAY_AMOUNT"))
        assert abs(display.si_value - Decimal(node.findtext("AMOUNT"))) <= TOL
    fruit = result.fermentables[0].quantity
    assert abs(fruit.si_value - Decimal("29.17") * Decimal("0.45359237")) <= TOL
    assert fruit.si_value != Decimal("29.17")
    assert result.notes == recipes[0].notes
    assert result.name == recipes[0].name
    assert path.read_bytes().startswith(b'<?xml version="1.0" encoding="utf-8"?>')
    assert all(e.text or len(e) for e in root.iter())
    assert [(m.name, m.use) for m in result.miscs[-2:]] == [
        ("Gypsum", "Mash"),
        ("Gypsum", "Sparge" if profile == "grainfather" else None),
    ]
    assert result.yeasts[0].quantity.si_value == Decimal("0.125")
    second = tmp_path / "second.xml"
    write([result], second)
    assert (
        read(second)[0].miscs[0].quantity.si_value == result.miscs[0].quantity.si_value
    )


def test_beerjson_original_units(tmp_path):
    recipe = read(FIXTURES / "gose.beerjson")[0]
    assert recipe.miscs[0].quantity.unit == "oz"
    assert recipe.yeasts[0].quantity.unit == "mL"
    path = tmp_path / "out.beerjson"
    write([recipe], path)
    result = read(path)[0]
    assert result.miscs[0].quantity.unit == "oz"
    assert result.miscs[0].quantity.value == Decimal("2.92")
    assert result.yeasts[0].quantity.kind == "volume"
    assert result.fermentables[0].quantity.unit == "lb"


@pytest.mark.parametrize("suffix", ["beerjson", "json", "btp", "bsmx"])
def test_culture_semantics(tmp_path, suffix):
    r = Recipe(
        "Cultures",
        yeasts=[
            YeastAddition("liquid", form="Liquid", quantity=Quantity(125, "mL")),
            YeastAddition("dry", form="Dry", quantity=Quantity("11.5", "g")),
            YeastAddition("package", form="Dry", quantity=Quantity(1, "package")),
        ],
    )
    path = tmp_path / f"out.{suffix}"
    report = write([r], path)
    out = read(path)[0]
    assert [y.quantity.kind for y in out.yeasts] == ["volume", "mass", "count"]
    assert out.yeasts[0].quantity.si_value == Decimal("0.125")
    assert out.yeasts[1].quantity.si_value == Decimal("0.0115")
    assert out.yeasts[2].quantity.unit == "package"
    if suffix == "bsmx":
        assert any("native-quantity-unsupported" in w for w in report.warnings)


def test_whirlfloc_export_is_explicitly_lossy(tmp_path):
    r = Recipe(
        "Tablet", miscs=[MiscAddition("Whirlfloc", quantity=Quantity(1, "tablet"))]
    )
    path = tmp_path / "out.xml"
    report = write([r], path)
    assert any("count-unsupported" in w and "Whirlfloc" in w for w in report.warnings)
    assert ET.parse(path).find(".//MISC/AMOUNT") is None
    with pytest.raises(ValidationError):
        write([r], tmp_path / "strict.xml", strict=True)
    assert not (tmp_path / "strict.xml").exists()


def xml_misc(
    tmp_path,
    amount="0.00292",
    flag="<AMOUNT_IS_WEIGHT>true</AMOUNT_IS_WEIGHT>",
    display="2.92 oz",
):
    path = tmp_path / "source.xml"
    path.write_text(
        f"<RECIPES><RECIPE><NAME>Contradiction</NAME><MISCS><MISC><NAME>Sea salt</NAME><AMOUNT>{amount}</AMOUNT>{flag}<DISPLAY_AMOUNT>{display}</DISPLAY_AMOUNT></MISC></MISCS></RECIPE></RECIPES>"
    )
    return path


def test_display_never_repairs_canonical(tmp_path):
    report = ConversionReport()
    path = xml_misc(tmp_path)
    r = read_recipes(path, report=report)[0]
    assert r.miscs[0].quantity.si_value == Decimal("0.00292")
    assert r.miscs[0].quantity.original_display == "2.92 oz"
    assert r.miscs[0].source["AMOUNT"] == "0.00292"
    assert any("amount-contradiction" in w for w in report.errors)
    assert any("magnitude-change" in w for w in report.errors)
    with pytest.raises(ValidationError):
        read(path, strict=True)
    dest = tmp_path / "output.xml"
    dest.write_text("existing content")
    with pytest.raises(ValidationError):
        write([r], dest, strict=True)
    assert dest.read_text() == "existing content"


@pytest.mark.parametrize(
    "flag,display,code",
    [
        ("", "2.92 oz", "ambiguous-unit"),
        ("<AMOUNT_IS_WEIGHT>nonsense</AMOUNT_IS_WEIGHT>", "2.92 oz", "ambiguous-unit"),
        (
            "<AMOUNT_IS_WEIGHT>false</AMOUNT_IS_WEIGHT>",
            "2.92 oz",
            "dimension-contradiction",
        ),
        (
            "<AMOUNT_IS_WEIGHT>true</AMOUNT_IS_WEIGHT>",
            "1 tablet",
            "dimension-contradiction",
        ),
    ],
)
def test_ambiguous_flags(tmp_path, flag, display, code):
    report = ConversionReport()
    read_recipes(xml_misc(tmp_path, flag=flag, display=display), report=report)
    assert any(code in w for w in report.errors)


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "nonsense"])
def test_invalid_quantities(tmp_path, value):
    report = ConversionReport()
    recipe = read_recipes(xml_misc(tmp_path, amount=value), report=report)[0]
    assert any("invalid-quantity" in w for w in report.errors)
    target = tmp_path / "out.xml"
    write([recipe], target)
    assert ET.parse(target).find(".//MISC/AMOUNT") is None


def test_validation_behaviors():
    r = Recipe(
        "Warnings",
        batch_size_l=20,
        boil_time_min=60,
        hops=[HopAddition("long boil", amount_kg=0.01, time_min=70, use="Boil")],
        yeasts=[YeastAddition("empty", form="Liquid", quantity=Quantity(0, "L"))],
        miscs=[
            MiscAddition("salt", quantity=Quantity(3, "kg")),
            MiscAddition("missing", amount=1),
        ],
    )
    report = validate_recipes([r])
    for code in ("hop-time", "zero-culture", "suspicious-quantity", "ambiguous-unit"):
        assert any(code in w for w in report.warnings)


def test_bsmx_supported_roundtrip(tmp_path):
    source = read(FIXTURES / "gose.beerjson")
    xml = tmp_path / "source.xml"
    write(source, xml, profile="grainfather")
    source = read(xml)
    target = tmp_path / "out.bsmx"
    report = write(source, target, profile="beersmith-bsmx")
    result = read(target)[0]
    for old, new in zip(source[0].miscs, result.miscs):
        assert old.quantity.kind == new.quantity.kind
        assert abs(old.quantity.si_value - new.quantity.si_value) <= TOL
        assert old.use == new.use
    assert result.yeasts[0].quantity.si_value > 0
    assert any("provisional-writer" in w for w in report.warnings)
    # Native supported mass fields must be correct independently of BC extensions.
    root = ET.parse(target)
    for el, old in zip(root.findall(".//Misc"), source[0].miscs):
        assert el.findtext("F_M_UNITS") == "2"
        assert (
            abs(
                Quantity(el.findtext("F_M_AMOUNT"), "oz").si_value
                - old.quantity.si_value
            )
            <= TOL
        )
        el.remove(el.find("BC_QUANTITY"))
    root.write(target)
    native = read(target)[0]
    for old, new in zip(source[0].miscs, native.miscs):
        assert abs(old.quantity.si_value - new.quantity.si_value) <= TOL


def test_attenuation_fixture():
    r = read(FIXTURES / "domo_after.bsmx")[0]
    assert r.yeasts[0].attenuation == 75
    assert r.yeasts[0].quantity.kind == "volume"
    assert r.est_fg is None
    assert "F_R_FG_MEASURED" in r.measured_values


def test_bsmx_unknown_unit_is_not_guessed(tmp_path):
    path = tmp_path / "unknown.bsmx"
    path.write_text(
        "<Selections><Data><Recipe><F_R_NAME>Unknown</F_R_NAME><Ingredients><Data><Misc><F_M_NAME>Unknown salt</F_M_NAME><F_M_AMOUNT>2</F_M_AMOUNT><F_M_UNITS>99</F_M_UNITS></Misc></Data></Ingredients></Recipe></Data></Selections>"
    )
    report = ConversionReport()
    r = read_recipes(path, report=report)[0]
    assert r.miscs[0].quantity.kind == "unknown"
    assert any("ambiguous-unit" in w for w in report.errors)


def test_phase_loss_and_merge_detection():
    old = Recipe(
        "Phases",
        miscs=[
            MiscAddition("Gypsum", use="Mash", quantity=Quantity(1, "g")),
            MiscAddition("Gypsum", use="Sparge", quantity=Quantity(2, "g")),
        ],
    )
    new = Recipe(
        "Phases", miscs=[MiscAddition("Gypsum", use="Boil", quantity=Quantity(3, "g"))]
    )
    report = ConversionReport()
    compare_recipes([old], [new], report)
    assert any("phase-loss" in w for w in report.errors)
    assert any("salt-phase-merge" in w for w in report.errors)


def test_packaging_not_boiled(tmp_path):
    r = Recipe(
        "Packaging",
        miscs=[MiscAddition("Sugar", use="Packaging", quantity=Quantity(10, "g"))],
    )
    path = tmp_path / "out.bsmx"
    report = write([r], path)
    assert ET.parse(path).find(".//Misc/F_M_USE") is None
    assert read(path)[0].miscs[0].use == "Packaging"
    assert any("native-phase-unsupported" in w for w in report.errors)


def test_unknown_report_and_direct_adapter(tmp_path):
    from brewconvert.formats.beerxml import read as adapter_read
    from brewconvert.formats.beerxml import write as adapter_write

    path = xml_misc(tmp_path, amount="0.01", display="10 g")
    text = path.read_text().replace(
        "</RECIPE>", "<CUSTOM><VALUE>42</VALUE></CUSTOM><OG>1.040</OG></RECIPE>"
    )
    path.write_text(text)
    report = ConversionReport()
    recipes = adapter_read(path, report=report)
    assert "CUSTOM" in recipes[0].unknown_fields
    assert recipes[0].measured_values["OG"] == "1.040"
    adapter_write(recipes, tmp_path / "out.xml", report=report)
    assert any("unsupported-source" in w and "CUSTOM" in w for w in report.warnings)
    assert any("measured-values" in w for w in report.warnings)


def test_cli_strict(tmp_path, capsys):
    path = xml_misc(tmp_path)
    assert main(["validate", str(path)]) == 0
    assert main(["validate", str(path), "--strict"]) == 2
    assert (
        main(
            [
                "convert",
                str(path),
                str(tmp_path / "out.xml"),
                "--to",
                "beerxml",
                "--strict",
                "--report",
            ]
        )
        == 2
    )
    assert not (tmp_path / "out.xml").exists()
    assert "Sea salt" in capsys.readouterr().out


def test_profiles_reject_ignored_options(tmp_path):
    with pytest.raises(ValueError, match="Unsupported profile"):
        write([Recipe("Profile")], tmp_path / "out.xml", profile="invented")


def test_display_rounding_tolerance(tmp_path):
    q = Quantity("2.9199999", "oz")
    report = ConversionReport()
    read_recipes(
        xml_misc(tmp_path, amount=str(q.si_value), display="2.92 oz"), report=report
    )
    assert not report.errors


def test_zero_not_missing(tmp_path):
    r = Recipe(
        "Zero",
        efficiency_pct=0,
        boil_time_min=0,
        hops=[
            HopAddition(
                "Zero time", amount_kg=0.01, time_min=0, temperature_c=0, use="Boil"
            )
        ],
    )
    path = tmp_path / "out.beerjson"
    write([r], path)
    out = read(path)[0]
    assert out.efficiency_pct == 0
    assert out.hops[0].time_min == 0
    assert out.hops[0].temperature_c == 0


def test_promash_quantity_and_unicode(tmp_path):
    r = Recipe(
        "Text",
        notes="5.2–5.4; 3–4 weeks; CO₂; 65 °C",
        miscs=[
            MiscAddition(
                "Coriander",
                quantity=Quantity("5.83", "oz"),
                type="Spice",
                use="Boil",
                time_min=5,
            )
        ],
    )
    path = tmp_path / "out.promash.txt"
    write([r], path)
    out = read(path)[0]
    assert out.miscs[0].quantity.si_value == r.miscs[0].quantity.si_value
    assert out.miscs[0].use == "Boil"
    assert out.notes == r.notes


def test_json_keeps_decimal_precision(tmp_path):
    value = "2.920000000000000000123"
    r = Recipe(
        "Precision", miscs=[MiscAddition("Salt", quantity=Quantity(value, "oz"))]
    )
    for suffix in ("beerjson", "json"):
        path = tmp_path / f"out.{suffix}"
        write([r], path)
        assert value in path.read_text()
        assert read(path)[0].miscs[0].quantity.value == Decimal(value)


@pytest.mark.parametrize(
    "source",
    [
        "domo_before.xml",
        "domo_after.bsmx",
        "sample.beerjson",
        "sample.brewfather.json",
        "test.btp",
        "sample.promash.txt",
    ],
)
@pytest.mark.parametrize(
    "target", ["xml", "bsmx", "beerjson", "json", "btp", "promash.txt"]
)
def test_fixture_conversion_semantics(tmp_path, source, target):
    from brewconvert.report import additions, quantity_of

    recipes = read(FIXTURES / source)
    path = tmp_path / f"out.{target}"
    report = write(recipes, path)
    result = read(path)
    assert len(result) == len(recipes)
    assert result[0].name == recipes[0].name
    by_name = {}
    for item in additions(result[0]):
        by_name.setdefault(item.name, []).append(item)
    for item in additions(recipes[0]):
        q = quantity_of(item)
        if not q or not q.valid or q.status == "ambiguous":
            continue
        matched = by_name.get(item.name, [])
        dest = matched.pop(0) if matched else None
        outq = quantity_of(dest) if dest else None
        preserved = (
            outq and q.kind == outq.kind and outq.valid and outq.status != "ambiguous"
        )
        if preserved and q.si_value is not None:
            preserved = abs(q.si_value - outq.si_value) <= TOL
        if not preserved:
            assert any(
                item.name in w
                and (
                    "quantity-loss" in w
                    or "ingredient-loss" in w
                    or "magnitude-change" in w
                )
                for w in report.warnings
            )


def test_multiple_beertools_recipes(tmp_path):
    path = tmp_path / "out.btp"
    recipes = [Recipe("One"), Recipe("Two")]
    write(recipes, path)
    assert [r.name for r in read(path)] == ["One", "Two"]


def test_standards_profile_reports_phase_loss(tmp_path):
    r = Recipe(
        "Phase", miscs=[MiscAddition("Salt", quantity=Quantity(1, "g"), use="Sparge")]
    )
    report = write([r], tmp_path / "standard.xml", profile="standard")
    assert any("phase-loss" in w for w in report.errors)
    assert read(tmp_path / "standard.xml")[0].miscs[0].use is None
    write([r], tmp_path / "grainfather.xml", profile="grainfather")
    assert read(tmp_path / "grainfather.xml")[0].miscs[0].use == "Sparge"


def test_invalid_unit_object_and_negative_display(tmp_path):
    report = validate_recipes(
        [Recipe("Bad unit", miscs=[MiscAddition("Salt", quantity=Quantity(1, 42))])]
    )
    assert any("ambiguous-unit" in w for w in report.errors)
    report = ConversionReport()
    read_recipes(xml_misc(tmp_path, display="-2 g"), report=report)
    assert any("invalid-display" in w for w in report.errors)


def test_library_without_report_emits_warnings(tmp_path):
    with pytest.warns(UserWarning, match="amount-contradiction"):
        read_recipes(xml_misc(tmp_path))


def test_no_placeholder_unit_emitted(tmp_path):
    r = Recipe(
        "Count", yeasts=[YeastAddition("packet", quantity=Quantity(1, "package"))]
    )
    path = tmp_path / "out.beerjson"
    write([r], path)
    assert '"unit": "package"' in path.read_text()
    assert '"unit": "unit"' not in path.read_text()


def test_attenuation_zero_endpoint(tmp_path):
    path = tmp_path / "zero.bsmx"
    path.write_text(
        "<Selections><Recipe><F_R_NAME>Attenuation</F_R_NAME><Ingredients><Data><Yeast><F_Y_NAME>Culture</F_Y_NAME><F_Y_MIN_ATTENUATION>0</F_Y_MIN_ATTENUATION><F_Y_MAX_ATTENUATION>80</F_Y_MAX_ATTENUATION></Yeast></Data></Ingredients></Recipe></Selections>"
    )
    assert read(path)[0].yeasts[0].attenuation == 40


def test_tiny_liquid_yeast_not_rounded_to_zero(tmp_path):
    q = Quantity("0.000001", "mL")
    recipe = Recipe(
        "Precision", yeasts=[YeastAddition("Liquid", form="Liquid", quantity=q)]
    )
    path = tmp_path / "tiny.xml"
    write([recipe], path)
    assert read(path)[0].yeasts[0].quantity.si_value == q.si_value > 0


def test_bsmx_equipment_targets_are_not_measured(tmp_path):
    r = Recipe(
        "Targets",
        batch_size_l=20,
        boil_size_l=25,
        boil_time_min=60,
        efficiency_pct=0,
        est_og=1.05,
    )
    path = tmp_path / "equipment.bsmx"
    write([r], path)
    tree = ET.parse(path)
    assert tree.find(".//F_R_VOLUME_MEASURED") is None
    assert tree.find(".//F_R_OG_MEASURED") is None
    assert tree.findtext(".//F_R_EQUIPMENT/F_E_BOIL_TIME") == "60.000000000000"
    out = read(path)[0]
    assert abs(out.batch_size_l - 20) < 1e-8
    assert out.boil_time_min == 60
    assert out.efficiency_pct == 0
    assert out.est_og == 1.05
    fixture = read(FIXTURES / "domo_after.bsmx")[0]
    assert fixture.boil_time_min == 60
    assert fixture.est_og == 1.05
    assert fixture.measured_values["F_R_OG_MEASURED"] == "1.0460000"
