# SPDX-License-Identifier: Apache-2.0
"""Normalized packaging regions of interest for reproducible spatial attribution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NormalizedRect:
    """Axis-aligned rectangle in the same [0, 1] coordinate space as gaze samples."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width <= 0.0 or self.height <= 0.0:
            raise ValueError("ROI width and height must be positive.")
        if self.x < 0.0 or self.y < 0.0 or self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("ROI must fit within the normalized display rectangle.")

    def contains(self, x_norm: float, y_norm: float) -> bool:
        """Use half-open right/bottom edges to give adjacent ROIs a stable boundary."""
        return self.x <= x_norm < self.x + self.width and self.y <= y_norm < self.y + self.height


@dataclass(frozen=True, slots=True)
class RegionOfInterest:
    """A versionable semantic area on a packaging stimulus."""

    roi_id: str
    label: str
    bounds: NormalizedRect
    stimulus_id: str
    version: str
    description: str = ""

    def __post_init__(self) -> None:
        required_values = (self.roi_id, self.label, self.stimulus_id, self.version)
        if any(not value.strip() for value in required_values):
            raise ValueError("ROI id, label, stimulus id, and version must be non-empty.")
