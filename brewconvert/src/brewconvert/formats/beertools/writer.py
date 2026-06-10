from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from brewconvert.model import Recipe

NS = "http://www.beertools.com/btp"
ET.register_namespace("b", NS)


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def _add(parent: ET.Element, name: str, value: object | None = None) -> ET.Element:
    el = ET.SubElement(parent, _tag(name))
    if value is not None:
        el.text = str(value)
    return el


def _measure(parent: ET.Element, name: str, value: float | None, unit: str) -> ET.Element:
    el = _add(parent, name)
    _add(el, "Text", "" if value is None else value)
    _add(el, "Value", 0 if value is None else value)
    _add(el, "Unit", unit)
    return el


def _ingredient(parent: ET.Element, kind: str, name: str, amount: float | None, unit: str = "kg") -> ET.Element:
    el = ET.SubElement(parent, _tag(kind))
    _add(el, "Active", "Y")
    _add(el, "Name", name)
    _measure(el, "Quantity", amount, unit)
    _measure(el, "UnitCost", 0, "$ / kg")
    _measure(el, "UnitSize", 1, unit)
    return el


def _one_recipe(r: Recipe) -> ET.Element:
    root = ET.Element(_tag("Recipe"), {"version": "2.1.4.15"})
    _add(root, "Name", r.name)
    _add(root, "Author", r.brewer or "")
    _add(root, "Date", r.date or "")
    _add(root, "Description", r.notes or "")
    _measure(root, "KettleVolume", r.boil_size_l, "L")
    _measure(root, "BoilDuration", r.boil_time_min, "min")
    _measure(root, "FinalVolume", r.batch_size_l, "L")
    _measure(root, "BrewHouseYield", r.efficiency_pct, "%")
    ingredients = _add(root, "Ingredients")

    for f in r.fermentables:
        kind = "Extract" if (f.type or "").lower() == "extract" else "Adjunct" if (f.type or "").lower() == "adjunct" else "Grain"
        el = _ingredient(ingredients, kind, f.name, f.amount_kg, "kg")
        _add(el, "Stage", "Mash")
        _measure(el, "Duration", 0, "min")
        _measure(el, "DryBasisFineGrind", f.yield_pct, "%")
        _measure(el, "Color", f.color_srm, "SRM")

    for h in r.hops:
        el = _ingredient(ingredients, "Hop", h.name, h.amount_kg, "kg")
        _add(el, "Stage", h.use or "Boil")
        _measure(el, "Duration", h.time_min, "min")
        _add(el, "Form", h.form or "Pellet")
        _measure(el, "Alpha", h.alpha, "%")

    for y in r.yeasts:
        el = _ingredient(ingredients, "Yeast", y.name, y.amount, "unit")
        _add(el, "Supplier", y.laboratory or "")
        _add(el, "CatalogNumber", y.product_id or "")
        _add(el, "Type", y.type or "")
        _add(el, "Medium", y.form or "")
        _measure(el, "AttenuationLow", y.attenuation, "%")
        _measure(el, "AttenuationHigh", y.attenuation, "%")

    for m in r.miscs:
        el = _ingredient(ingredients, "Special", m.name, m.amount, "unit")
        _add(el, "Stage", m.use or "")
        _measure(el, "Duration", m.time_min, "min")

    if r.style:
        style = _add(root, "Style")
        _add(style, "Name", r.style.name or "")
        _add(style, "Category", r.style.category_number or "")
        _add(style, "Guide", r.style.style_guide or "")
        _add(style, "Type", r.style.type or "")

    schedule = _add(root, "Schedule")
    for s in r.mash_steps:
        mash = _add(schedule, "Mash")
        _add(mash, "Name", s.name)
        _measure(mash, "Temperature", s.step_temp_c, "C")
        _measure(mash, "Duration", s.step_time_min, "min")
    _measure(root, "OGReading", r.est_og, "sg")
    _measure(root, "TGReading", r.est_fg, "sg")
    _add(root, "Notes", r.notes or "")
    return root


def write(recipes: list[Recipe], path: str | Path, profile: str | None = None) -> None:
    if len(recipes) == 1:
        root = _one_recipe(recipes[0])
    else:
        root = ET.Element(_tag("Recipes"))
        for r in recipes:
            root.append(_one_recipe(r))
    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    Path(path).write_bytes(pretty)
