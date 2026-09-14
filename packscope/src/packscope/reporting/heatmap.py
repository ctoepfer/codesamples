# SPDX-License-Identifier: Apache-2.0
"""Local gaze-density heatmap rendering for a labelled packaging stimulus."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from packscope.errors import OptionalDependencyError
from packscope.models import GazeSample


def render_gaze_heatmap(
    stimulus_path: Path,
    output_path: Path,
    samples: Sequence[GazeSample],
    *,
    sigma_px: float = 35.0,
    opacity: float = 0.58,
) -> int:
    """Overlay calibrated valid gaze density on an image and return plotted sample count.

    This visualizes gaze allocation only. Derived EEG metrics remain in their own
    time-windowed tables and must not be represented as causal color overlays.
    """
    if sigma_px <= 0.0 or not 0.0 < opacity <= 1.0:
        raise ValueError("sigma_px must be positive and opacity must be in (0, 1].")
    try:
        from PIL import Image
    except ImportError as error:
        raise OptionalDependencyError("Pillow", "reporting") from error

    with Image.open(stimulus_path) as opened:
        base = opened.convert("RGBA")
    width, height = base.size
    density = np.zeros((height, width), dtype=np.float64)
    radius = max(1, int(np.ceil(3.0 * sigma_px)))
    axis = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel_1d = np.exp(-0.5 * np.square(axis / sigma_px))
    kernel = np.outer(kernel_1d, kernel_1d)

    plotted = 0
    for sample in samples:
        if not sample.valid:
            continue
        x = int(round(sample.x_norm * (width - 1)))  # coordinates are present for valid samples
        y = int(round(sample.y_norm * (height - 1)))
        x_start, x_end = max(0, x - radius), min(width, x + radius + 1)
        y_start, y_end = max(0, y - radius), min(height, y + radius + 1)
        kx_start, kx_end = x_start - (x - radius), kernel.shape[1] - ((x + radius + 1) - x_end)
        ky_start, ky_end = y_start - (y - radius), kernel.shape[0] - ((y + radius + 1) - y_end)
        density[y_start:y_end, x_start:x_end] += kernel[ky_start:ky_end, kx_start:kx_end]
        plotted += 1

    if plotted == 0:
        raise ValueError("No valid gaze samples are available for heatmap rendering.")
    normalized = density / density.max()
    red = np.clip(255.0 * np.minimum(1.0, normalized * 2.0), 0, 255).astype(np.uint8)
    green = np.clip(255.0 * np.minimum(1.0, np.maximum(0.0, normalized * 2.0 - 1.0)), 0, 255).astype(np.uint8)
    alpha = (normalized * 255.0 * opacity).astype(np.uint8)
    rgba = np.dstack((red, green, np.zeros_like(red), alpha))
    overlay = Image.fromarray(rgba, mode="RGBA")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(base, overlay).save(output_path)
    return plotted
