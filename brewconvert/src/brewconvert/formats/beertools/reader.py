from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from brewconvert.model import Recipe, Style, FermentableAddition, HopAddition, YeastAddition, MiscAddition, MashStep


def _local(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _child(el: ET.Element | None, name: str) -> ET.Element | None:
    if el is None:
        return None
    for c in list(el):
        if _local(c.tag) == name:
            return c
    return None


def _children(el: ET.Element | None, name: str) -> list[ET.Element]:
    if el is None:
        return []
    return [c for c in list(el) if _local(c.tag) == name]


def _text(el: ET.Element | None, name: str | None = None) -> str | None:
    target = _child(el, name) if name else el
    if target is None or target.text is None:
        return None
    return target.text.strip()


def _num(el: ET.Element | None, name: str | None = None) -> float | None:
    target = _child(el, name) if name else el
    if target is None:
        return None
    val = _text(target, "Value") or target.text or _text(target, "Text")
    if val in (None, ""):
        return None
    try:
        return float(str(val).strip())
    except ValueError:
        return None


def _unit(el: ET.Element | None, name: str | None = None) -> str | None:
    target = _child(el, name) if name else el
    u = _text(target, "Unit") if target is not None else None
    return u.lower() if u else None


def _quantity(el: ET.Element | None, name: str, kind: str | None = None) -> float | None:
    target = _child(el, name)
    n = _num(target)
    if n is None:
        return None
    u = _unit(target)
    if kind == "mass":
        if u in {"g", "gram", "grams"}:
            return n / 1000
        if u in {"lb", "lbs", "pound", "pounds"}:
            return n * 0.45359237
        if u in {"oz", "ounce", "ounces"}:
            return n * 0.028349523125
    if kind == "volume":
        if u in {"gal", "gallon", "gallons"}:
            return n * 3.785411784
        if u in {"ml"}:
            return n / 1000
        if u in {"fl oz"}:
            return n * 0.0295735295625
    if kind == "temp":
        if u in {"f", "°f"}:
            return (n - 32) * 5 / 9
    return n


def _children_as_dict(el: ET.Element | None) -> dict[str, Any]:
    if el is None:
        return {}
    return {_local(c.tag): ''.join(c.itertext()).strip() for c in list(el)}


def _findall_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [e for e in root.iter() if _local(e.tag) == name]


def read(path: str | Path) -> list[Recipe]:
    root = ET.parse(path).getroot()
    if _local(root.tag) != "Recipe":
        raise ValueError("Not a BeerTools Pro Recipe XML document")

    recipe = Recipe(
        name=_text(root, "Name") or "Untitled",
        brewer=_text(root, "Author"),
        date=_text(root, "Date"),
        notes=_text(root, "Notes") or _text(root, "Description"),
        batch_size_l=_quantity(root, "FinalVolume", "volume"),
        boil_size_l=_quantity(root, "KettleVolume", "volume"),
        boil_time_min=_quantity(root, "BoilDuration"),
        efficiency_pct=_quantity(root, "BrewHouseYield"),
        est_fg=_quantity(root, "TGReading"),
        est_og=_quantity(root, "OGReading"),
        source_format="beertools-btp",
        source_metadata={"version": root.attrib.get("version"), "namespace": root.tag.split('}')[0][1:] if root.tag.startswith('{') else None},
    )

    style_el = _child(root, "Style")
    if style_el is not None:
        recipe.style = Style(
            name=_text(style_el, "Name"),
            category_number=_text(style_el, "Category"),
            style_guide=_text(style_el, "Guide") or _text(style_el, "Guidelines"),
            type=_text(style_el, "Type"),
            source=_children_as_dict(style_el),
        )

    ingredients = _child(root, "Ingredients")
    for item in list(ingredients) if ingredients is not None else []:
        kind = _local(item.tag)
        name = _text(item, "Name") or f"Unnamed {kind}"
        stage = _text(item, "Stage")
        duration = _quantity(item, "Duration")
        if kind in {"Grain", "Extract", "Adjunct"}:
            recipe.fermentables.append(FermentableAddition(
                name=name,
                amount_kg=_quantity(item, "Quantity", "mass"),
                type="Extract" if kind == "Extract" else "Adjunct" if kind == "Adjunct" else "Grain",
                yield_pct=_quantity(item, "DryBasisFineGrind") or _quantity(item, "Yield"),
                color_srm=_quantity(item, "Color"),
                source=_children_as_dict(item),
            ))
        elif kind == "Hop":
            recipe.hops.append(HopAddition(
                name=name,
                amount_kg=_quantity(item, "Quantity", "mass"),
                alpha=_quantity(item, "Alpha"),
                use=stage,
                time_min=duration,
                form=_text(item, "Form"),
                source=_children_as_dict(item),
            ))
        elif kind == "Yeast":
            low = _quantity(item, "AttenuationLow")
            high = _quantity(item, "AttenuationHigh")
            attenuation = (low + high) / 2 if low is not None and high is not None else low or high
            recipe.yeasts.append(YeastAddition(
                name=name,
                laboratory=_text(item, "Supplier") or _text(item, "Origin"),
                product_id=_text(item, "CatalogNumber") or _text(item, "Code"),
                type=_text(item, "Type"),
                form=_text(item, "Medium"),
                amount=_quantity(item, "Quantity"),
                attenuation=attenuation,
                source=_children_as_dict(item),
            ))
        else:
            recipe.miscs.append(MiscAddition(
                name=name,
                amount=_quantity(item, "Quantity"),
                time_min=duration,
                type=kind,
                use=stage,
                source=_children_as_dict(item),
            ))

    for s in _findall_local(root, "Mash") + _findall_local(root, "Rest"):
        if _local(s.tag) == "Mash" and not _text(s, "Name") and not _child(s, "Temperature"):
            continue
        recipe.mash_steps.append(MashStep(
            name=_text(s, "Name") or "Mash Step",
            type=_local(s.tag),
            step_time_min=_quantity(s, "Duration"),
            step_temp_c=_quantity(s, "Temperature", "temp") or _quantity(s, "Temp", "temp"),
            source=_children_as_dict(s),
        ))

    return [recipe]
