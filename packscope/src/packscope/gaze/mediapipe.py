# SPDX-License-Identifier: Apache-2.0
"""Optional MediaPipe landmark feature extraction for a calibrated webcam backend.

This module deliberately emits face/iris features, not unvalidated screen gaze.
Callers must use a recorded display calibration before producing GazeSample values.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from packscope.errors import ConfigurationError, OptionalDependencyError


@dataclass(frozen=True, slots=True)
class IrisFeatureConfig:
    """Landmark indices used by the selected compatible Face Landmarker model asset."""

    left_iris_center_index: int = 468
    right_iris_center_index: int = 473


class MediaPipeIrisFeatureExtractor:
    """Extract normalized iris-center landmark features from an RGB image."""

    def __init__(self, model_asset_path: Path, config: IrisFeatureConfig | None = None) -> None:
        if not model_asset_path.is_file():
            raise ConfigurationError(f"MediaPipe model asset does not exist: {model_asset_path}")
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
        except ImportError as error:
            raise OptionalDependencyError("mediapipe", "webcam") from error

        options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_asset_path)),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
        )
        self._mp = mp
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._config = config or IrisFeatureConfig()

    def close(self) -> None:
        """Release MediaPipe resources."""
        self._landmarker.close()

    def extract(self, rgb_image: npt.ArrayLike) -> npt.NDArray[np.float64] | None:
        """Return [left_x, left_y, right_x, right_y], or None if a face is not usable."""
        array = np.asarray(rgb_image)
        if array.ndim != 3 or array.shape[2] != 3 or array.dtype != np.uint8:
            raise ConfigurationError("rgb_image must be a uint8 array with shape (height, width, 3).")
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=array)
        result = self._landmarker.detect(image)
        if not result.face_landmarks:
            return None
        landmarks = result.face_landmarks[0]
        required_index = max(self._config.left_iris_center_index, self._config.right_iris_center_index)
        if len(landmarks) <= required_index:
            return None
        left = landmarks[self._config.left_iris_center_index]
        right = landmarks[self._config.right_iris_center_index]
        return np.asarray((left.x, left.y, right.x, right.y), dtype=np.float64)
