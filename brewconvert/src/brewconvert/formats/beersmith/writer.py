from __future__ import annotations

import datetime as _dt
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from brewconvert.formats.boundary import writer
from brewconvert.model import Recipe
from brewconvert.model.units import c_to_f, l_to_floz

from .quantities import write_quantity


def _add(parent: ET.Element, tag: str, value: object | None) -> ET.Element:
    if value is None or value == "":
        return None
    el = ET.SubElement(parent, tag)
    if value is not None:
        el.text = str(value)
    return el


def _num(value: float | None, digits: int = 12) -> str | None:
    return None if value is None else f"{value:.{digits}f}"


@writer("beersmith-bsmx")
def write(recipes: list[Recipe], path: str | Path, profile: str | None = None) -> None:
    """Write a minimal BeerSmith BSMX-style file.

    This is intentionally a draft writer. It produces an XML vocabulary BeerSmith-like
    enough for field-map development, but should be validated in BeerSmith before relying
    on it for production recipe exchange.
    """
    root = ET.Element("Selections")
    _add(root, "_PERMID_", 0)
    _add(root, "_MOD_", _dt.datetime.now(_dt.timezone.utc).date().isoformat())
    _add(root, "Name", "Selections")
    _add(root, "Type", 7372)
    _add(root, "Size", len(recipes))
    data_root = ET.SubElement(root, "Data")

    for r in recipes:
        rec = ET.SubElement(data_root, "Recipe")
        _add(rec, "_PERMID_", 0)
        _add(rec, "_MOD_", _dt.datetime.now(_dt.timezone.utc).date().isoformat())
        _add(rec, "F_R_NAME", r.name)
        _add(rec, "F_R_BREWER", r.brewer or "")
        _add(
            rec,
            "F_R_DATE",
            r.date or _dt.datetime.now(_dt.timezone.utc).date().isoformat(),
        )
        equipment = ET.SubElement(rec, "F_R_EQUIPMENT")
        _add(equipment, "F_E_BATCH_VOL", _num(l_to_floz(r.batch_size_l)))
        _add(equipment, "F_E_BOIL_VOL", _num(l_to_floz(r.boil_size_l)))
        _add(equipment, "F_E_BOIL_TIME", _num(r.boil_time_min))
        _add(equipment, "F_E_EFFICIENCY", _num(r.efficiency_pct))
        _add(rec, "F_R_DESIRED_OG", _num(r.est_og))
        _add(rec, "BC_EST_FG", _num(r.est_fg))
        _add(rec, "F_R_DESIRED_IBU", _num(r.ibu))
        _add(rec, "F_R_DESIRED_COLOR", _num(r.est_color_srm))
        _add(rec, "F_R_NOTES", r.notes or "")

        ingredients = ET.SubElement(rec, "Ingredients")
        _add(ingredients, "Name", "Ingredients")
        _add(
            ingredients,
            "Size",
            len(r.fermentables) + len(r.hops) + len(r.miscs) + len(r.yeasts),
        )
        idata = ET.SubElement(ingredients, "Data")

        for f in r.fermentables:
            g = ET.SubElement(idata, "Grain")
            _add(g, "F_G_NAME", f.name)
            _add(g, "F_G_TYPE", 0)
            _add(
                g,
                "F_G_AMOUNT",
                format(f.quantity.to("oz"), ".12f")
                if f.amount_kg is not None
                else None,
            )
            _add(g, "F_G_COLOR", _num(f.color_srm))
            _add(g, "F_G_YIELD", _num(f.yield_pct))
            _add(g, "F_ORDER", 0)

        for h in r.hops:
            he = ET.SubElement(idata, "Hops")
            _add(he, "F_H_NAME", h.name)
            _add(he, "F_H_TYPE", 0)
            _add(he, "F_H_FORM", 0)
            _add(he, "F_H_ALPHA", _num(h.alpha))
            _add(
                he,
                "F_H_AMOUNT",
                format(h.quantity.to("oz"), ".12f")
                if h.amount_kg is not None
                else None,
            )
            _add(he, "F_H_BOIL_TIME", _num(h.time_min))
            _add(he, "F_H_WHIRLPOOL_TEMP", _num(c_to_f(h.temperature_c)))
            _add(he, "F_H_IBU_CONTRIB", _num(0))
            _add(he, "F_H_USE", 0 if (h.use or "").lower() == "boil" else None)
            _add(he, "BC_PHASE", h.use)
            _add(he, "F_ORDER", 0)

        for m in r.miscs:
            me = ET.SubElement(idata, "Misc")
            _add(me, "F_M_NAME", m.name)
            _add(me, "F_M_TYPE", 5 if m.type == "Water Agent" else 4)
            write_quantity(me, m.quantity, "misc", _add)
            _add(
                me,
                "F_M_USE",
                {"mash": 1, "sparge": 5, "boil": 0}.get((m.use or "").lower()),
            )
            _add(me, "F_M_TIME", _num(m.time_min))
            _add(me, "BC_PHASE", m.use)
            _add(me, "F_ORDER", 0)

        for y in r.yeasts:
            ye = ET.SubElement(idata, "Yeast")
            _add(ye, "F_Y_NAME", y.name)
            _add(ye, "F_Y_FORM", 1 if (y.form or "").lower() == "liquid" else 0)
            write_quantity(ye, y.quantity, "yeast", _add)
            _add(ye, "BC_PHASE", y.use)
            if y.attenuation is not None:
                _add(ye, "F_Y_MIN_ATTENUATION", _num(y.attenuation))
                _add(ye, "F_Y_MAX_ATTENUATION", _num(y.attenuation))
            _add(ye, "F_ORDER", 0)

    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    Path(path).write_bytes(pretty)
