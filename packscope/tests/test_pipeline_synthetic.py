# SPDX-License-Identifier: Apache-2.0
"""Hardware-free integration tests using only the NumPy/SciPy core."""

from dataclasses import replace

import numpy as np
import pytest

from packscope.errors import ConfigurationError
from packscope.models import GazeSample, MetricStatus
from packscope.pipeline.runner import SessionRunner
from packscope.reporting.roi import NormalizedRect, RegionOfInterest
from packscope.testing.synthetic import generate_eeg_frames, generate_gaze_samples


def test_full_synthetic_pipeline() -> None:
    rois = [
        RegionOfInterest("left", "Left", NormalizedRect(0, 0, 0.5, 1), "demo", "v1"),
        RegionOfInterest("right", "Right", NormalizedRect(0.5, 0, 0.5, 1), "demo", "v1"),
    ]
    result = SessionRunner().run(generate_eeg_frames(noise_amplitude=0), generate_gaze_samples(), rois)
    assert result.eeg_frame_count == 2
    assert result.rejected_eeg_frames == result.rejected_gaze_samples == 0
    assert len(result.psd_metrics) == 8
    assert all(w.result.status == MetricStatus.AVAILABLE for w in result.psd_metrics)
    assert all(w.result.value == pytest.approx(np.log(4), abs=1e-8) for w in result.faa_metrics)
    assert result.psd_metrics[0].result.value == pytest.approx(0.5)
    assert result.rois[0].version == "v1"
    assert all(set(row.roi_dwell_s) == {"left", "right"} for row in result.roi_attributions)
    assert all(row.total_dwell_s <= 4 for row in result.roi_attributions)


def test_rejections_and_single_channel() -> None:
    frames = list(generate_eeg_frames(duration_s=5, channel_names=("FP1",), alpha_amplitudes=(1,)))
    summary = SessionRunner().run(frames, [GazeSample(0, False)], [])
    assert summary.rejected_eeg_frames == 1
    assert summary.rejected_eeg_samples == 250
    assert summary.rejected_gaze_samples == 1
    assert summary.faa_metrics[0].result.status == MetricStatus.INSUFFICIENT_CHANNELS
    assert summary.faa_metrics[1].result.status == MetricStatus.FAILED_QUALITY_GATE
    assert all(w.result.value is None for w in summary.psd_metrics[2:])
    flagged = replace(frames[0], quality_flags=("poor_contact",))
    assert SessionRunner().run([flagged], [], []).rejected_eeg_frames == 1


def test_empty_stream_and_bad_order() -> None:
    assert SessionRunner().run([], [], []).faa_metrics == ()
    frame = next(generate_eeg_frames())
    with pytest.raises(ConfigurationError, match="non-overlapping"):
        SessionRunner().run([frame, frame], [], [])
    with pytest.raises(ConfigurationError, match="ordered"):
        SessionRunner().run([], [GazeSample(1, False), GazeSample(0, False)], [])


def test_synthetic_repeatability_and_coordinates() -> None:
    first, second = next(generate_eeg_frames()), next(generate_eeg_frames())
    np.testing.assert_array_equal(first.samples, second.samples)
    gaze = list(generate_gaze_samples(duration_s=2))
    assert any(0.25 < s.x_norm < 0.75 for s in gaze)
    assert all(s.valid and s.calibration_id and 0 <= s.y_norm <= 1 for s in gaze)


@pytest.mark.parametrize(
    "kwargs",
    [{"sampling_rate_hz": 20}, {"noise_amplitude": float("nan")}, {"duration_s": 0}, {"channel_names": ("FP1",)}],
)
def test_invalid_synthetic_configuration(kwargs: dict) -> None:
    with pytest.raises(ConfigurationError):
        list(generate_eeg_frames(**kwargs))
