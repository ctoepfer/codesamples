from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brewconvert.model import Recipe


def _measure(value: float | None, unit: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return {"value": value, "unit": unit}


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if v is not None and _clean(v) not in ({}, [])}
    if isinstance(value, list):
        return [_clean(v) for v in value if v is not None and _clean(v) not in ({}, [])]
    return value


def _timing(use: str | None, time_min: float | None, temperature_c: float | None = None) -> dict[str, Any]:
    return _clean({
        "use": use or "Boil",
        "time": _measure(time_min, "min") if time_min is not None else None,
        "temperature": _measure(temperature_c, "C") if temperature_c is not None else None,
    })


def _recipe(r: Recipe) -> dict[str, Any]:
    style = None
    if r.style:
        style = _clean({
            "name": r.style.name,
            "category_number": r.style.category_number,
            "style_letter": r.style.style_letter,
            "style_guide": r.style.style_guide,
            "type": r.style.type,
        })

    ingredients = {
        "fermentable_additions": [_clean({
            "name": f.name,
            "type": f.type or "Grain",
            "amount": _measure(f.amount_kg, "kg"),
            "yield": _measure(f.yield_pct, "%") if f.yield_pct is not None else None,
            "color": _measure(f.color_srm, "SRM") if f.color_srm is not None else None,
        }) for f in r.fermentables],
        "hop_additions": [_clean({
            "name": h.name,
            "form": h.form or "Pellet",
            "alpha_acid": _measure(h.alpha, "%") if h.alpha is not None else None,
            "amount": _measure(h.amount_kg, "kg"),
            "timing": _timing(h.use, h.time_min, h.temperature_c),
        }) for h in r.hops],
        "miscellaneous_additions": [_clean({
            "name": m.name,
            "type": m.type or "Other",
            "amount": _measure(m.amount, "unit") if m.amount is not None else None,
            "timing": _timing(m.use, m.time_min),
        }) for m in r.miscs],
        "culture_additions": [_clean({
            "name": y.name,
            "producer": y.laboratory,
            "product_id": y.product_id,
            "type": y.type or "Ale",
            "form": y.form or "Liquid",
            "attenuation": _measure(y.attenuation, "%") if y.attenuation is not None else None,
            "amount": _measure(y.amount, "unit") if y.amount is not None else None,
        }) for y in r.yeasts],
    }

    mash = None
    if r.mash_steps:
        mash = {
            "name": "Mash",
            "grain_temperature": _measure(20, "C"),
            "mash_steps": [_clean({
                "name": s.name,
                "type": s.type or "Infusion",
                "step_time": _measure(s.step_time_min, "min") if s.step_time_min is not None else None,
                "step_temperature": _measure(s.step_temp_c, "C") if s.step_temp_c is not None else None,
                "ramp_time": _measure(s.ramp_time_min, "min") if s.ramp_time_min is not None else None,
                "end_temperature": _measure(s.end_temp_c, "C") if s.end_temp_c is not None else None,
            }) for s in r.mash_steps],
        }

    return _clean({
        "name": r.name,
        "type": r.type or "All Grain",
        "author": r.brewer or "Unknown",
        "created": r.date,
        "batch_size": _measure(r.batch_size_l, "l"),
        "efficiency": {"brewhouse": _measure(r.efficiency_pct or 0, "%")},
        "style": style,
        "ingredients": ingredients,
        "mash": mash,
        "notes": r.notes,
        "original_gravity": _measure(r.est_og, "sg"),
        "final_gravity": _measure(r.est_fg, "sg"),
        "alcohol_by_volume": _measure(r.est_abv, "%") if r.est_abv is not None else None,
        "ibu_estimate": _measure(r.ibu, "IBUs") if r.ibu is not None else None,
        "color_estimate": _measure(r.est_color_srm, "SRM") if r.est_color_srm is not None else None,
        "boil": {"name": "Boil", "duration": _measure(r.boil_time_min, "min")} if r.boil_time_min is not None else None,
    })


def write(recipes: list[Recipe], path: str | Path, profile: str | None = None) -> None:
    payload = {"version": "1.0", "recipes": [_recipe(r) for r in recipes]}
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
