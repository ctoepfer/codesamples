# SPDX-License-Identifier: Apache-2.0
"""Quality thresholds detect explicit signal defects."""

from dataclasses import replace

import numpy as np
import pytest

from packscope.analysis.quality import EegQualityConfig, assess_eeg_quality
from packscope.testing.synthetic import generate_eeg_frames


@pytest.mark.parametrize("frequency", [50, 60])
def test_mains_ratio(frequency: int) -> None:
    frame = next(generate_eeg_frames(noise_amplitude=0))
    config = EegQualityConfig(line_noise_hz=frequency, max_line_noise_ratio=0.2)
    assert assess_eeg_quality(frame, config).passed
    noisy = replace(frame, samples=frame.samples + 10 * np.sin(2 * np.pi * frequency * frame.timestamps_monotonic_s))
    assert "line_noise_exceeds_limit" in assess_eeg_quality(noisy, config).flags


def test_saturation_and_partial_flatline() -> None:
    frame = next(generate_eeg_frames())
    assert "amplitude_saturation" in assess_eeg_quality(frame, EegQualityConfig(saturation_amplitude=0.5)).flags
    samples = frame.samples.copy()
    samples[:, :200] = 0
    flat = replace(frame, samples=samples)
    assert "flatline_segment" in assess_eeg_quality(flat, EegQualityConfig(flatline_duration_s=0.5)).flags
    assert assess_eeg_quality(flat, EegQualityConfig(max_flatline_std=None)).passed


def test_unassessable_line_noise_and_duplicate_time() -> None:
    frame = next(generate_eeg_frames(sampling_rate_hz=100))
    assert "line_noise_unassessable" in assess_eeg_quality(frame, EegQualityConfig(max_line_noise_ratio=0.2)).flags
    times = frame.timestamps_monotonic_s.copy()
    times[1] = times[0]
    assert "non_increasing_timestamps" in assess_eeg_quality(replace(frame, timestamps_monotonic_s=times)).flags


@pytest.mark.parametrize(
    "kwargs",
    [{"max_flatline_std": float("nan")}, {"min_duration_s": 0}, {"max_line_noise_ratio": 2}, {"line_noise_hz": 55}],
)
def test_invalid_thresholds(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        EegQualityConfig(**kwargs)
