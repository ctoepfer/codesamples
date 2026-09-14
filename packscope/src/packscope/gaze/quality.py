# SPDX-License-Identifier: Apache-2.0
"""Quality summaries for calibrated gaze samples."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from packscope.models import GazeSample


@dataclass(frozen=True, slots=True)
class GazeQualityReport:
    """Descriptive quality statistics, not an accuracy guarantee."""

    sample_count: int
    valid_fraction: float
    dropout_fraction: float
    median_confidence: float | None


def assess_gaze_quality(samples: Sequence[GazeSample]) -> GazeQualityReport:
    """Summarize validity and reported confidence without masking dropout."""
    if not samples:
        return GazeQualityReport(0, 0.0, 1.0, None)
    valid = [sample for sample in samples if sample.valid]
    confidences = [sample.confidence for sample in valid if sample.confidence is not None]
    valid_fraction = len(valid) / len(samples)
    return GazeQualityReport(
        sample_count=len(samples),
        valid_fraction=valid_fraction,
        dropout_fraction=1.0 - valid_fraction,
        median_confidence=(float(np.median(confidences)) if confidences else None),
    )
