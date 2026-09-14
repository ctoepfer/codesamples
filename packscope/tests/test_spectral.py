# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from packscope.analysis.spectral import beta_to_theta_power_ratio, frontal_alpha_asymmetry
from packscope.models import EegFrame, MetricStatus


def _frame(channel_names: tuple[str, ...], signals: list[np.ndarray], fs: float = 250.0) -> EegFrame:
    timestamps = np.arange(signals[0].size, dtype=np.float64) / fs
    return EegFrame(
        samples=np.vstack(signals),
        timestamps_monotonic_s=timestamps,
        channel_names=channel_names,
        sampling_rate_hz=fs,
        source="test",
        device_id="test-device",
    )


def test_frontal_alpha_asymmetry_uses_both_channels() -> None:
    fs = 250.0
    time = np.arange(int(fs * 4.0)) / fs
    frame = _frame(("F3", "F4"), [np.sin(2 * np.pi * 10 * time), 2 * np.sin(2 * np.pi * 10 * time)])

    result = frontal_alpha_asymmetry(frame)

    assert result.status == MetricStatus.AVAILABLE
    assert result.value is not None and result.value > 1.2
    assert result.details["left_channel"] == "F3"
    assert result.details["right_channel"] == "F4"


def test_frontal_alpha_asymmetry_is_unavailable_without_bilateral_channels() -> None:
    fs = 250.0
    time = np.arange(int(fs * 4.0)) / fs
    frame = _frame(("FP1",), [np.sin(2 * np.pi * 10 * time)])

    result = frontal_alpha_asymmetry(frame)

    assert result.status == MetricStatus.INSUFFICIENT_CHANNELS
    assert result.value is None


def test_beta_theta_ratio_is_signal_derived_not_cognitive_label() -> None:
    fs = 250.0
    time = np.arange(int(fs * 4.0)) / fs
    signal = np.sin(2 * np.pi * 5 * time) + 2 * np.sin(2 * np.pi * 20 * time)

    result = beta_to_theta_power_ratio(_frame(("C3",), [signal]), "C3")

    assert result.status == MetricStatus.AVAILABLE
    assert result.name == "beta_to_theta_power_ratio:C3"
    assert result.value is not None and result.value > 2.0


def test_invalid_psd_configuration_returns_reason() -> None:
    from packscope.analysis.spectral import ALPHA, band_power
    from packscope.models import MetricReason

    time = np.arange(1000) / 250
    frame = _frame(("F3",), [np.sin(2 * np.pi * 10 * time)])
    result = band_power(frame, "F3", ALPHA, nperseg=-1)
    assert result.status == MetricStatus.INVALID_INPUT
    assert result.value is None
    assert result.reason == MetricReason.INVALID_PSD_CONFIGURATION


def test_nonfinite_band_power_is_unavailable() -> None:
    from packscope.analysis.spectral import ALPHA, band_power

    time = np.arange(1000) / 250
    frame = _frame(("F3",), [1e200 * np.sin(2 * np.pi * 10 * time)])
    with np.errstate(over="ignore", invalid="ignore"):
        result = band_power(frame, "F3", ALPHA)
    assert result.status == MetricStatus.INVALID_INPUT
    assert result.value is None and result.reason
