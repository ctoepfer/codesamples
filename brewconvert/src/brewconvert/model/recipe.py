from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FermentableAddition:
    name: str
    amount_kg: float | None = None
    type: str | None = None
    yield_pct: float | None = None
    color_srm: float | None = None
    source: dict[str, Any] = field(default_factory=dict)


@dataclass
class HopAddition:
    name: str
    amount_kg: float | None = None
    alpha: float | None = None
    use: str | None = None
    time_min: float | None = None
    form: str | None = None
    temperature_c: float | None = None
    source: dict[str, Any] = field(default_factory=dict)


@dataclass
class YeastAddition:
    name: str
    laboratory: str | None = None
    product_id: str | None = None
    type: str | None = None
    form: str | None = None
    amount: float | None = None
    amount_is_weight: bool | None = None
    display_amount: str | None = None
    attenuation: float | None = None
    source: dict[str, Any] = field(default_factory=dict)


@dataclass
class MiscAddition:
    name: str
    amount: float | None = None
    display_amount: str | None = None
    amount_is_weight: bool | None = None
    time_min: float | None = None
    type: str | None = None
    use: str | None = None
    source: dict[str, Any] = field(default_factory=dict)


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
    source_format: str | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)
    unknown_fields: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        parts = [self.name]
        if self.brewer:
            parts.append(f"by {self.brewer}")
        if self.batch_size_l:
            parts.append(f"{self.batch_size_l:.3g} L")
        if self.est_og:
            parts.append(f"OG {self.est_og:.3f}")
        if self.ibu:
            parts.append(f"IBU {self.ibu:.1f}")
        return " | ".join(parts)
