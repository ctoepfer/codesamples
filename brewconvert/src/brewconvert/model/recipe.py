from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any

from .units import Quantity


class _MassAddition:
    def __post_init__(self, amount_kg):
        if self.quantity is None and amount_kg is not None:
            self.quantity = Quantity(amount_kg, "kg", source_field="amount_kg")

    def _amount_kg(self):
        q = self.quantity
        return (
            float(q.si_value)
            if q
            and q.kind == "mass"
            and q.si_value is not None
            and q.status != "ambiguous"
            else None
        )


@dataclass
class FermentableAddition(_MassAddition):
    name: str
    amount_kg: InitVar[float | None] = None
    type: str | None = None
    yield_pct: float | None = None
    color_srm: float | None = None
    source: dict[str, Any] = field(default_factory=dict)
    quantity: Quantity | None = None
    use: str | None = None


@dataclass
class HopAddition(_MassAddition):
    name: str
    amount_kg: InitVar[float | None] = None
    alpha: float | None = None
    use: str | None = None
    time_min: float | None = None
    form: str | None = None
    temperature_c: float | None = None
    source: dict[str, Any] = field(default_factory=dict)
    quantity: Quantity | None = None


class _TypedAddition:
    def __post_init__(self, *legacy):
        # Both old constructors retain their original positional argument order.
        amount, weight, display = (
            legacy
            if isinstance(self, YeastAddition)
            else (legacy[0], legacy[2], legacy[1])
        )
        if self.quantity is None and amount is not None:
            self.quantity = Quantity(
                amount,
                "kg" if weight is True else "L" if weight is False else None,
                source_field="legacy amount",
                original_display=display,
            )
        elif self.quantity is None and display:
            self.quantity = Quantity.parse(
                display, status="ambiguous", source_field="display only"
            )

    def _amount(self):
        q = self.quantity
        return (
            float(q.si_value)
            if q and q.si_value is not None and q.status != "ambiguous"
            else None
        )

    def _weight(self):
        return (
            {"mass": True, "volume": False}.get(self.quantity.kind)
            if self.quantity
            else None
        )

    def _display(self):
        return self.quantity.display() if self.quantity else None


@dataclass
class YeastAddition(_TypedAddition):
    name: str
    laboratory: str | None = None
    product_id: str | None = None
    type: str | None = None
    form: str | None = None
    amount: InitVar[float | None] = None
    amount_is_weight: InitVar[bool | None] = None
    display_amount: InitVar[str | None] = None
    attenuation: float | None = None
    source: dict[str, Any] = field(default_factory=dict)
    quantity: Quantity | None = None
    use: str | None = None


@dataclass
class MiscAddition(_TypedAddition):
    name: str
    amount: InitVar[float | None] = None
    display_amount: InitVar[str | None] = None
    amount_is_weight: InitVar[bool | None] = None
    time_min: float | None = None
    type: str | None = None
    use: str | None = None
    source: dict[str, Any] = field(default_factory=dict)
    quantity: Quantity | None = None


@dataclass
class MashStep:
    name: str
    type: str | None = None
    step_time_min: float | None = None
    step_temp_c: float | None = None
    ramp_time_min: float | None = None
    end_temp_c: float | None = None
    source: dict[str, Any] = field(default_factory=dict)


@dataclass
class Style:
    name: str | None = None
    category_number: str | None = None
    style_letter: str | None = None
    style_guide: str | None = None
    type: str | None = None
    source: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recipe:
    name: str
    type: str | None = None
    brewer: str | None = None
    date: str | None = None
    batch_size_l: float | None = None
    boil_size_l: float | None = None
    boil_time_min: float | None = None
    efficiency_pct: float | None = None
    est_og: float | None = None
    est_fg: float | None = None
    ibu: float | None = None
    est_abv: float | None = None
    est_color_srm: float | None = None
    notes: str | None = None
    ibu_method: str | None = None
    style: Style | None = None
    fermentables: list[FermentableAddition] = field(default_factory=list)
    hops: list[HopAddition] = field(default_factory=list)
    yeasts: list[YeastAddition] = field(default_factory=list)
    miscs: list[MiscAddition] = field(default_factory=list)
    mash_steps: list[MashStep] = field(default_factory=list)
    measured_values: dict[str, Any] = field(default_factory=dict)
    calculated_values: dict[str, Any] = field(default_factory=dict)
    source_format: str | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)
    unknown_fields: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        parts = [self.name]
        if self.brewer:
            parts.append(f"by {self.brewer}")
        if self.batch_size_l is not None:
            parts.append(f"{self.batch_size_l:.3g} L")
        if self.est_og is not None:
            parts.append(f"OG {self.est_og:.3f}")
        if self.ibu is not None:
            parts.append(f"IBU {self.ibu:.1f}")
        return " | ".join(parts)


# Read-only legacy views: mutation must replace quantity, preventing stale unit/value pairs.
for _addition in (MiscAddition, YeastAddition):
    _addition.amount = property(_TypedAddition._amount)
    _addition.amount_is_weight = property(_TypedAddition._weight)
    _addition.display_amount = property(_TypedAddition._display)

for _addition in (FermentableAddition, HopAddition):
    _addition.amount_kg = property(_MassAddition._amount_kg)
