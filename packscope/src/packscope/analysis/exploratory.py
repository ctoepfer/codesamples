# SPDX-License-Identifier: Apache-2.0
"""Explicitly hypothesis-only two-axis annotations for exploratory visualizations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packscope.models import MetricResult, MetricStatus


class ExploratoryQuadrant(StrEnum):
    """Labels inspired by packaging-research hypotheses, not psychological detections."""

    INTEREST_HYPOTHESIS = "interest_hypothesis"
    CONFUSION_HYPOTHESIS = "confusion_hypothesis"
    EASY_ENJOYMENT_HYPOTHESIS = "easy_enjoyment_hypothesis"
    UNENGAGED_HYPOTHESIS = "unengaged_hypothesis"


@dataclass(frozen=True, slots=True)
class ExploratoryAxisConvention:
    """Predeclared within-session thresholds; never universal psychological cutoffs."""

    x_metric_name: str
    y_metric_name: str
    x_baseline_relative_threshold: float = 0.0
    y_baseline_relative_threshold: float = 0.0


def assign_exploratory_quadrant(
    x_baseline_relative: MetricResult,
    y_baseline_relative: MetricResult,
    convention: ExploratoryAxisConvention,
) -> ExploratoryQuadrant | None:
    """Return an opt-in hypothesis label only for two available declared metrics."""
    if (
        x_baseline_relative.status != MetricStatus.AVAILABLE
        or y_baseline_relative.status != MetricStatus.AVAILABLE
        or x_baseline_relative.value is None
        or y_baseline_relative.value is None
    ):
        return None
    x_positive = x_baseline_relative.value >= convention.x_baseline_relative_threshold
    y_positive = y_baseline_relative.value >= convention.y_baseline_relative_threshold
    if x_positive and y_positive:
        return ExploratoryQuadrant.INTEREST_HYPOTHESIS
    if not x_positive and y_positive:
        return ExploratoryQuadrant.CONFUSION_HYPOTHESIS
    if x_positive and not y_positive:
        return ExploratoryQuadrant.EASY_ENJOYMENT_HYPOTHESIS
    return ExploratoryQuadrant.UNENGAGED_HYPOTHESIS
