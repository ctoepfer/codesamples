# SPDX-License-Identifier: Apache-2.0
"""Deterministic synthetic signals; these are fixtures, never participant measurements."""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence

import numpy as np

from packscope.errors import ConfigurationError
from packscope.models import EegFrame, GazeSample


def generate_eeg_frames(
    *,
    duration_s: float = 8.0,
    sampling_rate_hz: float = 250.0,
    noise_amplitude: float = 0.05,
    alpha_amplitudes: tuple[float, ...] = (1.0, 2.0),
    beta_amplitude: float = 0.5,
    channel_names: tuple[str, ...] = ("F3", "F4"),
    frame_duration_s: float = 4.0,
    seed: int = 0,
) -> Iterator[EegFrame]:
    """Yield non-overlapping blocks with 10 Hz alpha and 20 Hz beta in synthetic units.

    Labels describe the explicitly simulated channels, not inferred device locations.
    The final partial block is retained so quality gates can reject short windows.
    """
    positive = (duration_s, sampling_rate_hz, frame_duration_s)
    amplitudes = (noise_amplitude, beta_amplitude, *alpha_amplitudes)
    if any(not math.isfinite(v) or v <= 0 for v in positive):
        raise ConfigurationError("Durations and sampling rate must be positive and finite.")
    if any(not math.isfinite(v) or v < 0 for v in amplitudes):
        raise ConfigurationError("Amplitudes must be finite and non-negative.")
    if not channel_names or len(channel_names) != len(alpha_amplitudes):
        raise ConfigurationError("Supply one alpha amplitude per explicit channel label.")
    if len(set(n.upper() for n in channel_names)) != len(channel_names) or any(not n.strip() for n in channel_names):
        raise ConfigurationError("Channel labels must be non-empty and unique.")
    if sampling_rate_hz <= 40:
        raise ConfigurationError("Sampling rate must exceed twice the injected 20 Hz frequency.")
    count, block = int(duration_s * sampling_rate_hz), int(frame_duration_s * sampling_rate_hz)
    if min(count, block) < 1:
        raise ConfigurationError("Durations must contain at least one sample.")
    rng = np.random.default_rng(seed)
    for start in range(0, count, block):
        times = np.arange(start, min(count, start + block), dtype=float) / sampling_rate_hz
        signals = np.array([a * np.sin(2 * np.pi * 10 * times) for a in alpha_amplitudes])
        signals += beta_amplitude * np.sin(2 * np.pi * 20 * times)
        signals += rng.normal(0, noise_amplitude, signals.shape)
        yield EegFrame(
            signals,
            times,
            channel_names,
            sampling_rate_hz,
            "synthetic",
            "synthetic-eeg",
            metadata={"synthetic": True, "units": "synthetic", "seed": seed},
        )


def generate_gaze_samples(
    coordinates: Sequence[tuple[float, float]] = ((0.25, 0.5), (0.75, 0.5)),
    *,
    duration_s: float = 8.0,
    sampling_rate_hz: float = 60.0,
    fixation_duration_s: float = 0.8,
    saccade_duration_s: float = 0.1,
) -> Iterator[GazeSample]:
    """Cycle through normalized fixation targets with linear inter-target saccades."""
    if not coordinates or any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in coordinates):
        raise ConfigurationError("Provide normalized fixation coordinates in [0, 1].")
    if any(
        not math.isfinite(v) or v <= 0 for v in (duration_s, sampling_rate_hz, fixation_duration_s, saccade_duration_s)
    ):
        raise ConfigurationError("Gaze durations and rate must be positive and finite.")
    period = fixation_duration_s + saccade_duration_s
    for index in range(int(duration_s * sampling_rate_hz)):
        timestamp = index / sampling_rate_hz
        cycle = int(timestamp / period)
        phase = timestamp - cycle * period
        x, y = coordinates[cycle % len(coordinates)]
        if phase > fixation_duration_s:
            nx, ny = coordinates[(cycle + 1) % len(coordinates)]
            fraction = (phase - fixation_duration_s) / saccade_duration_s
            x, y = x + fraction * (nx - x), y + fraction * (ny - y)
        yield GazeSample(timestamp, True, x, y, 1.0, "synthetic", "synthetic-calibration")
