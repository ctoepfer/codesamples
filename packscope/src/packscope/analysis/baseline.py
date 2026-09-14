# SPDX-License-Identifier: Apache-2.0
"""Within-session baseline normalization utilities for exploratory comparisons."""

from __future__ import annotations

import numpy as np

from packscope.models import MetricResult, MetricStatus


def robust_z_score(value: float, baseline_values: np.ndarray) -> MetricResult:
    """Compute a median/MAD normalized within-session difference when mathematically valid."""
    baseline = np.asarray(baseline_values, dtype=np.float64)
    finite = baseline[np.isfinite(baseline)]
    if not np.isfinite(value) or finite.size < 3:
        return MetricResult(
            name="baseline_robust_z_score",
            status=MetricStatus.INVALID_INPUT,
            value=None,
            reason="A finite value and at least three finite baseline values are required.",
        )
    median = float(np.median(finite))
    mad = float(np.median(np.abs(finite - median)))
    if mad == 0.0:
        return MetricResult(
            name="baseline_robust_z_score",
            status=MetricStatus.INVALID_INPUT,
            value=None,
            reason="Baseline median absolute deviation is zero.",
        )
    # 1.4826 scales normal-distribution MAD to a standard-deviation estimate.
    result = (value - median) / (1.4826 * mad)
    return MetricResult(
        name="baseline_robust_z_score",
        status=MetricStatus.AVAILABLE,
        value=float(result),
        details={"baseline_n": int(finite.size), "baseline_median": median, "baseline_mad": mad},
    )
