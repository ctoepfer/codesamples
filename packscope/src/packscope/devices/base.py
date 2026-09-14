# SPDX-License-Identifier: Apache-2.0
"""Hardware-neutral contracts for timestamped EEG acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from packscope.models import EegFrame


@dataclass(frozen=True, slots=True)
class DeviceCapabilities:
    """Explicitly declares what a backend can and cannot produce."""

    source_name: str
    raw_eeg: bool
    frontal_asymmetry_possible: bool
    has_signal_quality: bool
    sample_rate_hz: float | None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BandPowerSnapshot:
    """A device-supplied relative-band snapshot, not a reconstructed raw EEG signal."""

    timestamp_monotonic_s: float
    source: str
    device_id: str
    bands: dict[str, float]
    signal_quality: int | None = None
    attention: int | None = None
    meditation: int | None = None
    quality_flags: tuple[str, ...] = ()


@runtime_checkable
class EegSource(Protocol):
    """Common lifecycle for backends that expose raw multi-channel EEG blocks."""

    @property
    def capabilities(self) -> DeviceCapabilities:
        """Return the source's declared measurement capabilities."""

    def start(self) -> None:
        """Acquire the device or stream."""

    def stop(self) -> None:
        """Release the device or stream."""

    def read_frame(self, max_samples: int) -> EegFrame | None:
        """Return newly available raw samples, or None when no samples are ready."""
