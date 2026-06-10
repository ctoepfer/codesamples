from __future__ import annotations

import datetime as _dt
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from brewconvert.model import Recipe
from brewconvert.model.units import kg_to_oz, l_to_floz, c_to_f


def _add(parent: ET.Element, tag: str, value: object | None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if value is not None:
        el.text = str(value)
    return el


def _num(value: float | None, digits: int = 7) -> str:
    return f"{0 if value is None else value:.{digits}f}"


def write(recipes: list[Recipe], path: str | Path, profile: str | None = None) -> None:
    """Write a minimal BeerSmith BSMX-style file.

    This is intentionally a draft writer. It produces an XML vocabulary BeerSmith-like
    enough for field-map development, but should be validated in BeerSmith before relying
    on it for production recipe exchange.
    """
    root = ET.Element("Selections")
    _add(root, "_PERMID_", 0)
    _add(root, "_MOD_", _dt.date.today().isoformat())
    _add(root, "Name", "Selections")
    _add(root, "Type", 7372)
    _add(root, "Size", len(recipes))
    data_root = ET.SubElement(root, "Data")

    for r in recipes:
        rec = ET.SubElement(data_root, "Recipe")
        _add(rec, "_PERMID_", 0)
        _add(rec, "_MOD_", _dt.date.today().isoformat())
        _add(rec, "F_R_NAME", r.name)
        _add(rec, "F_R_BREWER", r.brewer or "")
        _add(rec, "F_R_DATE", r.date or _dt.date.today().isoformat())
        _add(rec, "F_R_VOLUME_MEASURED", _num(l_to_floz(r.batch_size_l)))
        _add(rec, "F_R_FINAL_VOL_MEASURED", _num(l_to_floz(r.batch_size_l)))
        _add(rec, "F_R_BOIL_VOL_MEASURED", _num(l_to_floz(r.boil_size_l)))
        _add(rec, "F_R_OG_MEASURED", _num(r.est_og))
        _add(rec, "F_R_FG_MEASURED", _num(r.est_fg))
        _add(rec, "F_R_DESIRED_IBU", _num(r.ibu))
        _add(rec, "F_R_DESIRED_COLOR", _num(r.est_color_srm))
        _add(rec, "F_R_NOTES", r.notes or "")

        ingredients = ET.SubElement(rec, "Ingredients")
        _add(ingredients, "Name", "Ingredients")
        _add(ingredients, "Size", len(r.fermentables) + len(r.hops) + len(r.miscs) + len(r.yeasts))
        idata = ET.SubElement(ingredients, "Data")

        for f in r.fermentables:
            g = ET.SubElement(idata, "Grain")
            _add(g, "F_G_NAME", f.name)
            _add(g, "F_G_TYPE", 0)
            _add(g, "F_G_AMOUNT", _num(kg_to_oz(f.amount_kg)))
            _add(g, "F_G_COLOR", _num(f.color_srm))
            _add(g, "F_G_YIELD", _num(f.yield_pct))
            _add(g, "F_ORDER", 0)

        for h in r.hops:
            he = ET.SubElement(idata, "Hops")
            _add(he, "F_H_NAME", h.name)
            _add(he, "F_H_TYPE", 0)
            _add(he, "F_H_FORM", 0)
            _add(he, "F_H_ALPHA", _num(h.alpha))
            _add(he, "F_H_AMOUNT", _num(kg_to_oz(h.amount_kg)))
            _add(he, "F_H_BOIL_TIME", _num(h.time_min))
            _add(he, "F_H_WHIRLPOOL_TEMP", _num(c_to_f(h.temperature_c)))
            _add(he, "F_H_IBU_CONTRIB", _num(0))
            _add(he, "F_H_USE", 0)
            _add(he, "F_ORDER", 0)

        for m in r.miscs:
            me = ET.SubElement(idata, "Misc")
            _add(me, "F_M_NAME", m.name)
            _add(me, "F_M_TYPE", 5 if m.type == "Water Agent" else 4)
            _add(me, "F_M_UNITS", 2)
            _add(me, "F_M_AMOUNT", _num(m.amount))
            _add(me, "F_M_USE", {"Mash": 1, "Sparge": 5, "Boil": 0, "Bottle": 0}.get(m.use or "", 0))
            _add(me, "F_M_TIME", _num(m.time_min))
            _add(me, "F_M_IMPORT_AS_WEIGHT", 1 if m.amount_is_weight else 0)
            _add(me, "F_ORDER", 0)

        for y in r.yeasts:
            ye = ET.SubElement(idata, "Yeast")
            _add(ye, "F_Y_NAME", y.name)
            _add(ye, "F_Y_FORM", 1 if (y.form or "").lower() == "liquid" else 0)
            _add(ye, "F_Y_AMOUNT", _num(y.amount))
            if y.attenuation is not None:
                _add(ye, "F_Y_MIN_ATTENUATION", _num(y.attenuation))
                _add(ye, "F_Y_MAX_ATTENUATION", _num(y.attenuation))
            _add(ye, "F_ORDER", 0)

    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    Path(path).write_bytes(pretty)
