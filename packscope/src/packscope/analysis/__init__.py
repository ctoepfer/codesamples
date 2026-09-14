# SPDX-License-Identifier: Apache-2.0
"""Quality-gated signal processing and multimodal attribution."""

from packscope.analysis.attribution import WindowAttribution, attribute_metric_windows
from packscope.analysis.baseline import robust_z_score
from packscope.analysis.fixations import Fixation, detect_fixations
from packscope.analysis.quality import EegQualityConfig, QualityReport, assess_eeg_quality
from packscope.analysis.spectral import (
    ALPHA,
    BETA,
    THETA,
    FrequencyBand,
    band_power,
    beta_to_theta_power_ratio,
    frontal_alpha_asymmetry,
)

__all__ = [
    "ALPHA",
    "BETA",
    "THETA",
    "EegQualityConfig",
    "Fixation",
    "FrequencyBand",
    "QualityReport",
    "WindowAttribution",
    "assess_eeg_quality",
    "attribute_metric_windows",
    "band_power",
    "beta_to_theta_power_ratio",
    "frontal_alpha_asymmetry",
    "robust_z_score",
    "detect_fixations",
]
