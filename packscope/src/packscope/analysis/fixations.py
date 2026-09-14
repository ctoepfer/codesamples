# SPDX-License-Identifier: Apache-2.0
"""Simple I-DT fixation extraction with explicit dropout boundaries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from packscope.models import GazeSample


@dataclass(frozen=True, slots=True)
class Fixation:
    """A dispersion-bounded cluster of valid display-space gaze observations."""

    start_time_s: float
    end_time_s: float
    x_norm: float
    y_norm: float
    sample_count: int

    @property
    def duration_s(self) -> float:
        """Elapsed duration from first to final sample."""
        return self.end_time_s - self.start_time_s


def detect_fixations(
    samples: Sequence[GazeSample],
    *,
    max_dispersion_norm: float = 0.05,
    min_duration_s: float = 0.10,
    max_sample_gap_s: float = 0.10,
) -> list[Fixation]:
    """Extract I-DT fixations without bridging invalid samples or long timing gaps.

    Dispersion is (max_x - min_x) + (max_y - min_y). This intentionally modest
    detector is a transparent default, not a substitute for a tracker-specific
    validated event classifier. Parameters should be retained in the session record.
    """
    if max_dispersion_norm <= 0.0 or min_duration_s <= 0.0 or max_sample_gap_s <= 0.0:
        raise ValueError("Fixation thresholds must be positive.")
    _validate_time_order(samples)
    fixations: list[Fixation] = []
    for run in _valid_contiguous_runs(samples, max_sample_gap_s):
        index = 0
        while index < len(run):
            end = index
            while end < len(run) and run[end].timestamp_monotonic_s - run[index].timestamp_monotonic_s < min_duration_s:
                end += 1
            if end >= len(run):
                break
            if _dispersion(run[index : end + 1]) > max_dispersion_norm:
                index += 1
                continue
            while end + 1 < len(run) and _dispersion(run[index : end + 2]) <= max_dispersion_norm:
                end += 1
            window = run[index : end + 1]
            fixations.append(
                Fixation(
                    start_time_s=window[0].timestamp_monotonic_s,
                    end_time_s=window[-1].timestamp_monotonic_s,
                    x_norm=float(np.mean([sample.x_norm for sample in window])),  # valid by construction
                    y_norm=float(np.mean([sample.y_norm for sample in window])),
                    sample_count=len(window),
                )
            )
            index = end + 1
    return fixations


def _validate_time_order(samples: Sequence[GazeSample]) -> None:
    timestamps = [sample.timestamp_monotonic_s for sample in samples]
    if any(second < first for first, second in zip(timestamps, timestamps[1:], strict=False)):
        raise ValueError("Gaze samples must be ordered by non-decreasing timestamp.")


def _valid_contiguous_runs(samples: Sequence[GazeSample], max_gap_s: float) -> list[list[GazeSample]]:
    runs: list[list[GazeSample]] = []
    current: list[GazeSample] = []
    for sample in samples:
        if not sample.valid or (
            current and sample.timestamp_monotonic_s - current[-1].timestamp_monotonic_s > max_gap_s
        ):
            if current:
                runs.append(current)
                current = []
            if not sample.valid:
                continue
        current.append(sample)
    if current:
        runs.append(current)
    return runs


def _dispersion(samples: Sequence[GazeSample]) -> float:
    x_values = [sample.x_norm for sample in samples]
    y_values = [sample.y_norm for sample in samples]
    return float(max(x_values) - min(x_values) + max(y_values) - min(y_values))  # type: ignore[arg-type]
