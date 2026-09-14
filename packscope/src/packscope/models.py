# SPDX-License-Identifier: Apache-2.0
"""Normalized, validated data contracts shared by all PackScope components."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
import numpy.typing as npt


class MetricStatus(StrEnum):
    """Availability state for a derived measurement."""

    AVAILABLE = "available"
    INSUFFICIENT_CHANNELS = "insufficient_channels"
    INSUFFICIENT_SAMPLES = "insufficient_samples"
    FAILED_QUALITY_GATE = "failed_quality_gate"
    INVALID_INPUT = "invalid_input"


@dataclass(frozen=True, slots=True)
class MetricResult:
    """A transparent derived value that carries availability and provenance context."""

    name: str
    status: MetricStatus
    value: float | None
    reason: str | None = None
    details: Mapping[str, float | int | str | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status == MetricStatus.AVAILABLE and self.value is None:
            raise ValueError("An available metric must contain a numeric value.")
        if self.status != MetricStatus.AVAILABLE and self.value is not None:
            raise ValueError("An unavailable metric must not contain a numeric value.")
        if self.value is not None and not np.isfinite(self.value):
            raise ValueError("Metric values must be finite.")


@dataclass(frozen=True, slots=True)
class GazeSample:
    """One gaze observation in a top-left-origin normalized display coordinate space.

    Valid samples have coordinates in the closed interval [0, 1]. Invalid samples
    intentionally carry no coordinates, which prevents accidental AOI attribution.
    """

    timestamp_monotonic_s: float
    valid: bool
    x_norm: float | None = None
    y_norm: float | None = None
    confidence: float | None = None
    source: str = "unknown"
    calibration_id: str | None = None
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not np.isfinite(self.timestamp_monotonic_s):
            raise ValueError("Gaze timestamps must be finite.")
        if self.valid:
            if self.x_norm is None or self.y_norm is None:
                raise ValueError("Valid gaze samples require x_norm and y_norm.")
            if not (0.0 <= self.x_norm <= 1.0 and 0.0 <= self.y_norm <= 1.0):
                raise ValueError("Normalized gaze coordinates must be in [0, 1].")
        elif self.x_norm is not None or self.y_norm is not None:
            raise ValueError("Invalid gaze samples must not carry screen coordinates.")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Gaze confidence must be in [0, 1].")


@dataclass(frozen=True, slots=True)
class EegFrame:
    """A channel-by-sample EEG block with explicit timing and channel metadata.

    Samples are expressed in the device's documented raw units. The caller must not
    assume microvolts unless the source metadata explicitly records that convention.
    """

    samples: npt.NDArray[np.float64]
    timestamps_monotonic_s: npt.NDArray[np.float64]
    channel_names: tuple[str, ...]
    sampling_rate_hz: float
    source: str
    device_id: str
    quality_flags: tuple[str, ...] = ()
    metadata: Mapping[str, str | int | float | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        samples = np.asarray(self.samples, dtype=np.float64)
        timestamps = np.asarray(self.timestamps_monotonic_s, dtype=np.float64)
        if samples.ndim != 2:
            raise ValueError("EEG samples must have shape (channels, samples).")
        if samples.shape[0] != len(self.channel_names):
            raise ValueError("channel_names must match the first sample dimension.")
        if samples.shape[1] != timestamps.size:
            raise ValueError("Each EEG sample must have one timestamp.")
        if timestamps.ndim != 1 or timestamps.size == 0:
            raise ValueError("EEG timestamps must be a non-empty one-dimensional array.")
        if not np.all(np.isfinite(samples)) or not np.all(np.isfinite(timestamps)):
            raise ValueError("EEG frames cannot contain NaN or infinite values.")
        if np.any(np.diff(timestamps) < 0):
            raise ValueError("EEG timestamps must be non-decreasing.")
        if self.sampling_rate_hz <= 0.0 or not np.isfinite(self.sampling_rate_hz):
            raise ValueError("sampling_rate_hz must be a positive finite number.")
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "timestamps_monotonic_s", timestamps)

    @property
    def start_time_s(self) -> float:
        """First timestamp in the frame."""
        return float(self.timestamps_monotonic_s[0])

    @property
    def end_time_s(self) -> float:
        """Last timestamp in the frame."""
        return float(self.timestamps_monotonic_s[-1])


@dataclass(frozen=True, slots=True)
class MetricWindow:
    """A time-bounded EEG feature ready to join against gaze observations."""

    start_time_s: float
    end_time_s: float
    result: MetricResult
    source: str

    def __post_init__(self) -> None:
        if self.end_time_s < self.start_time_s:
            raise ValueError("Metric-window end time cannot precede its start time.")
