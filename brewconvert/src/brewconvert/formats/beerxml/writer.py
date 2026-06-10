from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from brewconvert.model import Recipe


def _add(parent: ET.Element, tag: str, value: object | None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if value is not None:
        el.text = str(value)
    return el


def _fmt_float(value: float | None, digits: int = 6) -> str | None:
    if value is None:
        return None
    txt = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return txt if txt else "0"


def write(recipes: list[Recipe], path: str | Path, profile: str | None = None) -> None:
    root = ET.Element("RECIPES")
    for r in recipes:
        rel = ET.SubElement(root, "RECIPE")
        _add(rel, "NAME", r.name)
        _add(rel, "VERSION", 1)
        _add(rel, "DATE", r.date)
        _add(rel, "TYPE", r.type or "All Grain")
        _add(rel, "BREWER", r.brewer)
        _add(rel, "BATCH_SIZE", _fmt_float(r.batch_size_l, 3))
        _add(rel, "BOIL_SIZE", _fmt_float(r.boil_size_l, 3))
        _add(rel, "BOIL_TIME", _fmt_float(r.boil_time_min, 0))
        _add(rel, "EFFICIENCY", _fmt_float(r.efficiency_pct, 2))
        _add(rel, "EST_OG", _fmt_float(r.est_og, 3))
        _add(rel, "EST_FG", _fmt_float(r.est_fg, 3))
        _add(rel, "IBU", _fmt_float(r.ibu, 1))
        _add(rel, "EST_ABV", _fmt_float(r.est_abv, 1))
        _add(rel, "EST_COLOR", _fmt_float(r.est_color_srm, 6))
        _add(rel, "NOTES", r.notes)
        _add(rel, "IBU_METHOD", r.ibu_method or "Tinseth")

        if r.style:
            style = ET.SubElement(rel, "STYLE")
            _add(style, "NAME", r.style.name)
            _add(style, "VERSION", 1)
            _add(style, "CATEGORY_NUMBER", r.style.category_number)
            _add(style, "STYLE_LETTER", r.style.style_letter)
            _add(style, "STYLE_GUIDE", r.style.style_guide)
            _add(style, "TYPE", r.style.type)

        ET.SubElement(rel, "WATERS")

        fs = ET.SubElement(rel, "FERMENTABLES")
        for f in r.fermentables:
            fe = ET.SubElement(fs, "FERMENTABLE")
            _add(fe, "NAME", f.name)
            _add(fe, "VERSION", 1)
            _add(fe, "TYPE", f.type or "Grain")
            _add(fe, "AMOUNT", _fmt_float(f.amount_kg, 6))
            _add(fe, "YIELD", _fmt_float(f.yield_pct, 6))
            _add(fe, "COLOR", _fmt_float(f.color_srm, 3))

        hs = ET.SubElement(rel, "HOPS")
        for h in r.hops:
            he = ET.SubElement(hs, "HOP")
            _add(he, "NAME", h.name)
            _add(he, "VERSION", 1)
            _add(he, "ALPHA", _fmt_float(h.alpha, 3))
            _add(he, "AMOUNT", _fmt_float(h.amount_kg, 8))
            _add(he, "USE", h.use)
            _add(he, "TIME", _fmt_float(h.time_min, 2))
            _add(he, "FORM", h.form or "Pellet")
            if h.temperature_c is not None:
                _add(he, "TEMPERATURE", _fmt_float(h.temperature_c, 2))
                _add(he, "HOP_TEMP", _fmt_float(h.temperature_c, 2))

        ys = ET.SubElement(rel, "YEASTS")
        for y in r.yeasts:
            ye = ET.SubElement(ys, "YEAST")
            _add(ye, "NAME", y.name)
            _add(ye, "VERSION", 1)
            _add(ye, "TYPE", y.type)
            _add(ye, "FORM", y.form)
            _add(ye, "AMOUNT", _fmt_float(y.amount, 6))
            if y.amount_is_weight is not None:
                _add(ye, "AMOUNT_IS_WEIGHT", str(y.amount_is_weight).lower())
            if y.display_amount:
                _add(ye, "DISPLAY_AMOUNT", y.display_amount)
            _add(ye, "ATTENUATION", _fmt_float(y.attenuation, 2))
            _add(ye, "LABORATORY", y.laboratory)
            _add(ye, "PRODUCT_ID", y.product_id)

        ms = ET.SubElement(rel, "MISCS")
        for m in r.miscs:
            me = ET.SubElement(ms, "MISC")
            _add(me, "NAME", m.name)
            _add(me, "VERSION", 1)
            _add(me, "AMOUNT", _fmt_float(m.amount, 12))
            if m.display_amount:
                _add(me, "DISPLAY_AMOUNT", m.display_amount)
            if m.amount_is_weight is not None:
                _add(me, "AMOUNT_IS_WEIGHT", str(m.amount_is_weight).lower())
            _add(me, "TIME", _fmt_float(m.time_min, 2))
            _add(me, "TYPE", m.type)
            _add(me, "USE", m.use)

        mash = ET.SubElement(rel, "MASH")
        steps = ET.SubElement(mash, "MASH_STEPS")
        for s in r.mash_steps:
            se = ET.SubElement(steps, "MASH_STEP")
            _add(se, "NAME", s.name)
            _add(se, "VERSION", 1)
            _add(se, "TYPE", s.type or "Temperature")
            _add(se, "STEP_TIME", _fmt_float(s.step_time_min, 2))
            _add(se, "STEP_TEMP", _fmt_float(s.step_temp_c, 2))
            _add(se, "RAMP_TIME", _fmt_float(s.ramp_time_min, 2))
            _add(se, "END_TEMP", _fmt_float(s.end_temp_c, 2))

    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="ISO-8859-1")
    Path(path).write_bytes(pretty)
