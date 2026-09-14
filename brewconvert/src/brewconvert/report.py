"""Semantic diagnostics shared by the public API and individual adapters."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from .model.units import Quantity


class ValidationError(ValueError):
    pass


@dataclass
class ConversionReport:
    source_format: str = "model"
    target_format: str = "validation"
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add(
        self,
        code,
        recipe,
        ingredient,
        source,
        interpreted,
        target,
        reason,
        unsafe=False,
    ):
        message = (
            f"[{code}] recipe={recipe!r} ingredient={ingredient!r}; source={source!r}; "
            f"interpreted={interpreted!r}; target={target!r}; {reason}"
        )
        if message not in self.warnings:
            self.warnings.append(message)
        if unsafe and message not in self.errors:
            self.errors.append(message)

    def check(self):
        if self.errors:
            raise ValidationError(self.text())

    def text(self) -> str:
        return "\n".join(
            [f"{self.source_format} -> {self.target_format}"]
            + [f"NOTE: {n}" for n in self.notes]
            + [f"WARNING: {w}" for w in self.warnings]
        )


def quantity_of(item):
    if hasattr(item, "quantity"):
        return item.quantity
    return (
        Quantity(item.amount_kg, "kg", source_field="amount_kg")
        if item.amount_kg is not None
        else None
    )


def additions(recipe):
    return recipe.fermentables + recipe.hops + recipe.miscs + recipe.yeasts


def validate_recipes(recipes, report=None):
    report = report if report is not None else ConversionReport()
    for r in recipes:
        for item in additions(r):
            q = quantity_of(item)

            def warn(code, reason, unsafe=False, source=None, r=r, item=item, q=q):
                report.add(
                    code,
                    r.name,
                    item.name,
                    source
                    if source is not None
                    else (q.evidence if q and q.evidence is not None else str(q)),
                    q.display() if q else None,
                    report.target_format,
                    reason,
                    unsafe,
                )

            if q is None:
                warn(
                    "missing-quantity",
                    "Quantity or unit is unavailable; no zero is assumed.",
                    True,
                )
                continue
            if not q.valid:
                warn(
                    "invalid-quantity",
                    "Quantity is invalid, non-finite or negative.",
                    True,
                )
                continue
            if (item in r.fermentables or item in r.hops) and q.kind != "mass":
                warn(
                    "ingredient-dimension",
                    "Fermentables and hops require mass quantities in supported interchange mappings.",
                    True,
                )
            if q.status == "ambiguous" or q.kind == "unknown":
                warn(
                    "ambiguous-unit",
                    "Missing, unsupported or ambiguous unit; explicit interpretation is required.",
                    True,
                )
            if q.status == "inferred":
                warn(
                    "inferred-unit",
                    "Unit interpretation is inferred from the source format convention.",
                )
            if q.original_display:
                display = Quantity.parse(q.original_display)
                if display is None or display.kind == "unknown":
                    warn(
                        "ambiguous-display",
                        "DISPLAY_AMOUNT has an unrecognized unit or quantity.",
                        True,
                        q.original_display,
                    )
                elif not display.valid:
                    warn(
                        "invalid-display",
                        "DISPLAY_AMOUNT is negative or non-finite.",
                        True,
                        q.original_display,
                    )
                elif display.kind != q.kind:
                    warn(
                        "dimension-contradiction",
                        "DISPLAY_AMOUNT contradicts AMOUNT_IS_WEIGHT; canonical quantity retained.",
                        True,
                        q.original_display,
                    )
                elif display.valid and q.si_value is not None:
                    delta = abs(display.si_value - q.si_value)
                    if delta > max(
                        Decimal("0.000001"), abs(q.si_value) * Decimal("0.01")
                    ):
                        warn(
                            "amount-contradiction",
                            "DISPLAY_AMOUNT disagrees with canonical AMOUNT by more than max(1e-6 SI, 1%); both retained as evidence.",
                            True,
                            q.original_display,
                        )
                        if (
                            min(display.si_value, q.si_value) > 0
                            and max(display.si_value, q.si_value)
                            / min(display.si_value, q.si_value)
                            >= 10
                        ):
                            warn(
                                "magnitude-change",
                                "Source display and canonical quantity differ by at least a factor of ten.",
                                True,
                                q.original_display,
                            )
            if item in r.yeasts:
                form = (item.form or "").lower()
                if q.value == 0 and (form in {"dry", "liquid"}):
                    warn(
                        "zero-culture",
                        f"{form} yeast has zero quantity; verify the source/conversion.",
                        True,
                    )
                if (form == "dry" and q.kind == "volume") or (
                    form == "liquid" and q.kind == "mass"
                ):
                    warn(
                        "culture-dimension",
                        "Yeast form and quantity dimension disagree.",
                        True,
                    )
            if item in r.yeasts and q.kind == "volume" and q.si_value is not None:
                limit = Decimal(
                    str(r.batch_size_l if r.batch_size_l is not None else 20)
                ) * Decimal("0.1")
                if q.si_value > limit:
                    warn(
                        "suspicious-quantity",
                        f"Liquid culture exceeds advisory threshold {limit} L (10% of batch).",
                    )
            if q.kind == "mass" and q.si_value is not None:
                name = (item.name + " " + (getattr(item, "type", None) or "")).lower()
                limit = None
                if any(k in name for k in ("fruit", "raspberr", "cherr", "peach")):
                    limit = Decimal(
                        str(r.batch_size_l if r.batch_size_l is not None else 20)
                    )  # 1 kg per L
                elif (
                    any(
                        k in name
                        for k in (
                            "salt",
                            "sodium",
                            "calcium",
                            "sulph",
                            "spice",
                            "coriander",
                            "fining",
                            "whirlfloc",
                        )
                    )
                    or item in r.yeasts
                ):
                    limit = Decimal(
                        str(r.batch_size_l if r.batch_size_l is not None else 20)
                    ) * Decimal("0.01")
                if limit is not None and q.si_value > limit:
                    warn(
                        "suspicious-quantity",
                        f"Quantity exceeds advisory threshold {limit} kg; check units and batch size.",
                    )
        if r.source_format == "beersmith-bsmx":
            for item in r.hops + r.miscs:
                phase = item.use
                if item in r.hops and not item.source.get("BC_PHASE"):
                    report.add(
                        "inferred-phase",
                        r.name,
                        item.name,
                        item.source.get("F_H_USE"),
                        phase,
                        report.target_format,
                        "Native BSMX hop phase mapping is provisional; inspect the retained source timing fields.",
                    )
                if phase == "Unknown" or (
                    phase and (phase.startswith("BSMX use") or phase.isdigit())
                ):
                    report.add(
                        "ambiguous-phase",
                        r.name,
                        item.name,
                        phase,
                        phase,
                        report.target_format,
                        "Unrecognized native process phase; no boil fallback is invented.",
                        True,
                    )
        for h in r.hops:
            if (
                (h.use or "").lower() == "boil"
                and h.time_min is not None
                and r.boil_time_min is not None
                and h.time_min > r.boil_time_min
            ):
                report.add(
                    "hop-time",
                    r.name,
                    h.name,
                    h.time_min,
                    h.time_min,
                    r.boil_time_min,
                    "Hop time exceeds declared boil time.",
                )
    return report


def compare_recipes(before, after, report):
    """Compare actual serialized/reparsed semantics, matching duplicate names by occurrence."""
    if len(before) != len(after):
        report.add(
            "recipe-loss",
            "<collection>",
            None,
            len(before),
            len(before),
            len(after),
            "Recipe count changed.",
            True,
        )
    for r, out in zip(before, after):
        for field_name in (
            "name",
            "type",
            "brewer",
            "date",
            "batch_size_l",
            "boil_size_l",
            "boil_time_min",
            "efficiency_pct",
            "est_og",
            "est_fg",
            "ibu",
            "est_abv",
            "est_color_srm",
            "notes",
            "ibu_method",
        ):
            value, target = getattr(r, field_name), getattr(out, field_name)
            equal = value == target
            if isinstance(value, (int, float)) and isinstance(target, (int, float)):
                equal = abs(value - target) <= max(1e-6, abs(value) * 1e-5)
            if value is not None and not equal:
                report.add(
                    "field-loss",
                    r.name,
                    field_name,
                    value,
                    value,
                    target,
                    "Normalized recipe field is unavailable or changed in target.",
                )
        if r.style:
            for field_name in (
                "name",
                "category_number",
                "style_letter",
                "style_guide",
                "type",
            ):
                value, target = (
                    getattr(r.style, field_name),
                    getattr(out.style, field_name, None),
                )
                if value is not None and value != target:
                    report.add(
                        "style-loss",
                        r.name,
                        field_name,
                        value,
                        value,
                        target,
                        "Style field changed or was omitted.",
                    )
        if r.mash_steps != out.mash_steps:
            left = [
                (
                    s.name,
                    s.type,
                    s.step_time_min,
                    s.step_temp_c,
                    s.ramp_time_min,
                    s.end_temp_c,
                )
                for s in r.mash_steps
            ]
            right = [
                (
                    s.name,
                    s.type,
                    s.step_time_min,
                    s.step_temp_c,
                    s.ramp_time_min,
                    s.end_temp_c,
                )
                for s in out.mash_steps
            ]
            if left != right:
                report.add(
                    "mash-loss",
                    r.name,
                    "mash steps",
                    left,
                    left,
                    right,
                    "Mash schedule fields changed or were omitted.",
                )
        for group in ("fermentables", "hops", "miscs", "yeasts"):
            old, new = getattr(r, group), getattr(out, group)
            pools = {}
            for item in new:
                pools.setdefault(item.name, []).append(item)
            for item in old:
                matches = pools.get(item.name, [])
                dest = matches.pop(0) if matches else None
                q, dq = quantity_of(item), quantity_of(dest) if dest else None
                if dest is None:
                    report.add(
                        "ingredient-loss",
                        r.name,
                        item.name,
                        item.name,
                        item.name,
                        None,
                        "Ingredient addition missing from target.",
                        True,
                    )
                if q and q.valid and q.status != "ambiguous":
                    reason = None
                    code = "quantity-loss"
                    if dq is None or not dq.valid or dq.status == "ambiguous":
                        reason = "Target cannot preserve a usable typed quantity."
                    elif q.kind != dq.kind:
                        reason = "Target changes physical dimension (including count versus mass/volume)."
                    elif q.kind == "count" and (
                        q.unit != dq.unit or q.value != dq.value
                    ):
                        reason = "Count unit or value changed."
                    elif q.si_value is not None and abs(q.si_value - dq.si_value) > max(
                        Decimal("1e-8"), abs(q.si_value) * Decimal("1e-7")
                    ):
                        reason = "Canonical quantity changed beyond max(1e-8 SI, 1e-7 relative)."
                        if (
                            dq.si_value == 0
                            or q.si_value == 0
                            or max(q.si_value, dq.si_value)
                            / min(q.si_value, dq.si_value)
                            >= 10
                        ):
                            code = "magnitude-change"
                    if reason:
                        report.add(
                            code,
                            r.name,
                            item.name,
                            q.display(),
                            q.display(),
                            dq.display() if dq else None,
                            reason,
                            True,
                        )
                if dest is not None:
                    for field_name in (
                        "type",
                        "yield_pct",
                        "color_srm",
                        "alpha",
                        "time_min",
                        "form",
                        "temperature_c",
                        "laboratory",
                        "product_id",
                        "attenuation",
                    ):
                        value, target = (
                            getattr(item, field_name, None),
                            getattr(dest, field_name, None),
                        )
                        equal = value == target
                        if isinstance(value, (int, float)) and isinstance(
                            target, (int, float)
                        ):
                            equal = abs(value - target) <= max(1e-6, abs(value) * 1e-5)
                        if value is not None and not equal:
                            report.add(
                                "ingredient-field-loss",
                                r.name,
                                item.name,
                                {field_name: value},
                                value,
                                target,
                                "Ingredient field changed or was omitted.",
                            )
                phase, target = getattr(item, "use", None), getattr(dest, "use", None)
                if phase and (phase or "").lower() != (target or "").lower():
                    report.add(
                        "phase-loss",
                        r.name,
                        item.name,
                        phase,
                        phase,
                        target,
                        "Process phase lost or remapped.",
                        True,
                    )
            names = (
                {
                    i.name
                    for i in old
                    if (getattr(i, "use", None) or "").lower() in {"mash", "sparge"}
                }
                if group == "miscs"
                else set()
            )
            for name in names:
                a = Counter((i.use or "").lower() for i in old if i.name == name)
                b = Counter((i.use or "").lower() for i in new if i.name == name)
                if (
                    a["mash"]
                    and a["sparge"]
                    and (b["mash"] < a["mash"] or b["sparge"] < a["sparge"])
                ):
                    report.add(
                        "salt-phase-merge",
                        r.name,
                        name,
                        dict(a),
                        dict(a),
                        dict(b),
                        "Separate mash/sparge additions were lost or merged.",
                        True,
                    )
