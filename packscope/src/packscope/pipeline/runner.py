# SPDX-License-Identifier: Apache-2.0
"""Offline, frame-window analysis with explicit rejection accounting."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from packscope.analysis.attribution import WindowAttribution, attribute_metric_windows
from packscope.analysis.fixations import detect_fixations
from packscope.analysis.quality import EegQualityConfig, assess_eeg_quality
from packscope.analysis.spectral import ALPHA, BETA, band_power, frontal_alpha_asymmetry
from packscope.errors import ConfigurationError
from packscope.models import EegFrame, GazeSample, MetricResult, MetricStatus, MetricWindow
from packscope.reporting.roi import RegionOfInterest


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Measurements and independent gaze attribution, retaining ROI definitions/versions.

    EEG counts refer to frames (and time samples, not channel values). Gaze counts
    reject invalid, flagged or uncalibrated observations. Empty input yields no metrics.
    """

    psd_metrics: tuple[MetricWindow, ...]
    faa_metrics: tuple[MetricWindow, ...]
    roi_attributions: tuple[WindowAttribution, ...]
    rois: tuple[RegionOfInterest, ...]
    eeg_frame_count: int
    rejected_eeg_frames: int
    eeg_sample_count: int
    rejected_eeg_samples: int
    gaze_sample_count: int
    rejected_gaze_samples: int


class SessionRunner:
    """Analyze each supplied frame as one window; never concatenate across gaps."""

    def __init__(self, quality_config: EegQualityConfig | None = None) -> None:
        self.quality_config = quality_config or EegQualityConfig()

    def run(
        self, eeg_frames: Iterable[EegFrame], gaze_samples: Iterable[GazeSample], rois: Sequence[RegionOfInterest]
    ) -> SessionSummary:
        """Return quality-gated PSD/FAA and fixation dwell per FAA window.

        Streams must share a monotonic clock. Overlapping EEG frames are rejected as
        configuration errors to avoid silently double-counting data.
        """
        psd, faa = [], []
        frames = rejected = sample_count = rejected_samples = 0
        previous_end = None
        for frame in eeg_frames:
            if previous_end is not None and frame.start_time_s <= previous_end:
                raise ConfigurationError("EEG frames must be ordered and non-overlapping.")
            previous_end = frame.end_time_s
            frames += 1
            sample_count += frame.samples.shape[1]
            quality = assess_eeg_quality(frame, self.quality_config)
            rejected += int(not quality.passed)
            rejected_samples += frame.samples.shape[1] if not quality.passed else 0
            for channel in frame.channel_names:
                for band in (ALPHA, BETA):
                    result = (
                        band_power(frame, channel, band)
                        if quality.passed
                        else MetricResult(
                            f"{band.name}_power:{channel}",
                            MetricStatus.FAILED_QUALITY_GATE,
                            None,
                            "EEG quality gate failed: " + ", ".join(quality.flags),
                        )
                    )
                    psd.append(MetricWindow(frame.start_time_s, frame.end_time_s, result, frame.source))
            faa.append(
                MetricWindow(
                    frame.start_time_s,
                    frame.end_time_s,
                    frontal_alpha_asymmetry(frame, quality_config=self.quality_config),
                    frame.source,
                )
            )
        gaze = list(gaze_samples)
        rejected_gaze = sum(not s.valid or bool(s.quality_flags) or not s.calibration_id for s in gaze)
        cleaned = [
            replace(s, valid=False, x_norm=None, y_norm=None) if s.quality_flags or not s.calibration_id else s
            for s in gaze
        ]
        try:
            fixations = detect_fixations(cleaned)
            attributions = attribute_metric_windows(faa, fixations, rois)
        except ValueError as error:
            raise ConfigurationError(str(error)) from error
        return SessionSummary(
            tuple(psd),
            tuple(faa),
            tuple(attributions),
            tuple(rois),
            frames,
            rejected,
            sample_count,
            rejected_samples,
            len(gaze),
            rejected_gaze,
        )
