from __future__ import annotations

import re
from pathlib import Path

from brewconvert.model import Recipe, FermentableAddition, HopAddition, YeastAddition, MiscAddition, MashStep

_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _first_num(text: str | None) -> float | None:
    if not text:
        return None
    m = _NUM.search(text.replace(",", "."))
    return float(m.group(0)) if m else None


def _lb_to_kg(v: float | None) -> float | None:
    return None if v is None else v * 0.45359237


def _oz_to_kg(v: float | None) -> float | None:
    return None if v is None else v * 0.028349523125


def _gal_to_l(v: float | None) -> float | None:
    return None if v is None else v * 3.785411784


def _f_to_c(v: float | None) -> float | None:
    return None if v is None else (v - 32) * 5 / 9


def _split_label(line: str) -> tuple[str, str] | None:
    if ":" in line:
        a, b = line.split(":", 1)
        return a.strip().lower(), b.strip()
    return None


def _parse_amount(line: str) -> float | None:
    n = _first_num(line)
    lower = line.lower()
    if n is None:
        return None
    if " oz" in lower or lower.startswith("oz"):
        return _oz_to_kg(n)
    if " g" in lower or lower.startswith("g"):
        return n / 1000
    if " kg" in lower:
        return n
    return _lb_to_kg(n)


def read(path: str | Path) -> list[Recipe]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    lines = [l.rstrip() for l in text.splitlines()]
    recipe = Recipe(name="Untitled", source_format="promash-text", source_metadata={"parser": "line-oriented"})
    current = "header"

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if "promash recipe report" in low:
            current = "header"
            continue
        if "recipe specifics" in low:
            current = "specifics"
            continue
        if "grain/extract/sugar" in low:
            current = "fermentables"
            continue
        if low == "hops" or low.startswith("hops"):
            current = "hops"
            continue
        if low.startswith("extras") or low.startswith("misc"):
            current = "miscs"
            continue
        if low.startswith("yeast"):
            current = "yeast"
            continue
        if "mash schedule" in low:
            current = "mash"
            continue
        if low.startswith("water"):
            current = "water"
            continue

        pair = _split_label(line)
        if pair:
            key, val = pair
            if "recipe" in key and "name" in key or key == "name":
                recipe.name = val or recipe.name
            elif "brewer" in key or "author" in key:
                recipe.brewer = val
            elif key == "date" or "date" in key:
                recipe.date = val
            elif "batch" in key and "size" in key:
                recipe.batch_size_l = _gal_to_l(_first_num(val)) if "gal" in val.lower() else _first_num(val)
            elif "boil" in key and "size" in key:
                recipe.boil_size_l = _gal_to_l(_first_num(val)) if "gal" in val.lower() else _first_num(val)
            elif "boil" in key and "time" in key:
                recipe.boil_time_min = _first_num(val)
            elif "efficiency" in key:
                recipe.efficiency_pct = _first_num(val)
            elif "og" in key or "original gravity" in key:
                recipe.est_og = _first_num(val)
            elif "fg" in key or "final gravity" in key:
                recipe.est_fg = _first_num(val)
            elif "ibu" in key:
                recipe.ibu = _first_num(val)
            elif "color" in key or "srm" in key:
                recipe.est_color_srm = _first_num(val)
            elif "abv" in key:
                recipe.est_abv = _first_num(val)
            elif "notes" in key:
                recipe.notes = val
            continue

        if line.startswith("-") or set(line) <= {"-", "="}:
            continue

        parts = re.split(r"\s{2,}|\t+", line)
        if current == "fermentables" and len(parts) >= 2:
            amount = _parse_amount(parts[0]) or _parse_amount(line)
            name = parts[1] if amount is not None else parts[0]
            recipe.fermentables.append(FermentableAddition(name=name.strip(), amount_kg=amount, type="Grain", source={"line": line}))
        elif current == "hops" and len(parts) >= 2:
            amount = _parse_amount(parts[0]) or _parse_amount(line)
            name = parts[1] if amount is not None else parts[0]
            alpha = next((_first_num(p) for p in parts if "%" in p), None)
            time = next((_first_num(p) for p in parts if "min" in p.lower()), None)
            recipe.hops.append(HopAddition(name=name.strip(), amount_kg=amount, alpha=alpha, time_min=time, use="Boil", source={"line": line}))
        elif current == "yeast":
            recipe.yeasts.append(YeastAddition(name=line.strip(), source={"line": line}))
        elif current == "miscs" and len(line) > 2:
            recipe.miscs.append(MiscAddition(name=parts[0].strip(), amount=_first_num(line), source={"line": line}))
        elif current == "mash":
            temp = _f_to_c(_first_num(line)) if " f" in low else _first_num(line)
            time = next((_first_num(p) for p in parts if "min" in p.lower()), None)
            recipe.mash_steps.append(MashStep(name=parts[0].strip(), step_temp_c=temp, step_time_min=time, source={"line": line}))

    return [recipe]
