# SPDX-License-Identifier: Apache-2.0
"""Conservative, transparent quality gates for raw EEG windows."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from packscope.models import EegFrame


@dataclass(frozen=True, slots=True)
class EegQualityConfig:
    """Unit-aware thresholds that callers must set for their device when appropriate."""

    min_duration_s: float = 2.0
    max_flatline_std: float = 1e-9
    max_absolute_amplitude: float | None = None
    max_timestamp_gap_factor: float = 2.5


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Result of tests that are deliberately insufficient to prove neural signal origin."""

    passed: bool
    flags: tuple[str, ...]
    duration_s: float
    maximum_absolute_amplitude: float


def assess_eeg_quality(frame: EegFrame, config: EegQualityConfig | None = None) -> QualityReport:
    """Check duration, flatlines, timing gaps, declared flags, and optional amplitude limits."""
    config = config or EegQualityConfig()
    if config.min_duration_s <= 0.0 or config.max_flatline_std < 0.0:
        raise ValueError("Quality thresholds must be non-negative and min_duration_s positive.")

    flags = list(frame.quality_flags)
    duration_s = (frame.samples.shape[1] - 1) / frame.sampling_rate_hz
    if duration_s < config.min_duration_s:
        flags.append("insufficient_duration")

    channel_stds = np.std(frame.samples, axis=1)
    if np.any(channel_stds <= config.max_flatline_std):
        flags.append("flatline_channel")

    maximum_absolute_amplitude = float(np.max(np.abs(frame.samples)))
    if config.max_absolute_amplitude is not None and maximum_absolute_amplitude > config.max_absolute_amplitude:
        flags.append("amplitude_exceeds_limit")

    if frame.timestamps_monotonic_s.size > 1:
        expected_interval = 1.0 / frame.sampling_rate_hz
        maximum_gap = expected_interval * config.max_timestamp_gap_factor
        if np.any(np.diff(frame.timestamps_monotonic_s) > maximum_gap):
            flags.append("timestamp_gap")

    return QualityReport(
        passed=not flags,
        flags=tuple(sorted(set(flags))),
        duration_s=duration_s,
        maximum_absolute_amplitude=maximum_absolute_amplitude,
    )
