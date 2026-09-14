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
    max_flatline_std: float | None = 1e-9
    max_absolute_amplitude: float | None = None
    max_timestamp_gap_factor: float = 2.5
    saturation_amplitude: float | None = None
    max_saturation_fraction: float = 0.01
    line_noise_hz: float = 50.0
    max_line_noise_ratio: float | None = None
    flatline_duration_s: float | None = None

    def __post_init__(self) -> None:
        for name in ("min_duration_s", "max_timestamp_gap_factor", "line_noise_hz"):
            value = getattr(self, name)
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite.")
        for name in ("max_flatline_std", "max_absolute_amplitude", "saturation_amplitude",
                     "max_line_noise_ratio", "flatline_duration_s"):
            value = getattr(self, name)
            if value is not None and (not np.isfinite(value) or value < 0):
                raise ValueError(f"{name} must be non-negative and finite, or None.")
        if not 0 <= self.max_saturation_fraction <= 1:
            raise ValueError("max_saturation_fraction must be in [0, 1].")
        if self.line_noise_hz not in (50.0, 60.0):
            raise ValueError("line_noise_hz must be 50 or 60.")
        if self.max_line_noise_ratio is not None and self.max_line_noise_ratio > 1:
            raise ValueError("max_line_noise_ratio must be in [0, 1].")


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

    flags = list(frame.quality_flags)
    duration_s = frame.samples.shape[1] / frame.sampling_rate_hz
    if duration_s < config.min_duration_s:
        flags.append("insufficient_duration")

    channel_stds = np.std(frame.samples, axis=1)
    if config.max_flatline_std is not None and np.any(channel_stds <= config.max_flatline_std):
        flags.append("flatline_channel")

    maximum_absolute_amplitude = float(np.max(np.abs(frame.samples)))
    if config.max_absolute_amplitude is not None and maximum_absolute_amplitude > config.max_absolute_amplitude:
        flags.append("amplitude_exceeds_limit")

    if config.saturation_amplitude is not None:
        fractions = np.mean(np.abs(frame.samples) >= config.saturation_amplitude, axis=1)
        if np.any(fractions > config.max_saturation_fraction):
            flags.append("amplitude_saturation")

    if config.flatline_duration_s is not None:
        threshold = config.max_flatline_std or 0.0
        for channel in frame.samples:
            run = 0
            for difference in np.abs(np.diff(channel)):
                run = run + 1 if difference <= threshold else 0
                if run > 0 and run / frame.sampling_rate_hz >= config.flatline_duration_s:
                    flags.append("flatline_segment")
                    break

    if config.max_line_noise_ratio is not None:
        if frame.sampling_rate_hz / 2 < config.line_noise_hz + 1 or frame.samples.shape[1] < 8:
            flags.append("line_noise_unassessable")
        else:
            # Fraction of non-DC periodogram power within +/-1 Hz of mains frequency.
            centered = frame.samples - np.mean(frame.samples, axis=1, keepdims=True)
            with np.errstate(over="ignore", invalid="ignore"):
                power = np.abs(np.fft.rfft(centered * np.hanning(centered.shape[1]), axis=1)) ** 2
                frequencies = np.fft.rfftfreq(centered.shape[1], 1 / frame.sampling_rate_hz)
                mask = np.abs(frequencies - config.line_noise_hz) <= 1
                total = power[:, 1:].sum(axis=1)
                ratios = np.divide(power[:, mask].sum(axis=1), total,
                                   out=np.full_like(total, np.nan), where=total > 0)
            if not np.any(mask) or not np.all(np.isfinite(ratios)):
                flags.append("line_noise_unassessable")
            elif np.any(ratios > config.max_line_noise_ratio):
                flags.append("line_noise_exceeds_limit")

    if frame.timestamps_monotonic_s.size > 1:
        expected_interval = 1.0 / frame.sampling_rate_hz
        maximum_gap = expected_interval * config.max_timestamp_gap_factor
        if np.any(np.diff(frame.timestamps_monotonic_s) <= 0):
            flags.append("non_increasing_timestamps")
        if np.any(np.diff(frame.timestamps_monotonic_s) > maximum_gap):
            flags.append("timestamp_gap")

    return QualityReport(
        passed=not flags,
        flags=tuple(sorted(set(flags))),
        duration_s=duration_s,
        maximum_absolute_amplitude=maximum_absolute_amplitude,
    )
