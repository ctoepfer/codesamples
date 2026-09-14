from __future__ import annotations

from packscope.analysis.attribution import attribute_metric_windows
from packscope.analysis.fixations import detect_fixations
from packscope.models import GazeSample, MetricResult, MetricStatus, MetricWindow
from packscope.reporting.roi import NormalizedRect, RegionOfInterest


def test_fixation_dwell_is_joined_to_a_matching_metric_window() -> None:
    samples = [
        GazeSample(0.00, True, 0.25, 0.25, source="test"),
        GazeSample(0.10, True, 0.26, 0.25, source="test"),
        GazeSample(0.20, True, 0.25, 0.26, source="test"),
        GazeSample(0.30, True, 0.25, 0.25, source="test"),
    ]
    fixations = detect_fixations(samples, max_dispersion_norm=0.05, min_duration_s=0.1)
    window = MetricWindow(
        start_time_s=0.05,
        end_time_s=0.25,
        result=MetricResult("alpha_change", MetricStatus.AVAILABLE, 0.2),
        source="test",
    )
    roi = RegionOfInterest("logo", "Logo", NormalizedRect(0.1, 0.1, 0.3, 0.3), "can-a", "1")

    attribution = attribute_metric_windows([window], fixations, [roi])[0]

    assert len(fixations) == 1
    assert attribution.fixation_count == 1
    assert attribution.roi_dwell_s["logo"] == 0.2
    assert attribution.unassigned_dwell_s == 0.0
