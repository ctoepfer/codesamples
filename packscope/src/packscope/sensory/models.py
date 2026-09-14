# SPDX-License-Identifier: Apache-2.0
"""Validated post-exposure self-reports; no inferred sensory measurements."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class BlindingType(StrEnum):
    """Recorded protocol conditions, not guarantees that blinding succeeded."""

    DOUBLE_BLIND = "DOUBLE_BLIND"
    SINGLE_BLIND = "SINGLE_BLIND"
    OPEN = "OPEN"


@dataclass(frozen=True, slots=True)
class SensoryRating:
    """One discrete post-exposure rating of an explicitly versioned variant.

    variant_id must identify an immutable stimulus version in the study manifest.
    timestamp is timezone-aware wall time, never joined to a gaze/EEG clock.
    Intensities use an explicitly declared common 0–10 scale (0 absent, 10 maximum).
    Missing hedonic scores remain None; rank is optional and one-based. Notes may
    contain personal data and require separate permission before collection.
    """

    rating_id: str
    session_id: str
    stimulus_id: str
    variant_id: str
    product_id: str
    timestamp: datetime
    hedonic_scale_9pt: int | None = None
    intensity_ratings: dict[str, float] = field(default_factory=dict)
    preference_rank: int | None = None
    free_text_notes: str | None = None
    quality_flags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("rating_id", "session_id", "stimulus_id", "variant_id", "product_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if not isinstance(self.timestamp, datetime) or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be a timezone-aware datetime.")
        if self.hedonic_scale_9pt is not None and (
            type(self.hedonic_scale_9pt) is not int or not 1 <= self.hedonic_scale_9pt <= 9
        ):
            raise ValueError("hedonic_scale_9pt must be an integer from 1 to 9, or None.")
        if self.preference_rank is not None and (type(self.preference_rank) is not int or self.preference_rank < 1):
            raise ValueError("preference_rank must be a positive integer, or None.")
        if not isinstance(self.intensity_ratings, dict):
            raise ValueError("intensity_ratings must be a dictionary.")
        for label, intensity in self.intensity_ratings.items():
            if not isinstance(label, str) or not label.strip():
                raise ValueError("Intensity labels must be non-empty strings.")
            if type(intensity) not in (float, int) or not math.isfinite(intensity) or not 0 <= intensity <= 10:
                raise ValueError("Intensity ratings must be finite numbers on the declared 0–10 scale.")
        if self.free_text_notes is not None and not isinstance(self.free_text_notes, str):
            raise ValueError("free_text_notes must be a string or None.")
        if not isinstance(self.quality_flags, list) or any(
            not isinstance(flag, str) or not flag.strip() for flag in self.quality_flags
        ):
            raise ValueError("quality_flags must be a list of non-empty strings.")
        object.__setattr__(self, "intensity_ratings", dict(self.intensity_ratings))
        object.__setattr__(self, "quality_flags", list(self.quality_flags))


@dataclass(frozen=True, slots=True)
class TastingProtocolMetadata:
    """Explicit protocol provenance; thresholds are not universal validity claims."""

    protocol_version: str
    blinding_type: BlindingType
    washout_seconds: float
    serving_temperature_c: float
    counterbalanced_order: bool

    def __post_init__(self) -> None:
        if not isinstance(self.protocol_version, str) or not self.protocol_version.strip():
            raise ValueError("protocol_version must be a non-empty string.")
        if not isinstance(self.blinding_type, BlindingType):
            raise ValueError("blinding_type must be an explicit BlindingType.")
        for name in ("washout_seconds", "serving_temperature_c"):
            value = getattr(self, name)
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite and numeric.")
        if self.washout_seconds < 0 or self.serving_temperature_c < -273.15:
            raise ValueError("Washout must be non-negative and temperature above absolute zero.")
        if type(self.counterbalanced_order) is not bool:
            raise ValueError("counterbalanced_order must be a boolean.")
