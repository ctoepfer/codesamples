# SPDX-License-Identifier: Apache-2.0
"""Optional offline replay of measured gaze and EEG; no mental-state overlays."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from bisect import bisect_right
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from packscope.analysis.fixations import detect_fixations
from packscope.analysis.quality import EegQualityConfig, assess_eeg_quality
from packscope.models import ArtifactPath, EegFrame, GazeSample, MetricReason, MetricResult, MetricStatus


class _MissingDependency(Exception):
    pass


def _unavailable(name: str, reason: MetricReason, message: str) -> MetricResult[str]:
    return MetricResult(name, MetricStatus.UNAVAILABLE, None, reason, {"message": message})


def _plotting(output: Path, fps: int) -> tuple[Any, Any, Any]:
    """Load plotting only on demand and use Agg without altering the user's backend."""
    try:
        from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        if output.suffix.lower() == ".gif":
            from PIL import Image  # noqa: F401

            writer = PillowWriter(fps=fps)
        else:
            if not FFMpegWriter.isAvailable():
                raise _MissingDependency("Install the external ffmpeg executable for MP4 export, or choose GIF.")
            writer = FFMpegWriter(fps=fps, codec="libx264")
        figure = Figure(figsize=(6, 5), dpi=80)
        FigureCanvasAgg(figure)
        return figure, FuncAnimation, writer
    except (ImportError, OSError) as error:
        raise _MissingDependency("Install reporting libraries with: pip install 'packscope[reporting]'.") from error


