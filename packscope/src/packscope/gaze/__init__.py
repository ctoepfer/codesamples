# SPDX-License-Identifier: Apache-2.0
"""Calibrated, top-left-origin normalized gaze interfaces."""

from packscope.gaze.base import DisplayGeometry, GazeCapabilities, GazeSource
from packscope.gaze.calibration import AffineGazeCalibration, CalibrationValidation
from packscope.gaze.mediapipe import IrisFeatureConfig, MediaPipeIrisFeatureExtractor
from packscope.gaze.quality import GazeQualityReport, assess_gaze_quality

__all__ = [
    "AffineGazeCalibration",
    "CalibrationValidation",
    "DisplayGeometry",
    "GazeCapabilities",
    "GazeQualityReport",
    "GazeSource",
    "IrisFeatureConfig",
    "MediaPipeIrisFeatureExtractor",
    "assess_gaze_quality",
]
