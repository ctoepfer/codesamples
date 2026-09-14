from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from brewconvert.formats.boundary import reader
from brewconvert.model import (
    FermentableAddition,
    HopAddition,
    MiscAddition,
    Recipe,
    YeastAddition,
)
from brewconvert.model.units import Quantity, f_to_c, floz_to_l

from .quantities import read_quantity


def _text(el: ET.Element | None, tag: str, default: str | None = None) -> str | None:
    if el is None:
        return default
    child = el.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _float(el: ET.Element | None, tag: str) -> float | None:
    txt = _text(el, tag)
    if txt in (None, ""):
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def _children_as_dict(el: ET.Element | None) -> dict[str, str]:
    if el is None:
        return {}
    return {c.tag: (c.text or "") for c in list(el)}


def _hop_use(h: ET.Element) -> str:
    explicit = _text(h, "BC_PHASE")
    if explicit is not None:
        return explicit
    if _text(h, "F_H_USE") == "0":
        return "Boil"
    code = _text(h, "F_H_USE")
    return f"BSMX use {code}" if code is not None else "Unknown"


@reader("beersmith-bsmx")
def read(path: str | Path) -> list[Recipe]:
    root = ET.parse(path).getroot()
    if root.tag != "Selections":
        raise ValueError("Not a BeerSmith BSMX Selections document")
    recipes: list[Recipe] = []
    for rec in root.findall(".//Recipe"):
        recipe = Recipe(
            name=_text(rec, "F_R_NAME", "Untitled") or "Untitled",
            brewer=_text(rec, "F_R_BREWER"),
            date=_text(rec, "F_R_DATE"),
            batch_size_l=floz_to_l(_float(rec, "F_R_EQUIPMENT/F_E_BATCH_VOL")),
            boil_time_min=_float(rec, "F_R_EQUIPMENT/F_E_BOIL_TIME"),
            boil_size_l=floz_to_l(_float(rec, "F_R_EQUIPMENT/F_E_BOIL_VOL")),
            efficiency_pct=_float(rec, "F_R_EQUIPMENT/F_E_EFFICIENCY"),
            est_og=_float(rec, "F_R_DESIRED_OG"),
            est_fg=_float(rec, "BC_EST_FG"),
            ibu=_float(rec, "F_R_DESIRED_IBU"),
            est_color_srm=_float(rec, "F_R_DESIRED_COLOR"),
            notes=_text(rec, "F_R_NOTES"),
            source_format="beersmith-bsmx",
            source_metadata={"root_tag": root.tag},
        )
        data = rec.find("./Ingredients/Data")
        if data is not None:
            for g in data.findall("Grain"):
                recipe.fermentables.append(
                    FermentableAddition(
                        name=_text(g, "F_G_NAME", "Unnamed grain") or "Unnamed grain",
                        quantity=Quantity.from_measure(
                            _text(g, "F_G_AMOUNT"), "oz", source_field="F_G_AMOUNT"
                        ),
                        color_srm=_float(g, "F_G_COLOR"),
                        yield_pct=_float(g, "F_G_YIELD"),
                        type="Grain",
                        source=_children_as_dict(g),
                    )
                )
            for h in data.findall("Hops"):
                temp_f = _float(h, "F_H_WHIRLPOOL_TEMP")
                recipe.hops.append(
                    HopAddition(
                        name=_text(h, "F_H_NAME", "Unnamed hop") or "Unnamed hop",
                        quantity=Quantity.from_measure(
                            _text(h, "F_H_AMOUNT"), "oz", source_field="F_H_AMOUNT"
                        ),
                        alpha=_float(h, "F_H_ALPHA"),
                        use=_hop_use(h),
                        time_min=_float(h, "F_H_BOIL_TIME"),
                        form="Pellet"
                        if (_text(h, "F_H_FORM") in {"0", None})
                        else _text(h, "F_H_FORM"),
                        temperature_c=f_to_c(temp_f) if temp_f is not None else None,
                        source=_children_as_dict(h),
                    )
                )
            for m in data.findall("Misc"):
                recipe.miscs.append(
                    MiscAddition(
                        name=_text(m, "F_M_NAME", "Unnamed misc") or "Unnamed misc",
                        quantity=read_quantity(m, "misc"),
                        time_min=_float(m, "F_M_TIME"),
                        type="Water Agent" if _text(m, "F_M_TYPE") == "5" else "Other",
                        use=_text(m, "BC_PHASE")
                        or {"1": "Mash", "5": "Sparge", "0": "Boil"}.get(
                            _text(m, "F_M_USE") or "", _text(m, "F_M_USE")
                        ),
                        amount_is_weight=(_text(m, "F_M_IMPORT_AS_WEIGHT") == "1"),
                        source=_children_as_dict(m),
                    )
                )
            for y in data.findall("Yeast"):
                recipe.yeasts.append(
                    YeastAddition(
                        name=_text(y, "F_Y_NAME", "Unnamed yeast") or "Unnamed yeast",
                        quantity=read_quantity(y, "yeast"),
                        attenuation=(
                            _float(y, "F_Y_MIN_ATTENUATION")
                            + _float(y, "F_Y_MAX_ATTENUATION")
                        )
                        / 2
                        if _float(y, "F_Y_MIN_ATTENUATION") is not None
                        and _float(y, "F_Y_MAX_ATTENUATION") is not None
                        else None,
                        use=_text(y, "BC_PHASE"),
                        form="Liquid" if _text(y, "F_Y_FORM") == "1" else "Dry",
                        source=_children_as_dict(y),
                    )
                )
        recipe.measured_values = {c.tag: c.text for c in rec if "MEASURED" in c.tag}
        recipe.calculated_values = {c.tag: c.text for c in rec if "DESIRED" in c.tag}
        recipe.source_metadata["document"] = ET.tostring(rec, encoding="unicode")
        known = {
            "F_R_NAME",
            "F_R_BREWER",
            "F_R_DATE",
            "F_R_DESIRED_OG",
            "F_R_DESIRED_IBU",
            "F_R_DESIRED_COLOR",
            "F_R_NOTES",
            "Ingredients",
            "BC_BATCH_FLOZ",
            "BC_BOIL_FLOZ",
            "BC_BOIL_TIME",
            "BC_EST_FG",
            "_PERMID_",
            "_MOD_",
        }
        recipe.unknown_fields = {
            c.tag: ET.tostring(c, encoding="unicode") for c in rec if c.tag not in known
        }
        recipes.append(recipe)
    return recipes
