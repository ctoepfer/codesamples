from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brewconvert.model import Recipe


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            cv = _clean(v)
            if cv not in (None, {}, []):
                out[k] = cv
        return out
    if isinstance(value, list):
        return [_clean(v) for v in value if _clean(v) not in (None, {}, [])]
    return value


def _recipe(r: Recipe) -> dict[str, Any]:
    style = None
    if r.style:
        style = _clean({
            "name": r.style.name,
            "categoryNumber": r.style.category_number,
            "styleLetter": r.style.style_letter,
            "styleGuide": r.style.style_guide,
            "type": r.style.type,
        })
    return _clean({
        "name": r.name,
        "author": r.brewer,
        "type": r.type or "All Grain",
        "created": r.date,
        "batchSize": r.batch_size_l,
        "boilSize": r.boil_size_l,
        "boilTime": r.boil_time_min,
        "efficiency": r.efficiency_pct,
        "og": r.est_og,
        "fg": r.est_fg,
        "ibu": r.ibu,
        "abv": r.est_abv,
        "color": r.est_color_srm,
        "notes": r.notes,
        "ibuMethod": r.ibu_method,
        "style": style,
        "fermentables": [_clean({
            "name": f.name,
            "amount": f.amount_kg,
            "unit": "kg",
            "type": f.type,
            "yield": f.yield_pct,
            "color": f.color_srm,
        }) for f in r.fermentables],
        "hops": [_clean({
            "name": h.name,
            "amount": h.amount_kg,
            "unit": "kg",
            "alpha": h.alpha,
            "use": h.use,
            "time": h.time_min,
            "form": h.form,
            "temperature": h.temperature_c,
        }) for h in r.hops],
        "yeasts": [_clean({
            "name": y.name,
            "laboratory": y.laboratory,
            "productId": y.product_id,
            "type": y.type,
            "form": y.form,
            "amount": y.amount,
            "attenuation": y.attenuation,
        }) for y in r.yeasts],
        "miscs": [_clean({
            "name": m.name,
            "amount": m.amount,
            "displayAmount": m.display_amount,
            "amountIsWeight": m.amount_is_weight,
            "time": m.time_min,
            "type": m.type,
            "use": m.use,
        }) for m in r.miscs],
        "mash": {"steps": [_clean({
            "name": s.name,
            "type": s.type,
            "stepTime": s.step_time_min,
            "stepTemp": s.step_temp_c,
            "rampTime": s.ramp_time_min,
            "endTemp": s.end_temp_c,
        }) for s in r.mash_steps]} if r.mash_steps else None,
    })


def write(recipes: list[Recipe], path: str | Path, profile: str | None = None) -> None:
    payload: Any
    if len(recipes) == 1 and profile != "export":
        payload = _recipe(recipes[0])
    else:
        payload = {"recipes": [_recipe(r) for r in recipes]}
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
