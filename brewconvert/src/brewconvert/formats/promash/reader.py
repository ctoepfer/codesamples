from __future__ import annotations

import re
from pathlib import Path

from brewconvert.formats.boundary import reader
from brewconvert.model import (
    FermentableAddition,
    HopAddition,
    MashStep,
    MiscAddition,
    Recipe,
    YeastAddition,
)
from brewconvert.model.units import Quantity

_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _first_num(text: str | None) -> float | None:
    if not text:
        return None
    m = _NUM.search(text.replace(",", "."))
    return float(m.group(0)) if m else None


def _gal_to_l(v):
    return None if v is None else float(Quantity(v, "US gal").to("L"))


def _f_to_c(v: float | None) -> float | None:
    return None if v is None else (v - 32) * 5 / 9


def _split_label(line: str) -> tuple[str, str] | None:
    if ":" in line:
        a, b = line.split(":", 1)
        return a.strip().lower(), b.strip()
    return None


@reader("promash-text")
def read(path: str | Path) -> list[Recipe]:
    text = Path(path).read_text(encoding="utf-8")
    return [_read_text(chunk) for chunk in text.split("\f") if chunk.strip()]


def _read_text(text):
    lines = [l.rstrip() for l in text.splitlines()]
    recipe = Recipe(
        name="Untitled",
        source_format="promash-text",
        source_metadata={"parser": "line-oriented"},
    )
    current = "header"

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low == "notes":
            current = "notes"
            recipe.notes = ""
            continue
        if current == "notes":
            if set(line) <= {"-", "="}:
                continue
            recipe.notes += ("\n" if recipe.notes else "") + raw
            continue
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
        if low.startswith(("extras", "misc")):
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
                recipe.batch_size_l = (
                    _gal_to_l(_first_num(val))
                    if "gal" in val.lower()
                    else _first_num(val)
                )
            elif "boil" in key and "size" in key:
                recipe.boil_size_l = (
                    _gal_to_l(_first_num(val))
                    if "gal" in val.lower()
                    else _first_num(val)
                )
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
            q = Quantity.parse(parts[0], source_field="line amount")
            amount = float(q.si_value) if q and q.si_value is not None else None
            name = parts[1] if amount is not None else parts[0]
            recipe.fermentables.append(
                FermentableAddition(
                    name=name.strip(), quantity=q, type="Grain", source={"line": line}
                )
            )
        elif current == "hops" and len(parts) >= 2:
            q = Quantity.parse(parts[0], source_field="line amount")
            amount = float(q.si_value) if q and q.si_value is not None else None
            name = parts[1] if amount is not None else parts[0]
            alpha = next((_first_num(p) for p in parts if "%" in p), None)
            time = next((_first_num(p) for p in parts if "min" in p.lower()), None)
            recipe.hops.append(
                HopAddition(
                    name=name.strip(),
                    quantity=q,
                    alpha=alpha,
                    time_min=time,
                    use=next(
                        (
                            p
                            for p in parts[2:]
                            if p.lower()
                            in {
                                "boil",
                                "dry hop",
                                "mash",
                                "hop stand",
                                "sparge",
                                "secondary",
                                "packaging",
                            }
                        ),
                        "Boil",
                    ),
                    source={"line": line},
                )
            )
        elif current == "yeast":
            q = Quantity.parse(parts[0], source_field="line amount")
            recipe.yeasts.append(
                YeastAddition(
                    name=parts[1] if q and len(parts) > 1 else line.strip(),
                    quantity=q,
                    source={"line": line},
                )
            )
        elif current == "miscs" and len(line) > 2:
            q = Quantity.parse(parts[0], source_field="line amount")
            recipe.miscs.append(
                MiscAddition(
                    name=parts[1] if len(parts) > 1 else parts[0],
                    quantity=q,
                    use=parts[3] if len(parts) > 3 else None,
                    type=parts[2] if len(parts) > 2 else None,
                    time_min=_first_num(parts[4]) if len(parts) > 4 else None,
                    source={"line": line},
                )
            )
        elif current == "mash":
            temp = _f_to_c(_first_num(line)) if " f" in low else _first_num(line)
            time = next((_first_num(p) for p in parts if "min" in p.lower()), None)
            recipe.mash_steps.append(
                MashStep(
                    name=parts[0].strip(),
                    step_temp_c=temp,
                    step_time_min=time,
                    source={"line": line},
                )
            )

    recipe.source_metadata["document"] = text
    return recipe
