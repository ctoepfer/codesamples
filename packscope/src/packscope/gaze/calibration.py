# SPDX-License-Identifier: Apache-2.0
"""Affine calibration from source features to normalized display-space gaze."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from packscope.errors import CalibrationError
from packscope.models import GazeSample


@dataclass(frozen=True, slots=True)
class CalibrationValidation:
    """Error statistics in the normalized display coordinate system."""

    median_error_norm: float
    percentile_95_error_norm: float
    rms_error_norm: float
    point_count: int


@dataclass(frozen=True, slots=True)
class AffineGazeCalibration:
    """A least-squares affine mapper fit from raw source features to display coordinates."""

    coefficients: npt.NDArray[np.float64]
    calibration_id: str
    validation: CalibrationValidation

    @classmethod
    def fit(
        cls,
        raw_features: npt.ArrayLike,
        target_coordinates_norm: npt.ArrayLike,
        *,
        calibration_id: str | None = None,
    ) -> AffineGazeCalibration:
        """Fit a calibration using at least five non-degenerate target measurements.

        A webcam's face or iris landmarks are features, not gaze coordinates. The
        calibration maps those features to the physical display where targets appear.
        """
        features = np.asarray(raw_features, dtype=np.float64)
        targets = np.asarray(target_coordinates_norm, dtype=np.float64)
        if features.ndim != 2 or targets.ndim != 2 or targets.shape[1] != 2:
            raise CalibrationError("Features must be (n, k) and targets must be (n, 2).")
        if features.shape[0] != targets.shape[0] or features.shape[0] < 5:
            raise CalibrationError("Calibration requires at least five paired measurements.")
        if not np.all(np.isfinite(features)) or not np.all(np.isfinite(targets)):
            raise CalibrationError("Calibration inputs must be finite.")
        if np.any(targets < 0.0) or np.any(targets > 1.0):
            raise CalibrationError("Calibration target coordinates must be in [0, 1].")
        if np.linalg.matrix_rank(np.column_stack((features, np.ones(features.shape[0])))) < features.shape[1] + 1:
            raise CalibrationError("Calibration features are degenerate; vary head and eye position.")

        design = np.column_stack((features, np.ones(features.shape[0])))
        coefficients, _, rank, _ = np.linalg.lstsq(design, targets, rcond=None)
        if rank < design.shape[1]:
            raise CalibrationError("Calibration design matrix is rank deficient.")
        predicted = design @ coefficients
        errors = np.linalg.norm(predicted - targets, axis=1)
        validation = CalibrationValidation(
            median_error_norm=float(np.median(errors)),
            percentile_95_error_norm=float(np.percentile(errors, 95)),
            rms_error_norm=float(np.sqrt(np.mean(np.square(errors)))),
            point_count=int(features.shape[0]),
        )
        return cls(
            coefficients=coefficients,
            calibration_id=calibration_id or str(uuid.uuid4()),
            validation=validation,
        )

    def map_sample(
        self,
        timestamp_monotonic_s: float,
        raw_features: npt.ArrayLike,
        *,
        source: str,
        confidence: float | None = None,
    ) -> GazeSample:
        """Map one feature vector, marking it invalid rather than clipping off-display results."""
        features = np.asarray(raw_features, dtype=np.float64)
        expected_size = self.coefficients.shape[0] - 1
        if features.ndim != 1 or features.size != expected_size or not np.all(np.isfinite(features)):
            return GazeSample(
                timestamp_monotonic_s=timestamp_monotonic_s,
                valid=False,
                confidence=confidence,
                source=source,
                calibration_id=self.calibration_id,
                quality_flags=("invalid_feature_vector",),
            )
        x_norm, y_norm = np.append(features, 1.0) @ self.coefficients
        if not (0.0 <= x_norm <= 1.0 and 0.0 <= y_norm <= 1.0):
            return GazeSample(
                timestamp_monotonic_s=timestamp_monotonic_s,
                valid=False,
                confidence=confidence,
                source=source,
                calibration_id=self.calibration_id,
                quality_flags=("predicted_off_display",),
            )
        return GazeSample(
            timestamp_monotonic_s=timestamp_monotonic_s,
            valid=True,
            x_norm=float(x_norm),
            y_norm=float(y_norm),
            confidence=confidence,
            source=source,
            calibration_id=self.calibration_id,
        )
