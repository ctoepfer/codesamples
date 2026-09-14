# SPDX-License-Identifier: Apache-2.0
"""PackScope: exploratory gaze and EEG attribution for packaging studies.

The package intentionally reports calibrated measurements and quality metadata,
rather than claiming to infer emotion, intent, or medical/psychological states.
"""

from packscope.models import EegFrame, GazeSample, MetricResult, MetricStatus

__all__ = ["EegFrame", "GazeSample", "MetricResult", "MetricStatus"]
__version__ = "0.1.0"
