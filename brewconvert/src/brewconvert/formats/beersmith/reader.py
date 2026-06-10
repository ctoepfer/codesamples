from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from brewconvert.model import Recipe, FermentableAddition, HopAddition, MiscAddition, YeastAddition
from brewconvert.model.units import oz_to_kg, floz_to_l, f_to_c


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
    amount = _float(h, "F_H_AMOUNT") or 0
    boil_time = _float(h, "F_H_BOIL_TIME") or 0
    ibu = _float(h, "F_H_IBU_CONTRIB") or 0
    if boil_time <= 0 and ibu <= 0:
        return "Dry Hop"
    if boil_time and ibu:
        # BeerSmith's exported sample does not clearly flag whirlpool use, but whirlpool
        # additions tend to carry a whirlpool temp and short boil/stand time.
        if boil_time <= 20 and _float(h, "F_H_WHIRLPOOL_TEMP") is not None:
            return "Hop Stand"
        return "Boil"
    return "Boil"


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
            batch_size_l=floz_to_l(_float(rec, "F_R_FINAL_VOL_MEASURED") or _float(rec, "F_R_VOLUME_MEASURED")),
            boil_size_l=floz_to_l(_float(rec, "F_R_BOIL_VOL_MEASURED")),
            est_og=_float(rec, "F_R_OG_MEASURED") or _float(rec, "F_R_DESIRED_OG"),
            est_fg=_float(rec, "F_R_FG_MEASURED"),
            ibu=_float(rec, "F_R_DESIRED_IBU"),
            est_color_srm=_float(rec, "F_R_DESIRED_COLOR"),
            notes=_text(rec, "F_R_NOTES"),
            source_format="beersmith-bsmx",
            source_metadata={"root_tag": root.tag},
        )
        data = rec.find("./Ingredients/Data")
        if data is not None:
            for g in data.findall("Grain"):
                recipe.fermentables.append(FermentableAddition(
                    name=_text(g, "F_G_NAME", "Unnamed grain") or "Unnamed grain",
                    amount_kg=oz_to_kg(_float(g, "F_G_AMOUNT")),
                    color_srm=_float(g, "F_G_COLOR"),
                    yield_pct=_float(g, "F_G_YIELD"),
                    type="Grain",
                    source=_children_as_dict(g),
                ))
            for h in data.findall("Hops"):
                temp_f = _float(h, "F_H_WHIRLPOOL_TEMP")
                recipe.hops.append(HopAddition(
                    name=_text(h, "F_H_NAME", "Unnamed hop") or "Unnamed hop",
                    amount_kg=oz_to_kg(_float(h, "F_H_AMOUNT")),
                    alpha=_float(h, "F_H_ALPHA"),
                    use=_hop_use(h),
                    time_min=_float(h, "F_H_BOIL_TIME"),
                    form="Pellet" if (_text(h, "F_H_FORM") in {"0", None}) else _text(h, "F_H_FORM"),
                    temperature_c=f_to_c(temp_f) if temp_f is not None else None,
                    source=_children_as_dict(h),
                ))
            for m in data.findall("Misc"):
                recipe.miscs.append(MiscAddition(
                    name=_text(m, "F_M_NAME", "Unnamed misc") or "Unnamed misc",
                    amount=_float(m, "F_M_AMOUNT"),
                    time_min=_float(m, "F_M_TIME"),
                    type="Water Agent" if _text(m, "F_M_TYPE") == "5" else "Other",
                    use={"1": "Mash", "5": "Sparge", "0": "Boil"}.get(_text(m, "F_M_USE") or "", _text(m, "F_M_USE")),
                    amount_is_weight=(_text(m, "F_M_IMPORT_AS_WEIGHT") == "1"),
                    source=_children_as_dict(m),
                ))
            for y in data.findall("Yeast"):
                recipe.yeasts.append(YeastAddition(
                    name=_text(y, "F_Y_NAME", "Unnamed yeast") or "Unnamed yeast",
                    amount=_float(y, "F_Y_AMOUNT"),
                    attenuation=(_float(y, "F_Y_MIN_ATTENUATION") or 0 + _float(y, "F_Y_MAX_ATTENUATION") or 0) / 2 if _float(y, "F_Y_MIN_ATTENUATION") and _float(y, "F_Y_MAX_ATTENUATION") else None,
                    form="Liquid" if _text(y, "F_Y_FORM") == "1" else "Dry",
                    source=_children_as_dict(y),
                ))
        recipes.append(recipe)
    return recipes
