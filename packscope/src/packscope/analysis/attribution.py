# SPDX-License-Identifier: Apache-2.0
"""Time-windowed linking of transparent EEG metrics to independently detected fixations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from packscope.analysis.fixations import Fixation
from packscope.models import MetricWindow
from packscope.reporting.roi import RegionOfInterest


@dataclass(frozen=True, slots=True)
class WindowAttribution:
    """Spatial allocation observed during a metric window, including unassigned dwell."""

    metric_window: MetricWindow
    roi_dwell_s: dict[str, float]
    unassigned_dwell_s: float
    fixation_count: int

    @property
    def total_dwell_s(self) -> float:
        """Dwell time overlapping the window after validity and fixation rules."""
        return self.unassigned_dwell_s + sum(self.roi_dwell_s.values())


def attribute_metric_windows(
    windows: Sequence[MetricWindow],
    fixations: Sequence[Fixation],
    rois: Sequence[RegionOfInterest],
) -> list[WindowAttribution]:
    """Join overlapping fixation dwell to metric windows without inferring causality.

    The result says where a calibrated fixation overlapped a quality-gated spectral
    window. It does not show that the package element caused a neural response.
    """
    _validate_rois(rois)
    results: list[WindowAttribution] = []
    for window in windows:
        roi_dwell = {roi.roi_id: 0.0 for roi in rois}
        unassigned = 0.0
        matched = 0
        for fixation in fixations:
            overlap = _overlap_seconds(
                window.start_time_s, window.end_time_s, fixation.start_time_s, fixation.end_time_s
            )
            if overlap <= 0.0:
                continue
            matched += 1
            roi = next(
                (candidate for candidate in rois if candidate.bounds.contains(fixation.x_norm, fixation.y_norm)),
                None,
            )
            if roi is None:
                unassigned += overlap
            else:
                roi_dwell[roi.roi_id] += overlap
        results.append(
            WindowAttribution(
                metric_window=window,
                roi_dwell_s={key: value for key, value in roi_dwell.items() if value > 0.0},
                unassigned_dwell_s=unassigned,
                fixation_count=matched,
            )
        )
    return results


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _validate_rois(rois: Sequence[RegionOfInterest]) -> None:
    identifiers = [roi.roi_id for roi in rois]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("ROI identifiers must be unique.")
    if len({roi.stimulus_id for roi in rois}) > 1:
        raise ValueError("A single attribution call must use ROIs from one stimulus.")
