from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brewconvert.model import Recipe, Style, FermentableAddition, HopAddition, YeastAddition, MiscAddition, MashStep


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("value", "Value", "amount", "quantity"):
            if key in value:
                return _num(value[key])
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _unit(value: Any) -> str | None:
    if isinstance(value, dict):
        u = value.get("unit") or value.get("Unit")
        return str(u).lower() if u else None
    return None


def _measure(value: Any, kind: str | None = None) -> float | None:
    n = _num(value)
    if n is None:
        return None
    unit = _unit(value)
    if kind == "mass":
        if unit in {"g", "gram", "grams"}:
            return n / 1000
        if unit in {"lb", "lbs", "pound", "pounds"}:
            return n * 0.45359237
        if unit in {"oz", "ounce", "ounces"}:
            return n * 0.028349523125
    if kind == "volume":
        if unit in {"ml", "milliliter", "milliliters"}:
            return n / 1000
        if unit in {"gal", "gallon", "gallons", "us gal", "us gallon"}:
            return n * 3.785411784
        if unit in {"qt", "quart", "quarts"}:
            return n * 0.946352946
        if unit in {"fl oz", "floz", "fluid ounce", "fluid ounces"}:
            return n * 0.0295735295625
    if kind == "temp":
        if unit in {"f", "°f", "degf", "fahrenheit"}:
            return (n - 32) * 5 / 9
    if kind == "color":
        if unit in {"ebc"}:
            return n / 1.97
    return n


def _str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("name", "value", "text", "display"):
            if key in value and value[key] not in (None, ""):
                return str(value[key])
        return None
    return str(value)


def _timing(addition: dict[str, Any]) -> tuple[str | None, float | None, float | None]:
    timing = addition.get("timing") or {}
    use = _str(timing.get("use") or timing.get("type") or addition.get("use"))
    time_min = _measure(timing.get("time") or timing.get("duration") or addition.get("time"), None)
    temp_c = _measure(timing.get("temperature") or addition.get("temperature"), "temp")
    return use, time_min, temp_c


def _recipe_objects(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and "beerjson" in data and isinstance(data["beerjson"], dict):
        data = data["beerjson"]
    if isinstance(data, dict) and "recipes" in data:
        return [r for r in _as_list(data.get("recipes")) if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def read(path: str | Path) -> list[Recipe]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    root = data.get("beerjson", data) if isinstance(data, dict) else data
    recipes: list[Recipe] = []

    for raw in _recipe_objects(data):
        eff = raw.get("efficiency") or {}
        ingredients = raw.get("ingredients") or {}
        boil = raw.get("boil") or {}
        boil_time = None
        if isinstance(boil, dict):
            boil_time = _measure(boil.get("duration") or boil.get("boil_time"), None)
            steps = boil.get("boil_steps") or boil.get("steps") or []
            if boil_time is None and steps:
                boil_time = _measure(_as_list(steps)[0].get("duration"), None) if isinstance(_as_list(steps)[0], dict) else None

        recipe = Recipe(
            name=_str(raw.get("name")) or "Untitled",
            type=_str(raw.get("type")),
            brewer=_str(raw.get("author")),
            date=_str(raw.get("created")),
            batch_size_l=_measure(raw.get("batch_size"), "volume"),
            boil_size_l=_measure(raw.get("boil_size"), "volume"),
            boil_time_min=boil_time,
            efficiency_pct=_measure(eff.get("brewhouse") or eff.get("mash") or eff, None) if isinstance(eff, dict) else _measure(eff, None),
            est_og=_measure(raw.get("original_gravity"), None),
            est_fg=_measure(raw.get("final_gravity"), None),
            ibu=_measure(raw.get("ibu_estimate"), None),
            est_abv=_measure(raw.get("alcohol_by_volume"), None),
            est_color_srm=_measure(raw.get("color_estimate"), "color"),
            notes=_str(raw.get("notes")) or (_str(raw.get("taste", {}).get("notes")) if isinstance(raw.get("taste"), dict) else None),
            source_format="beerjson",
            source_metadata={"version": root.get("version") if isinstance(root, dict) else None},
        )

        style = raw.get("style")
        if isinstance(style, dict):
            recipe.style = Style(
                name=_str(style.get("name")),
                category_number=_str(style.get("category_number")),
                style_letter=_str(style.get("style_letter")),
                style_guide=_str(style.get("style_guide")),
                type=_str(style.get("type")),
                source=style,
            )
        elif style:
            recipe.style = Style(name=_str(style))

        for f in _as_list(ingredients.get("fermentable_additions")):
            if not isinstance(f, dict):
                continue
            recipe.fermentables.append(FermentableAddition(
                name=_str(f.get("name")) or "Unnamed fermentable",
                amount_kg=_measure(f.get("amount"), "mass"),
                type=_str(f.get("type")),
                yield_pct=_measure(f.get("yield"), None),
                color_srm=_measure(f.get("color"), "color"),
                source=f,
            ))

        for h in _as_list(ingredients.get("hop_additions")):
            if not isinstance(h, dict):
                continue
            use, time_min, temp_c = _timing(h)
            recipe.hops.append(HopAddition(
                name=_str(h.get("name")) or "Unnamed hop",
                amount_kg=_measure(h.get("amount"), "mass"),
                alpha=_measure(h.get("alpha_acid"), None),
                use=use,
                time_min=time_min,
                form=_str(h.get("form")),
                temperature_c=temp_c,
                source=h,
            ))

        for y in _as_list(ingredients.get("culture_additions")):
            if not isinstance(y, dict):
                continue
            recipe.yeasts.append(YeastAddition(
                name=_str(y.get("name")) or "Unnamed yeast",
                laboratory=_str(y.get("producer")),
                product_id=_str(y.get("product_id")),
                type=_str(y.get("type")),
                form=_str(y.get("form")),
                amount=_measure(y.get("amount"), None),
                attenuation=_measure(y.get("attenuation"), None),
                source=y,
            ))

        for m in _as_list(ingredients.get("miscellaneous_additions")):
            if not isinstance(m, dict):
                continue
            use, time_min, _ = _timing(m)
            recipe.miscs.append(MiscAddition(
                name=_str(m.get("name")) or "Unnamed misc",
                amount=_measure(m.get("amount"), None),
                time_min=time_min,
                type=_str(m.get("type")),
                use=use,
                source=m,
            ))

        mash = raw.get("mash") or {}
        for s in _as_list(mash.get("mash_steps") if isinstance(mash, dict) else None):
            if not isinstance(s, dict):
                continue
            recipe.mash_steps.append(MashStep(
                name=_str(s.get("name")) or "Mash Step",
                type=_str(s.get("type")),
                step_time_min=_measure(s.get("step_time") or s.get("duration"), None),
                step_temp_c=_measure(s.get("step_temperature") or s.get("step_temp"), "temp"),
                ramp_time_min=_measure(s.get("ramp_time"), None),
                end_temp_c=_measure(s.get("end_temperature") or s.get("end_temp"), "temp"),
                source=s,
            ))

        recipe.unknown_fields = {k: v for k, v in raw.items() if k not in {"name", "type", "author", "created", "batch_size", "boil_size", "boil", "efficiency", "original_gravity", "final_gravity", "ibu_estimate", "alcohol_by_volume", "color_estimate", "notes", "taste", "style", "ingredients", "mash"}}
        recipes.append(recipe)
    return recipes
