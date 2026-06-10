from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from brewconvert.model import Recipe, Style, FermentableAddition, HopAddition, YeastAddition, MiscAddition, MashStep


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


def _bool(el: ET.Element | None, tag: str) -> bool | None:
    txt = _text(el, tag)
    if txt is None:
        return None
    return txt.lower() in {"true", "1", "yes"}


def _children_as_dict(el: ET.Element | None) -> dict[str, str]:
    if el is None:
        return {}
    return {c.tag: (c.text or "") for c in list(el)}


def read(path: str | Path) -> list[Recipe]:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "RECIPES":
        raise ValueError("Not a BeerXML RECIPES document")

    recipes: list[Recipe] = []
    for rel in root.findall("RECIPE"):
        recipe = Recipe(
            name=_text(rel, "NAME", "Untitled") or "Untitled",
            type=_text(rel, "TYPE"),
            brewer=_text(rel, "BREWER"),
            date=_text(rel, "DATE"),
            batch_size_l=_float(rel, "BATCH_SIZE"),
            boil_size_l=_float(rel, "BOIL_SIZE"),
            boil_time_min=_float(rel, "BOIL_TIME"),
            efficiency_pct=_float(rel, "EFFICIENCY"),
            est_og=_float(rel, "EST_OG"),
            est_fg=_float(rel, "EST_FG"),
            ibu=_float(rel, "IBU"),
            est_abv=_float(rel, "EST_ABV"),
            est_color_srm=_float(rel, "EST_COLOR"),
            notes=_text(rel, "NOTES"),
            ibu_method=_text(rel, "IBU_METHOD"),
            source_format="beerxml",
            source_metadata={"root_tag": root.tag, "encoding": "ISO-8859-1"},
        )

        style_el = rel.find("STYLE")
        if style_el is not None:
            recipe.style = Style(
                name=_text(style_el, "NAME"),
                category_number=_text(style_el, "CATEGORY_NUMBER"),
                style_letter=_text(style_el, "STYLE_LETTER"),
                style_guide=_text(style_el, "STYLE_GUIDE"),
                type=_text(style_el, "TYPE"),
                source=_children_as_dict(style_el),
            )

        for f in rel.findall("./FERMENTABLES/FERMENTABLE"):
            recipe.fermentables.append(FermentableAddition(
                name=_text(f, "NAME", "Unnamed fermentable") or "Unnamed fermentable",
                type=_text(f, "TYPE"),
                amount_kg=_float(f, "AMOUNT"),
                yield_pct=_float(f, "YIELD"),
                color_srm=_float(f, "COLOR"),
                source=_children_as_dict(f),
            ))

        for h in rel.findall("./HOPS/HOP"):
            temp = _float(h, "HOP_TEMP")
            if temp is None:
                temp = _float(h, "TEMPERATURE")
            recipe.hops.append(HopAddition(
                name=_text(h, "NAME", "Unnamed hop") or "Unnamed hop",
                alpha=_float(h, "ALPHA"),
                amount_kg=_float(h, "AMOUNT"),
                use=_text(h, "USE"),
                time_min=_float(h, "TIME"),
                form=_text(h, "FORM"),
                temperature_c=temp,
                source=_children_as_dict(h),
            ))

        for y in rel.findall("./YEASTS/YEAST"):
            recipe.yeasts.append(YeastAddition(
                name=_text(y, "NAME", "Unnamed yeast") or "Unnamed yeast",
                type=_text(y, "TYPE"),
                form=_text(y, "FORM"),
                amount=_float(y, "AMOUNT"),
                amount_is_weight=_bool(y, "AMOUNT_IS_WEIGHT"),
                display_amount=_text(y, "DISPLAY_AMOUNT"),
                attenuation=_float(y, "ATTENUATION"),
                laboratory=_text(y, "LABORATORY"),
                product_id=_text(y, "PRODUCT_ID"),
                source=_children_as_dict(y),
            ))

        for m in rel.findall("./MISCS/MISC"):
            recipe.miscs.append(MiscAddition(
                name=_text(m, "NAME", "Unnamed misc") or "Unnamed misc",
                amount=_float(m, "AMOUNT"),
                display_amount=_text(m, "DISPLAY_AMOUNT"),
                amount_is_weight=_bool(m, "AMOUNT_IS_WEIGHT"),
                time_min=_float(m, "TIME"),
                type=_text(m, "TYPE"),
                use=_text(m, "USE"),
                source=_children_as_dict(m),
            ))

        for s in rel.findall("./MASH/MASH_STEPS/MASH_STEP"):
            recipe.mash_steps.append(MashStep(
                name=_text(s, "NAME", "Mash Step") or "Mash Step",
                type=_text(s, "TYPE"),
                step_time_min=_float(s, "STEP_TIME"),
                step_temp_c=_float(s, "STEP_TEMP"),
                ramp_time_min=_float(s, "RAMP_TIME"),
                end_temp_c=_float(s, "END_TEMP"),
                source=_children_as_dict(s),
            ))

        known = {"NAME","VERSION","DATE","TYPE","BREWER","BATCH_SIZE","BOIL_SIZE","BOIL_TIME","EFFICIENCY","EST_OG","EST_FG","IBU","EST_ABV","CALORIES","EST_COLOR","NOTES","IBU_METHOD","STYLE","WATERS","FERMENTABLES","HOPS","YEASTS","MISCS","MASH","FERMENTATION_STAGES","PRIMARY_AGE","PRIMARY_TEMP","SECONDARY_AGE","SECONDARY_TEMP"}
        recipe.unknown_fields = {c.tag: ET.tostring(c, encoding="unicode") for c in rel if c.tag not in known}
        recipes.append(recipe)
    return recipes
