# SPDX-License-Identifier: Apache-2.0
"""PackScope: exploratory gaze and EEG attribution for packaging studies.

The package intentionally reports calibrated measurements and quality metadata,
rather than claiming to infer emotion, intent, or medical/psychological states.
"""

from typing import Any

__all__ = ["EegFrame", "GazeSample", "MetricResult", "MetricStatus", "MetricReason"]
__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    """Load numeric contracts on demand so dependency diagnostics can run without NumPy."""
    if name in __all__:
        from packscope import models
        return getattr(models, name)
    raise AttributeError(name)
