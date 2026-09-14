"""Exact brewing unit factors. SI interchange bases are kg and L; count has no SI value."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Any

# International avoirdupois and US liquid measures (not imperial gallons).
UNITS = {
    "kg": ("mass", Decimal(1)),
    "g": ("mass", Decimal("0.001")),
    "lb": ("mass", Decimal("0.45359237")),
    "oz": ("mass", Decimal("0.028349523125")),
    "L": ("volume", Decimal(1)),
    "mL": ("volume", Decimal("0.001")),
    "US gal": ("volume", Decimal("3.785411784")),
    "qt": ("volume", Decimal("0.946352946")),
    "US fl oz": ("volume", Decimal("0.0295735295625")),
    **{u: ("count", Decimal(1)) for u in ("package", "sachet", "tablet", "count")},
}
ALIASES = {
    "l": "L",
    "ml": "mL",
    "gal": "US gal",
    "us gal": "US gal",
    "fl oz": "US fl oz",
    "floz": "US fl oz",
    "us fl oz": "US fl oz",
    "lbs": "lb",
    "grams": "g",
    "gram": "g",
    "pounds": "lb",
    "pound": "lb",
    "ounces": "oz",
    "ounce": "oz",
    "gallons": "US gal",
    "gallon": "US gal",
    "quart": "qt",
    "quarts": "qt",
    "liter": "L",
    "liters": "L",
    "milliliter": "mL",
    "milliliters": "mL",
    "fluid ounce": "US fl oz",
    "fluid ounces": "US fl oz",
    "pkg": "package",
    "pkgs": "package",
    "packages": "package",
    "sachets": "sachet",
    "tablets": "tablet",
    "item": "count",
    "each": "count",
    "items": "count",
    "item/count": "count",
    "unit": "count",
}


def decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("NaN")


def unit_name(unit: str | None) -> str | None:
    if not isinstance(unit, str) or not unit.strip():
        return None
    clean = unit.strip()
    lower = clean.lower()
    return ALIASES.get(lower, lower if lower in UNITS else clean)


@dataclass(frozen=True)
class Quantity:
    value: Decimal | str | float
    unit: str | None
    status: str = "explicit"
    source_field: str | None = None
    original_display: str | None = None
    evidence: Any = None

    def __post_init__(self):
        object.__setattr__(self, "value", decimal(self.value))
        if self.status not in {"explicit", "inferred", "ambiguous"}:
            raise ValueError("Quantity status must be explicit, inferred or ambiguous")
        if unit_name(self.unit) not in UNITS or self.unit == "unit":
            object.__setattr__(self, "status", "ambiguous")

    @property
    def kind(self) -> str:
        return UNITS.get(unit_name(self.unit), ("unknown", None))[0]

    @property
    def valid(self) -> bool:
        return self.value.is_finite() and self.value >= 0

    @property
    def si_value(self) -> Decimal | None:
        if self.kind not in {"mass", "volume"} or not self.valid:
            return None
        return self.value * UNITS[unit_name(self.unit)][1]

    @property
    def si_unit(self) -> str | None:
        return {"mass": "kg", "volume": "L"}.get(self.kind)

    def to(self, unit: str) -> Decimal:
        target = UNITS.get(unit_name(unit))
        if not target or target[0] != self.kind or not self.valid:
            raise ValueError(f"Cannot convert {self} to {unit}")
        if self.kind == "count" and unit_name(unit) != unit_name(self.unit):
            raise ValueError(
                "Package, sachet, tablet and item counts are not interchangeable"
            )
        return self.value * UNITS[unit_name(self.unit)][1] / target[1]

    def scaled(self, factor: Any) -> Quantity:
        return replace(self, value=self.value * decimal(factor), original_display=None)

    def display(self, unit: str | None = None) -> str:
        return f"{self.to(unit) if unit else self.value:f} {unit or self.unit or '?'}"

    def measure(self) -> dict | None:
        if not self.valid or self.status == "ambiguous":
            return None
        return {"value": self.value, "unit": self.unit}

    @classmethod
    def from_measure(
        cls, raw: Any, unit: str | None = None, **kwargs
    ) -> Quantity | None:
        if raw is None:
            return None
        if isinstance(raw, dict):
            unit = raw.get("unit", unit)
            value = raw.get("value")
        else:
            value = raw
        return cls(value, unit, evidence=raw, **kwargs)

    @classmethod
    def parse(cls, text: str | None, **kwargs) -> Quantity | None:
        if not text:
            return None
        match = re.fullmatch(r"\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+(.+?)\s*", text)
        return (
            cls(match[1], match[2], original_display=text, **kwargs) if match else None
        )


def first_present(*values):
    """Coalesce absent values without discarding a meaningful numeric zero."""
    return next((v for v in values if v is not None), None)


def convert(value, source, target):
    return None if value is None else float(Quantity(value, source).to(target))


KG_TO_OZ = float(1 / UNITS["oz"][1])
OZ_TO_KG = float(UNITS["oz"][1])
L_TO_FLOZ = float(1 / UNITS["US fl oz"][1])
FLOZ_TO_L = float(UNITS["US fl oz"][1])


def kg_to_oz(value):
    return convert(value, "kg", "oz")


def oz_to_kg(value):
    return convert(value, "oz", "kg")


def l_to_floz(value):
    return convert(value, "L", "US fl oz")


def floz_to_l(value):
    return convert(value, "US fl oz", "L")


def c_to_f(value):
    return None if value is None else value * 9 / 5 + 32


def f_to_c(value):
    return None if value is None else (value - 32) * 5 / 9
