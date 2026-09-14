# SPDX-License-Identifier: Apache-2.0
"""Spatial annotations and local visual reporting helpers."""

from packscope.reporting.heatmap import render_gaze_heatmap
from packscope.reporting.roi import NormalizedRect, RegionOfInterest

__all__ = ["NormalizedRect", "RegionOfInterest", "render_gaze_heatmap"]
