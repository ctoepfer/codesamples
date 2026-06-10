from __future__ import annotations

from pathlib import Path

from brewconvert.model import Recipe


def _fmt(value: object | None, suffix: str = "") -> str:
    if value is None:
        return ""
    return f"{value}{suffix}"


def write(recipes: list[Recipe], path: str | Path, profile: str | None = None) -> None:
    chunks: list[str] = []
    for r in recipes:
        lines = [
            "ProMash Recipe Report",
            "=====================",
            "",
            f"Recipe Name: {r.name}",
            f"Brewer: {r.brewer or ''}",
            f"Date: {r.date or ''}",
            "",
            "Recipe Specifics",
            "----------------",
            f"Batch Size: {_fmt(r.batch_size_l, ' L')}",
            f"Boil Size: {_fmt(r.boil_size_l, ' L')}",
            f"Boil Time: {_fmt(r.boil_time_min, ' min')}",
            f"Efficiency: {_fmt(r.efficiency_pct, ' %')}",
            f"OG: {_fmt(r.est_og)}",
            f"FG: {_fmt(r.est_fg)}",
            f"IBU: {_fmt(r.ibu)}",
            f"Color: {_fmt(r.est_color_srm, ' SRM')}",
            f"ABV: {_fmt(r.est_abv, ' %')}",
            "",
            "Grain/Extract/Sugar",
            "-------------------",
        ]
        for f in r.fermentables:
            lines.append(f"{_fmt(f.amount_kg, ' kg'):>12}  {f.name}  {f.type or ''}  {_fmt(f.color_srm, ' SRM')}")
        lines += ["", "Hops", "----"]
        for h in r.hops:
            lines.append(f"{_fmt(h.amount_kg, ' kg'):>12}  {h.name}  {_fmt(h.alpha, ' %')}  {h.use or ''}  {_fmt(h.time_min, ' min')}  {h.form or ''}")
        lines += ["", "Yeast", "-----"]
        for y in r.yeasts:
            lines.append(f"{y.name}  {y.laboratory or ''}  {y.product_id or ''}  {y.form or ''}")
        lines += ["", "Extras", "------"]
        for m in r.miscs:
            lines.append(f"{_fmt(m.amount):>12}  {m.name}  {m.type or ''}  {m.use or ''}  {_fmt(m.time_min, ' min')}")
        lines += ["", "Mash Schedule", "-------------"]
        for s in r.mash_steps:
            lines.append(f"{s.name}  {_fmt(s.step_temp_c, ' C')}  {_fmt(s.step_time_min, ' min')}  {s.type or ''}")
        lines += ["", "Notes", "-----", r.notes or ""]
        chunks.append("\n".join(lines))
    Path(path).write_text("\n\n\f\n\n".join(chunks) + "\n", encoding="utf-8")
