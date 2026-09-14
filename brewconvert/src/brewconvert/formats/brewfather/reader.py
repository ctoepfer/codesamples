from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from brewconvert.formats.boundary import reader
from brewconvert.model import (
    FermentableAddition,
    HopAddition,
    MashStep,
    MiscAddition,
    Recipe,
    Style,
    YeastAddition,
)
from brewconvert.model.units import Quantity


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _get(obj: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in obj and obj[name] not in (None, ""):
            return obj[name]
    lower = {k.lower(): v for k, v in obj.items()}
    for name in names:
        if name.lower() in lower and lower[name.lower()] not in (None, ""):
            return lower[name.lower()]
    return None


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("value", "amount", "quantity", "total", "displayValue"):
            n = _num(value.get(key))
            if n is not None:
                return n
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("name", "display", "text", "value"):
            if value.get(key) not in (None, ""):
                return str(value[key])
        return None
    return str(value)


def _recipe_objects(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        if isinstance(data.get("recipes"), list):
            return [r for r in data["recipes"] if isinstance(r, dict)]
        if isinstance(data.get("recipe"), dict):
            return [data["recipe"]]
        if isinstance(data.get("data"), dict) and isinstance(
            data["data"].get("recipes"), list
        ):
            return [r for r in data["data"]["recipes"] if isinstance(r, dict)]
        return [data]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


@reader("brewfather-json")
def read(path: str | Path) -> list[Recipe]:
    data = json.loads(Path(path).read_text(encoding="utf-8"), parse_float=Decimal)
    recipes: list[Recipe] = []
    for raw in _recipe_objects(data):
        recipe = Recipe(
            name=_str(_get(raw, "name", "Name")) or "Untitled",
            type=_str(_get(raw, "type")),
            brewer=_str(_get(raw, "author", "brewer")),
            date=_str(_get(raw, "created", "createdAt", "brewDate", "date")),
            batch_size_l=_num(
                _get(raw, "batchSize", "batch_size", "volume", "fermenterVolume")
            ),
            boil_size_l=_num(
                _get(raw, "boilSize", "boil_size", "preBoilSize", "kettleSize")
            ),
            boil_time_min=_num(_get(raw, "boilTime", "boil_time")),
            efficiency_pct=_num(_get(raw, "efficiency", "brewhouseEfficiency")),
            est_og=_num(_get(raw, "og", "estOg", "originalGravity", "estimatedOg")),
            est_fg=_num(_get(raw, "fg", "estFg", "finalGravity", "estimatedFg")),
            ibu=_num(_get(raw, "ibu", "ibus", "ibuEstimate")),
            est_abv=_num(_get(raw, "abv", "estAbv")),
            est_color_srm=_num(_get(raw, "color", "srm", "estColor")),
            notes=_str(_get(raw, "notes", "description")),
            ibu_method=_str(_get(raw, "ibuMethod")),
            source_format="brewfather-json",
            source_metadata={"_id": _get(raw, "_id", "id")},
        )
        style = _get(raw, "style")
        if isinstance(style, dict):
            recipe.style = Style(
                name=_str(_get(style, "name")),
                category_number=_str(_get(style, "categoryNumber", "category_number")),
                style_letter=_str(_get(style, "styleLetter", "style_letter")),
                style_guide=_str(_get(style, "styleGuide", "style_guide")),
                type=_str(_get(style, "type")),
                source=style,
            )
        elif style:
            recipe.style = Style(name=_str(style))

        for f in _as_list(_get(raw, "fermentables", "grains")):
            if isinstance(f, dict):
                recipe.fermentables.append(
                    FermentableAddition(
                        name=_str(_get(f, "name")) or "Unnamed fermentable",
                        quantity=Quantity.from_measure(
                            _get(f, "amount", "weight"),
                            _get(f, "unit"),
                            source_field="amount/unit",
                        ),
                        use=_str(_get(f, "use")),
                        type=_str(_get(f, "type")),
                        yield_pct=_num(_get(f, "yield", "yieldPercent", "potential")),
                        color_srm=_num(_get(f, "color", "srm")),
                        source=f,
                    )
                )

        for h in _as_list(_get(raw, "hops")):
            if isinstance(h, dict):
                recipe.hops.append(
                    HopAddition(
                        name=_str(_get(h, "name")) or "Unnamed hop",
                        quantity=Quantity.from_measure(
                            _get(h, "amount", "weight"),
                            _get(h, "unit"),
                            source_field="amount/unit",
                        ),
                        alpha=_num(_get(h, "alpha", "alphaAcid")),
                        use=_str(_get(h, "use")),
                        time_min=_num(_get(h, "time", "duration")),
                        form=_str(_get(h, "form")),
                        temperature_c=_num(_get(h, "temperature", "hopStandTemp")),
                        source=h,
                    )
                )

        for y in _as_list(_get(raw, "yeasts", "yeast")):
            if isinstance(y, dict):
                recipe.yeasts.append(
                    YeastAddition(
                        name=_str(_get(y, "name")) or "Unnamed yeast",
                        laboratory=_str(
                            _get(y, "laboratory", "manufacturer", "producer")
                        ),
                        product_id=_str(_get(y, "productId", "product_id")),
                        type=_str(_get(y, "type")),
                        form=_str(_get(y, "form")),
                        quantity=Quantity.from_measure(
                            _get(y, "amount"),
                            _get(y, "unit"),
                            source_field="amount/unit",
                        ),
                        use=_str(_get(y, "use")),
                        attenuation=_num(_get(y, "attenuation")),
                        source=y,
                    )
                )

        for m in _as_list(_get(raw, "miscs", "misc", "miscellaneous")):
            if isinstance(m, dict):
                recipe.miscs.append(
                    MiscAddition(
                        name=_str(_get(m, "name")) or "Unnamed misc",
                        quantity=Quantity.from_measure(
                            _get(m, "amount"),
                            _get(m, "unit"),
                            source_field="amount/unit",
                        ),
                        display_amount=_str(_get(m, "displayAmount")),
                        amount_is_weight=bool(_get(m, "amountIsWeight"))
                        if _get(m, "amountIsWeight") is not None
                        else None,
                        time_min=_num(_get(m, "time", "duration")),
                        type=_str(_get(m, "type")),
                        use=_str(_get(m, "use")),
                        source=m,
                    )
                )

        mash = _get(raw, "mash")
        steps = _get(mash, "steps", "mashSteps") if isinstance(mash, dict) else None
        for s in _as_list(steps):
            if isinstance(s, dict):
                recipe.mash_steps.append(
                    MashStep(
                        name=_str(_get(s, "name")) or "Mash Step",
                        type=_str(_get(s, "type")),
                        step_time_min=_num(_get(s, "stepTime", "time", "duration")),
                        step_temp_c=_num(_get(s, "stepTemp", "temperature", "temp")),
                        ramp_time_min=_num(_get(s, "rampTime")),
                        end_temp_c=_num(_get(s, "endTemp")),
                        source=s,
                    )
                )
        recipe.measured_values = {
            k: v
            for k, v in raw.items()
            if k.lower().startswith("measured") or k.lower().startswith("actual")
        }
        recipe.calculated_values = {
            k: raw[k] for k in ("og", "fg", "ibu", "abv", "color") if k in raw
        }
        known = {
            "name",
            "type",
            "author",
            "brewer",
            "created",
            "createdAt",
            "brewDate",
            "date",
            "batchSize",
            "batch_size",
            "volume",
            "fermenterVolume",
            "boilSize",
            "boil_size",
            "preBoilSize",
            "kettleSize",
            "boilTime",
            "boil_time",
            "efficiency",
            "brewhouseEfficiency",
            "og",
            "estOg",
            "originalGravity",
            "estimatedOg",
            "fg",
            "estFg",
            "finalGravity",
            "estimatedFg",
            "ibu",
            "ibus",
            "ibuEstimate",
            "abv",
            "estAbv",
            "color",
            "srm",
            "estColor",
            "notes",
            "description",
            "ibuMethod",
            "style",
            "fermentables",
            "grains",
            "hops",
            "yeasts",
            "yeast",
            "miscs",
            "misc",
            "miscellaneous",
            "mash",
        }
        recipe.unknown_fields = {
            k: v
            for k, v in raw.items()
            if k.lower() not in {name.lower() for name in known}
        }
        recipe.source_metadata["document"] = raw
        recipes.append(recipe)
    return recipes
