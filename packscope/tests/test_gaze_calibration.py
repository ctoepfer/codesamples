from __future__ import annotations

import numpy as np
import pytest

from packscope.gaze.calibration import AffineGazeCalibration


def test_affine_calibration_maps_features_to_normalized_display() -> None:
    targets = np.array([[0.1, 0.1], [0.9, 0.1], [0.1, 0.9], [0.9, 0.9], [0.5, 0.5]])
    features = np.column_stack((targets[:, 0] * 2.0 + 0.25, targets[:, 1] * 3.0 - 0.4))
    calibration = AffineGazeCalibration.fit(features, targets, calibration_id="cal-1")

    sample = calibration.map_sample(1.0, np.array([1.25, 1.1]), source="webcam")

    assert sample.valid
    assert sample.calibration_id == "cal-1"
    assert sample.x_norm == pytest.approx(0.5)
    assert sample.y_norm == pytest.approx(0.5)
    assert calibration.validation.median_error_norm < 1e-12


def test_affine_calibration_marks_off_display_prediction_invalid() -> None:
    targets = np.array([[0.1, 0.1], [0.9, 0.1], [0.1, 0.9], [0.9, 0.9], [0.5, 0.5]])
    calibration = AffineGazeCalibration.fit(targets, targets)

    sample = calibration.map_sample(1.0, np.array([1.5, 0.5]), source="webcam")

    assert not sample.valid
    assert sample.quality_flags == ("predicted_off_display",)
