# SPDX-License-Identifier: Apache-2.0
"""Display-coordinate conventions and source capabilities for gaze integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from packscope.models import GazeSample


@dataclass(frozen=True, slots=True)
class DisplayGeometry:
    """Physical stimulus-display geometry with an origin at the top-left pixel."""

    width_px: int
    height_px: int
    screen_id: str = "primary"

    def __post_init__(self) -> None:
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("Display width_px and height_px must be positive.")

    def pixels_to_normalized(self, x_px: float, y_px: float) -> tuple[float, float]:
        """Convert a display pixel position to the PackScope [0, 1] coordinate space."""
        return x_px / self.width_px, y_px / self.height_px

    def normalized_to_pixels(self, x_norm: float, y_norm: float) -> tuple[float, float]:
        """Convert a normalized coordinate to display pixels without rounding."""
        if not 0.0 <= x_norm <= 1.0 or not 0.0 <= y_norm <= 1.0:
            raise ValueError("Normalized coordinates must be in [0, 1].")
        return x_norm * self.width_px, y_norm * self.height_px


@dataclass(frozen=True, slots=True)
class GazeCapabilities:
    """Source-specific caveats surfaced to experiments and exports."""

    source_name: str
    requires_calibration: bool
    dedicated_eyetracker: bool
    provides_confidence: bool
    notes: tuple[str, ...] = ()


@runtime_checkable
class GazeSource(Protocol):
    """Minimal lifecycle for sources that already emit display-space gaze samples."""

    @property
    def capabilities(self) -> GazeCapabilities:
        """Return known source capabilities and constraints."""

    def start(self) -> None:
        """Start data acquisition."""

    def stop(self) -> None:
        """Stop data acquisition."""

    def read_sample(self) -> GazeSample | None:
        """Return one normalized display-space sample, or None when no sample is ready."""
