# SPDX-License-Identifier: Apache-2.0
"""Normalized, validated data contracts shared by all PackScope components."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import StrEnum
from numbers import Real
from typing import Generic, TypeVar

import numpy as np
import numpy.typing as npt

from packscope.privacy import SessionConsent as SessionConsent


class MetricStatus(StrEnum):
    """Availability state for a derived measurement."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    INSUFFICIENT_CHANNELS = "insufficient_channels"
    INSUFFICIENT_SAMPLES = "insufficient_samples"
    FAILED_QUALITY_GATE = "failed_quality_gate"
    INVALID_INPUT = "invalid_input"


class MetricReason(StrEnum):
    """Stable explanations for common unavailable numeric measurements."""

    INSUFFICIENT_PSD_SAMPLES = "At least eight samples are required for PSD estimation."
    INVALID_PSD_CONFIGURATION = "Band must fit below Nyquist and nperseg must be an integer >= 2."
    BAND_NOT_COVERED = "The Welch frequency grid does not cover the requested band."
    INVALID_BAND_POWER = "Band-power estimate is not a positive finite number."
    NON_FINITE_RATIO = "Power ratio is not finite."
    CONSENT_NOT_GRANTED = "CONSENT_NOT_GRANTED"
    FREETEXT_CONSENT_NOT_GRANTED = "FREETEXT_CONSENT_NOT_GRANTED"
    MISSING_HEDONIC_SCORE = "MISSING_HEDONIC_SCORE"
    RATING_QUALITY_FAILED = "RATING_QUALITY_FAILED"
    INVALID_SENSORY_RECORD = "INVALID_SENSORY_RECORD"
    MISSING_PROTOCOL = "MISSING_PROTOCOL"
    MISSING_RATING = "MISSING_RATING"
    MISSING_ATTRIBUTION = "MISSING_ATTRIBUTION"
    AMBIGUOUS_RATING = "AMBIGUOUS_RATING"
    PREFERENCE_RANK_CONFLICT = "PREFERENCE_RANK_CONFLICT"
    PROVENANCE_MISMATCH = "PROVENANCE_MISMATCH"
    INVALID_ATTRIBUTION = "INVALID_ATTRIBUTION"
    NO_QUALIFYING_PAIRS = "NO_QUALIFYING_PAIRS"


T = TypeVar("T")


@dataclass(frozen=True)
class MetricResult(Generic[T]):
    """A transparent derived value that carries availability and provenance context."""

    name: str
    status: MetricStatus
    value: T | None
    reason: str | MetricReason | None = None
    details: Mapping[str, float | int | str | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status == MetricStatus.AVAILABLE and self.value is None:
            raise ValueError("An available result must contain a value.")
        if self.status != MetricStatus.AVAILABLE and not self.reason:
            raise ValueError("An unavailable metric must explain its reason.")
        if self.status != MetricStatus.AVAILABLE and self.value is not None:
            raise ValueError("An unavailable metric must not contain a numeric value.")
        if self.value is not None:
            if isinstance(self.value, bool) or not (isinstance(self.value, Real) or is_dataclass(self.value)):
                raise ValueError("Metric values must be numeric or structured dataclass records.")
            _validate_finite_payload(self.value)


def _validate_finite_payload(value: object) -> None:
    """Apply the finite-value invariant recursively to structured result payloads."""
    if isinstance(value, Real):
        if not np.isfinite(value):
            raise ValueError("Metric values must be finite.")
    elif is_dataclass(value) and not isinstance(value, type):
        for item in fields(value):
            _validate_finite_payload(getattr(value, item.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _validate_finite_payload(key)
            _validate_finite_payload(item)
    elif isinstance(value, (list, tuple, frozenset)):
        for item in value:
            _validate_finite_payload(item)
    elif value is not None and not isinstance(value, (str, datetime)):
        raise ValueError("Unsupported structured metric field.")


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
        if samples.shape[0] == 0:
            raise ValueError("EEG frames require at least one explicitly named channel.")
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
    result: MetricResult[float]
    source: str

    def __post_init__(self) -> None:
        if self.end_time_s < self.start_time_s:
            raise ValueError("Metric-window end time cannot precede its start time.")
