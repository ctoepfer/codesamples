# SPDX-License-Identifier: Apache-2.0
"""PSD-based, quality-gated EEG spectral features with no mental-state assertions."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import trapezoid
from scipy.signal import welch

from packscope.analysis.quality import EegQualityConfig, assess_eeg_quality
from packscope.models import EegFrame, MetricReason, MetricResult, MetricStatus


@dataclass(frozen=True, slots=True)
class FrequencyBand:
    """Inclusive lower and upper frequency bounds in Hertz."""

    name: str
    low_hz: float
    high_hz: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.low_hz, self.high_hz)) or not 0 < self.low_hz < self.high_hz:
            raise ValueError("Frequency bands require 0 < low_hz < high_hz.")


THETA = FrequencyBand("theta", 4.0, 7.0)
ALPHA = FrequencyBand("alpha", 8.0, 12.0)
BETA = FrequencyBand("beta", 13.0, 30.0)


def band_power(
    frame: EegFrame,
    channel_name: str,
    band: FrequencyBand,
    *,
    nperseg: int | None = None,
) -> MetricResult:
    """Estimate integrated power spectral density within a named, explicit channel band."""
    index = _channel_index(frame, channel_name)
    if index is None:
        return MetricResult(
            name=f"{band.name}_power:{channel_name}",
            status=MetricStatus.INSUFFICIENT_CHANNELS,
            value=None,
            reason=f"Channel '{channel_name}' is not present in the frame.",
        )
    if frame.samples.shape[1] < 8:
        return MetricResult(
            name=f"{band.name}_power:{channel_name}",
            status=MetricStatus.INSUFFICIENT_SAMPLES,
            value=None,
            reason=MetricReason.INSUFFICIENT_PSD_SAMPLES,
        )

    if (nperseg is not None and (not isinstance(nperseg, int) or nperseg < 2)
            or band.high_hz > frame.sampling_rate_hz / 2):
        return MetricResult(f"{band.name}_power:{channel_name}", MetricStatus.INVALID_INPUT, None,
                            MetricReason.INVALID_PSD_CONFIGURATION)
    segment = min(nperseg or max(2, int(round(frame.sampling_rate_hz))), frame.samples.shape[1])
    frequencies, density = welch(frame.samples[index], fs=frame.sampling_rate_hz, nperseg=segment, detrend="constant")
    mask = (frequencies >= band.low_hz) & (frequencies <= band.high_hz)
    if not np.any(mask):
        return MetricResult(
            name=f"{band.name}_power:{channel_name}",
            status=MetricStatus.INVALID_INPUT,
            value=None,
            reason=MetricReason.BAND_NOT_COVERED,
        )
    # PSD is density per Hertz, so integrate rather than average it. Averaging
    # would make the value depend on the number of frequency-grid bins in a
    # named band rather than the band-integrated spectral power.
    power = float(trapezoid(density[mask], frequencies[mask]))
    if not math.isfinite(power) or power <= 0.0:
        return MetricResult(
            name=f"{band.name}_power:{channel_name}",
            status=MetricStatus.INVALID_INPUT,
            value=None,
            reason=MetricReason.INVALID_BAND_POWER,
        )
    return MetricResult(
        name=f"{band.name}_power:{channel_name}",
        status=MetricStatus.AVAILABLE,
        value=power,
        details={"low_hz": band.low_hz, "high_hz": band.high_hz, "nperseg": segment},
    )


def frontal_alpha_asymmetry(
    frame: EegFrame,
    *,
    left_channel: str = "F3",
    right_channel: str = "F4",
    alpha_band: FrequencyBand = ALPHA,
    quality_config: EegQualityConfig | None = None,
) -> MetricResult:
    """Calculate ln(alpha power right) - ln(alpha power left), or return why unavailable.

    This is a named spectral convention. It is not an emotion, cognition, preference,
    diagnostic, or purchasing-intent measurement.
    """
    quality = assess_eeg_quality(frame, quality_config)
    if not quality.passed:
        return MetricResult(
            name="frontal_alpha_asymmetry",
            status=MetricStatus.FAILED_QUALITY_GATE,
            value=None,
            reason="EEG quality gate failed: " + ", ".join(quality.flags),
            details={"duration_s": quality.duration_s},
        )
    left = band_power(frame, left_channel, alpha_band)
    right = band_power(frame, right_channel, alpha_band)
    if left.status != MetricStatus.AVAILABLE or right.status != MetricStatus.AVAILABLE:
        missing = ", ".join(
            result.reason or result.status.value for result in (left, right) if result.status != MetricStatus.AVAILABLE
        )
        return MetricResult(
            name="frontal_alpha_asymmetry",
            status=(
                MetricStatus.INSUFFICIENT_CHANNELS
                if MetricStatus.INSUFFICIENT_CHANNELS in {left.status, right.status}
                else next(r.status for r in (left, right) if r.status != MetricStatus.AVAILABLE)
            ),
            value=None,
            reason=missing,
        )
    value = float(math.log(right.value) - math.log(left.value))
    return MetricResult(
        name="frontal_alpha_asymmetry",
        status=MetricStatus.AVAILABLE,
        value=value,
        details={
            "left_channel": left_channel.upper(),
            "right_channel": right_channel.upper(),
            "band_low_hz": alpha_band.low_hz,
            "band_high_hz": alpha_band.high_hz,
        },
    )


def beta_to_theta_power_ratio(
    frame: EegFrame,
    channel_name: str,
    *,
    quality_config: EegQualityConfig | None = None,
) -> MetricResult:
    """Return a transparent beta/theta PSD ratio; do not label it cognitive load."""
    quality = assess_eeg_quality(frame, quality_config)
    if not quality.passed:
        return MetricResult(
            name=f"beta_to_theta_power_ratio:{channel_name}",
            status=MetricStatus.FAILED_QUALITY_GATE,
            value=None,
            reason="EEG quality gate failed: " + ", ".join(quality.flags),
        )
    theta = band_power(frame, channel_name, THETA)
    beta = band_power(frame, channel_name, BETA)
    if theta.status != MetricStatus.AVAILABLE or beta.status != MetricStatus.AVAILABLE:
        unavailable = theta if theta.status != MetricStatus.AVAILABLE else beta
        return MetricResult(
            name=f"beta_to_theta_power_ratio:{channel_name}",
            status=unavailable.status,
            value=None,
            reason=unavailable.reason,
        )
    ratio = float(beta.value / theta.value)
    if not math.isfinite(ratio):
        return MetricResult(f"beta_to_theta_power_ratio:{channel_name}", MetricStatus.INVALID_INPUT, None,
                            MetricReason.NON_FINITE_RATIO)
    return MetricResult(
        name=f"beta_to_theta_power_ratio:{channel_name}",
        status=MetricStatus.AVAILABLE,
        value=ratio,
        details={"channel": channel_name.upper()},
    )


def _channel_index(frame: EegFrame, channel_name: str) -> int | None:
    canonical = channel_name.strip().upper()
    matches = [index for index, name in enumerate(frame.channel_names) if name.upper() == canonical]
    if len(matches) != 1:
        return None
    return matches[0]