def _save(animation: Any, writer: Any, output: Path) -> None:
    """Replace the destination only after successful rendering; clean partial exports."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=output.suffix, delete=False) as stream:
            temporary_path = Path(stream.name)
        animation.save(str(temporary_path), writer=writer)
        os.replace(temporary_path, output)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _valid_gaze(sample: GazeSample) -> bool:
    return (
        sample.valid
        and bool(sample.calibration_id)
        and not sample.quality_flags
        and sample.x_norm is not None
        and sample.y_norm is not None
        and 0 <= sample.x_norm <= 1
        and 0 <= sample.y_norm <= 1
    )


def _gaze_timeline(samples: list[GazeSample], fps: int) -> tuple[list[float], list[list[GazeSample]]]:
    """Hold actual observations for at most 100 ms; never interpolate through missing data."""
    timestamps = [s.timestamp_monotonic_s for s in samples]
    start, end = timestamps[0], timestamps[-1]
    count = max(1, math.ceil((end - start) * fps) + 1)
    # GIF writers buffer frames: refuse accidental multi-hour recordings.
    if count > 10000:
        raise ValueError("Export at most 10,000 frames per animation; split long recordings.")
    times = [min(end, start + i / fps) for i in range(count)]
    runs = []
    for time in times:
        index = bisect_right(timestamps, time) - 1
        trail = []
        if index >= 0 and time - timestamps[index] <= 0.1 + 1e-9:
            while index >= 0 and time - timestamps[index] <= 0.75:
                sample = samples[index]
                if not _valid_gaze(sample):
                    break
                if trail and trail[-1].timestamp_monotonic_s - sample.timestamp_monotonic_s > 0.1 + 1e-9:
                    break
                trail.append(sample)
                index -= 1
        runs.append(list(reversed(trail)))
    return times, runs


def render_gaze_scanpath_animation(
    gaze_samples: list[GazeSample],
    background_image_path: str | None = None,
    output_path: str = "scanpath.gif",
    fps: int = 10,
) -> MetricResult[str]:
    """Export a timestamp-paced GIF/MP4 of calibrated gaze in top-left coordinates.

    Invalid, flagged and uncalibrated samples break trails. Rings show elapsed time
    within I-DT fixations (0.05 dispersion, 0.1 s duration/gap), not interest or liking.
    A supplied background must be the exact displayed stimulus and viewport crop.
    """
    name = "gaze_scanpath_animation"
    figure = None
    try:
        output = Path(output_path)
        if type(fps) is not int or not 1 <= fps <= 100 or output.suffix.lower() not in (".gif", ".mp4"):
            return _unavailable(
                name, MetricReason.INVALID_ANIMATION_INPUT, "Use GIF/MP4 and integer fps from 1 to 100."
            )
        samples = list(gaze_samples)
        if not samples:
            return _unavailable(name, MetricReason.NO_VALID_SAMPLES, "No gaze samples supplied.")
        samples = [replace(s) for s in samples]  # Revalidate the public contracts.
        if any(b.timestamp_monotonic_s <= a.timestamp_monotonic_s for a, b in zip(samples, samples[1:], strict=False)):
            return _unavailable(name, MetricReason.ANIMATION_QUALITY_FAILED, "Gaze timestamps must strictly increase.")
        valid_count = sum(_valid_gaze(s) for s in samples)
        if not valid_count:
            return _unavailable(name, MetricReason.NO_VALID_SAMPLES, "No valid calibrated, unflagged gaze samples.")
        cleaned = [s if _valid_gaze(s) else replace(s, valid=False, x_norm=None, y_norm=None) for s in samples]
        fixations = detect_fixations(cleaned)
        times, trails = _gaze_timeline(cleaned, fps)
        if not any(trails):
            return _unavailable(
                name, MetricReason.NO_VALID_SAMPLES, "No valid observations at playback times; increase fps."
            )
        figure, animation_class, writer = _plotting(output, fps)
        axis = figure.subplots()
        figure.subplots_adjust(bottom=0.17)
        aspect = 1.0
        if background_image_path is not None:
            try:
                from PIL import Image
            except ImportError as error:
                raise _MissingDependency(
                    "Install Pillow with packscope[reporting] to load a stimulus image."
                ) from error
            with Image.open(background_image_path) as opened:
                aspect = opened.height / opened.width
                axis.imshow(np.asarray(opened.convert("RGB")), extent=(0, 1, 1, 0), origin="upper")
        axis.set(xlim=(0, 1), ylim=(1, 0), xlabel="Normalized x", ylabel="Normalized y")
        axis.set_aspect(aspect)
        from matplotlib.patches import Circle, FancyArrowPatch

        (line,) = axis.plot([], [], color="#21918c", linewidth=2, alpha=0.7)
        (point,) = axis.plot([], [], "o", color="#440154", markersize=6)
        arrow = FancyArrowPatch((0, 0), (0, 0), arrowstyle="->", mutation_scale=14, color="#440154")
        ring = Circle((0, 0), 0.01, fill=False, edgecolor="#21918c", linewidth=2)
        axis.add_patch(arrow)
        axis.add_patch(ring)
        figure.text(0.5, 0.01, "Gaze order and fixation duration only • gaps remain blank", ha="center", fontsize=8)

        def update(index: int) -> tuple[Any, ...]:
            time, trail = times[index], trails[index]
            line.set_data([s.x_norm for s in trail], [s.y_norm for s in trail])
            point.set_data([trail[-1].x_norm] if trail else [], [trail[-1].y_norm] if trail else [])
            arrow.set_visible(len(trail) >= 2)
            if len(trail) >= 2:
                arrow.set_positions((trail[-2].x_norm, trail[-2].y_norm), (trail[-1].x_norm, trail[-1].y_norm))
            fixation = next((f for f in fixations if f.start_time_s <= time <= f.end_time_s), None)
            ring.set_visible(bool(trail) and fixation is not None)
            if fixation is not None:
                ring.center = (fixation.x_norm, fixation.y_norm)
                ring.set_radius(0.01 + 0.03 * min(time - fixation.start_time_s, 2))
            axis.set_title(f"Gaze replay • {time - times[0]:.2f} s" + ("" if trail else " • no valid sample"))
            return line, point, arrow, ring

        animation = animation_class(figure, update, frames=len(times), interval=1000 / fps, blit=False)
        _save(animation, writer, output)
        return MetricResult(
            name,
            MetricStatus.AVAILABLE,
            ArtifactPath(str(output)),
            details={
                "sample_count": len(samples),
                "rejected_samples": len(samples) - valid_count,
                "animation_frames": len(times),
                "fps": fps,
                "fixation_count": len(fixations),
            },
        )
    except _MissingDependency as error:
        return _unavailable(name, MetricReason.MISSING_DEPENDENCY, str(error))
    except (OSError, ValueError, TypeError, OverflowError, RuntimeError, subprocess.SubprocessError) as error:
        return _unavailable(name, MetricReason.ANIMATION_RENDER_FAILED, str(error))
    finally:
        if figure is not None:
            figure.clear()


def render_eeg_psd_waterfall_animation(
    eeg_frames: list[EegFrame],
    window_size_sec: float = 1.0,
    output_path: str = "eeg_psd.gif",
) -> MetricResult[str]:
    """Replay per-channel Welch PSD curves over full, non-overlapping windows.

    The default is one second per window; no windows cross frame boundaries or gaps.
    All input frames and complete windows must pass quality gates. Partial tails are
    rejected explicitly. Playback advances one window/second, with acquisition times
    labelled; it is offline review, not a live acquisition display. No powers are
    fabricated above Nyquist and no unnamed channels are assigned electrode labels.
    """
    name = "eeg_psd_animation"
    figure = None
    try:
        output = Path(output_path)
        if (
            type(window_size_sec) not in (int, float)
            or not math.isfinite(window_size_sec)
            or window_size_sec <= 0
            or output.suffix.lower() not in (".gif", ".mp4")
        ):
            return _unavailable(name, MetricReason.INVALID_ANIMATION_INPUT, "Use GIF/MP4 and a positive finite window.")
        if not eeg_frames:
            return _unavailable(name, MetricReason.NO_VALID_SAMPLES, "No EEG frames supplied.")
        from scipy.signal import welch

        spectra = []
        previous_end = None
        channels = eeg_frames[0].channel_names
        units = eeg_frames[0].metadata.get("units", "device units (unspecified)")
        config = EegQualityConfig(min_duration_s=window_size_sec)
        for original in eeg_frames:
            frame = replace(original)
            if (
                frame.channel_names != channels
                or len(set(channels)) != len(channels)
                or any(not isinstance(channel, str) or not channel.strip() for channel in channels)
                or frame.metadata.get("units", "device units (unspecified)") != units
                or frame.device_id != eeg_frames[0].device_id
                or frame.source != eeg_frames[0].source
                or (previous_end is not None and frame.start_time_s <= previous_end)
            ):
                return _unavailable(
                    name,
                    MetricReason.ANIMATION_QUALITY_FAILED,
                    "Require ordered non-overlapping frames with consistent channels, device and units.",
                )
            previous_end = frame.end_time_s
            size = int(round(window_size_sec * frame.sampling_rate_hz))
            if size < 8 or frame.sampling_rate_hz < 100:
                return _unavailable(
                    name,
                    MetricReason.ANIMATION_QUALITY_FAILED,
                    "At least eight samples/window and sampling rate >=100 Hz are required for 0–50 Hz.",
                )
            report = assess_eeg_quality(frame, config)
            if not report.passed or frame.samples.shape[1] % size:
                return _unavailable(
                    name,
                    MetricReason.ANIMATION_QUALITY_FAILED,
                    "EEG quality failed or incomplete final window: " + ", ".join(report.flags),
                )
            for start in range(0, frame.samples.shape[1], size):
                window = replace(
                    frame,
                    samples=frame.samples[:, start : start + size],
                    timestamps_monotonic_s=frame.timestamps_monotonic_s[start : start + size],
                )
                report = assess_eeg_quality(window, replace(config, min_duration_s=size / frame.sampling_rate_hz))
                if not report.passed:
                    return _unavailable(name, MetricReason.ANIMATION_QUALITY_FAILED, ", ".join(report.flags))
                with np.errstate(over="ignore", invalid="ignore"):
                    frequencies, density = welch(window.samples, fs=frame.sampling_rate_hz, nperseg=size, axis=1)
                mask = frequencies <= 50
                if not np.all(np.isfinite(density)) or np.any(density < 0):
                    return _unavailable(
                        name, MetricReason.ANIMATION_QUALITY_FAILED, "PSD must be finite and non-negative."
                    )
                spectra.append((window.start_time_s, window.end_time_s, frequencies[mask], density[:, mask]))
                if len(spectra) > 10000:
                    return _unavailable(
                        name, MetricReason.INVALID_ANIMATION_INPUT, "Split exports into <=10,000 windows."
                    )
        figure, animation_class, writer = _plotting(output, 1)
        axis = figure.subplots()
        figure.subplots_adjust(bottom=0.17)
        from matplotlib import colormaps

        lines = [
            axis.plot([], [], label=channel, color=colormaps["viridis"](0.12 + 0.63 * i / max(1, len(channels) - 1)))[0]
            for i, channel in enumerate(channels)
        ]
        maximum = max(float(density.max()) for _, _, _, density in spectra)
        if maximum <= 0:
            return _unavailable(name, MetricReason.ANIMATION_QUALITY_FAILED, "No positive PSD in the displayed range.")
        axis.set(xlim=(0, 50), ylim=(0, maximum), xlabel="Frequency (Hz)", ylabel=f"PSD ({units}²/Hz)")
        axis.legend()
        figure.text(
            0.5,
            0.01,
            "Measured spectra • one window per playback second • no mental-state labels",
            ha="center",
            fontsize=8,
        )

        def update(index: int) -> tuple[Any, ...]:
            start, end, frequencies, density = spectra[index]
            for line, power in zip(lines, density, strict=True):
                line.set_data(frequencies, power)
            axis.set_title(f"EEG PSD • acquisition {start:.2f}–{end:.2f} s")
            return tuple(lines)

        animation = animation_class(figure, update, frames=len(spectra), interval=1000, blit=False)
        _save(animation, writer, output)
        return MetricResult(
            name,
            MetricStatus.AVAILABLE,
            ArtifactPath(str(output)),
            details={
                "window_count": len(spectra),
                "window_size_sec": window_size_sec,
                "playback_windows_per_second": 1,
            },
        )
    except _MissingDependency as error:
        return _unavailable(name, MetricReason.MISSING_DEPENDENCY, str(error))
    except (OSError, ValueError, TypeError, OverflowError, RuntimeError, subprocess.SubprocessError) as error:
        return _unavailable(name, MetricReason.ANIMATION_RENDER_FAILED, str(error))
    finally:
        if figure is not None:
            figure.clear()
