# SPDX-License-Identifier: Apache-2.0
"""Fixations must respect missing samples and validated time/coordinate contracts."""

import pytest

from packscope.analysis.fixations import detect_fixations
from packscope.models import GazeSample


def sample(time: float) -> GazeSample:
    return GazeSample(time, True, 0.5, 0.5)


@pytest.mark.parametrize("samples", [[], [sample(0)], [sample(0), sample(0.05)]])
def test_short_sequences(samples: list[GazeSample]) -> None:
    assert detect_fixations(samples) == []


def test_time_order_and_duplicate_timestamps() -> None:
    with pytest.raises(ValueError, match="ordered"):
        detect_fixations([sample(0.1), sample(0)])
    assert detect_fixations([sample(0), sample(0)]) == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timestamp_monotonic_s": float("nan"), "valid": False},
        {"timestamp_monotonic_s": 0, "valid": True, "x_norm": float("nan"), "y_norm": 0.5},
    ],
)
def test_nan_rejected_at_contract_boundary(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        GazeSample(**kwargs)


def test_nan_threshold_and_dropout_boundaries() -> None:
    with pytest.raises(ValueError):
        detect_fixations([], min_duration_s=float("nan"))
    gaze = [sample(0), sample(0.05), GazeSample(0.1, False), sample(0.15), sample(0.2)]
    assert detect_fixations(gaze) == []
    gaze = [sample(i / 100) for i in range(21)] + [sample(1 + i / 100) for i in range(21)]
    assert len(detect_fixations(gaze)) == 2
