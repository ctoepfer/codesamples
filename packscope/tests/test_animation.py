# SPDX-License-Identifier: Apache-2.0
"""Offline animation exports, scientific display contracts and optional dependencies."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from packscope.cli import main
from packscope.io.serialization import ExportMetadata, dumps, loads
from packscope.models import ArtifactPath, GazeSample, MetricReason, MetricResult, MetricStatus
from packscope.reporting.animation import (
    _gaze_timeline,
    render_eeg_psd_waterfall_animation,
    render_gaze_scanpath_animation,
)
from packscope.testing.synthetic import generate_eeg_frames, generate_gaze_samples


def gaze() -> list[GazeSample]:
    return list(generate_gaze_samples(duration_s=0.4, sampling_rate_hz=20))


@pytest.mark.parametrize("module", ["matplotlib", "PIL"])
def test_missing_dependency(module: str, tmp_path: Path) -> None:
    script = """
import sys
sys.modules[sys.argv[1]] = None
from packscope.reporting.animation import render_gaze_scanpath_animation
from packscope.testing.synthetic import generate_gaze_samples
from packscope.models import MetricStatus, MetricReason
result = render_gaze_scanpath_animation(list(generate_gaze_samples(duration_s=.4)), output_path=sys.argv[2])
assert result.status == MetricStatus.UNAVAILABLE and result.value is None
assert result.reason == MetricReason.MISSING_DEPENDENCY, result
"""
    result = subprocess.run(
        [sys.executable, "-c", script, module, str(tmp_path / "test.gif")], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


def test_core_and_demo_without_reporting(tmp_path: Path) -> None:
    demo = Path(__file__).parents[1] / "examples" / "homebrew_label_tasting_demo.py"
    script = """
import sys, runpy
sys.modules["matplotlib"] = None
sys.modules["PIL"] = None
from packscope.testing.synthetic import generate_synthetic_sensory_ratings
assert len(generate_synthetic_sensory_ratings(session_count=1).ratings) == 2
sys.argv = [sys.argv[1], "--output-dir", sys.argv[2]]
runpy.run_path(sys.argv[0], run_name="__main__")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(demo), str(tmp_path)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "N=6" in result.stdout and "MISSING_DEPENDENCY" in result.stdout
    assert not list(tmp_path.iterdir())


def test_gaze_gates_and_timeline(tmp_path: Path) -> None:
    output = str(tmp_path / "test.gif")
    assert render_gaze_scanpath_animation([], output_path=output).reason == MetricReason.NO_VALID_SAMPLES
    invalid = [GazeSample(0, False)]
    assert render_gaze_scanpath_animation(invalid, output_path=output).value is None
    uncalibrated = [replace(s, calibration_id=None) for s in gaze()]
    assert render_gaze_scanpath_animation(uncalibrated, output_path=output).value is None
    assert (
        render_gaze_scanpath_animation(gaze()[::-1], output_path=output).reason == MetricReason.ANIMATION_QUALITY_FAILED
    )
    assert (
        render_gaze_scanpath_animation(gaze(), output_path=output, fps=0).reason == MetricReason.INVALID_ANIMATION_INPUT
    )
    samples = [
        GazeSample(0, True, 0.1, 0.2, calibration_id="c"),
        GazeSample(0.1, False),
        GazeSample(0.2, True, 0.8, 0.9, calibration_id="c"),
        GazeSample(1, True, 0.3, 0.4, calibration_id="c"),
    ]
    times, trails = _gaze_timeline(samples, 10)
    assert len(times) == 11  # one elapsed second, including blank dropout frames
    assert trails[1] == [] and trails[5] == []
    assert trails[2] == [samples[2]]  # no arrow from before the dropout
    assert trails[-1] == [samples[-1]]
    assert not list(tmp_path.iterdir())


def test_gaze_gif_and_path_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    image = pytest.importorskip("PIL.Image")
    background = tmp_path / "stimulus.png"
    image.new("RGB", (160, 240), "white").save(background)
    output = tmp_path / "scanpath.gif"
    result = render_gaze_scanpath_animation(gaze(), str(background), str(output))
    assert result.status == MetricStatus.AVAILABLE and isinstance(result.value, str)
    with image.open(output) as opened:
        assert opened.format == "GIF" and opened.n_frames > 1
        assert opened.info["duration"] == 100
    restored = loads(dumps(result, ExportMetadata("a" * 64, "0.1.0", (), "c", ())))
    assert restored == result and isinstance(restored.value, ArtifactPath)
    with pytest.raises(ValueError):
        MetricResult("score", MetricStatus.AVAILABLE, "not a numeric score")


def test_eeg_quality_gates(tmp_path: Path) -> None:
    path = str(tmp_path / "eeg.gif")
    frame = next(generate_eeg_frames(duration_s=2))
    cases = [
        [],
        [replace(frame, quality_flags=("bad_contact",))],
        [replace(frame, samples=np.zeros_like(frame.samples))],
        [next(generate_eeg_frames(duration_s=1.5))],
        [frame, frame],
        [next(generate_eeg_frames(duration_s=2, sampling_rate_hz=60))],
    ]
    for frames in cases:
        result = render_eeg_psd_waterfall_animation(frames, output_path=path)
        assert result.status == MetricStatus.UNAVAILABLE and result.value is None
    assert render_eeg_psd_waterfall_animation([frame], window_size_sec=float("nan")).reason == (
        MetricReason.INVALID_ANIMATION_INPUT
    )
    assert not list(tmp_path.iterdir())


def test_eeg_gif_and_measured_spectral_peaks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("matplotlib")
    image = pytest.importorskip("PIL.Image")
    from packscope.reporting import animation as module

    original = module._save
    peaks = []

    def inspect_and_save(animation: object, writer: object, output: Path) -> None:
        lines = animation._func(0)
        peaks.extend(float(line.get_xdata()[np.argmax(line.get_ydata())]) for line in lines)
        assert animation._fig.axes[0].get_xlim() == (0, 50)
        original(animation, writer, output)

    monkeypatch.setattr(module, "_save", inspect_and_save)
    output = tmp_path / "eeg.gif"
    result = render_eeg_psd_waterfall_animation(list(generate_eeg_frames(duration_s=2)), output_path=str(output))
    assert result.status == MetricStatus.AVAILABLE
    assert peaks == [10, 10]  # Measured injected alpha peak in each explicitly named channel.
    with image.open(output) as opened:
        assert opened.n_frames == 2 and opened.info["duration"] == 1000


def test_missing_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    animation = pytest.importorskip("matplotlib.animation")
    monkeypatch.setattr(animation.FFMpegWriter, "isAvailable", classmethod(lambda cls: False))
    result = render_gaze_scanpath_animation(gaze(), output_path=str(tmp_path / "scanpath.mp4"))
    assert result.reason == MetricReason.MISSING_DEPENDENCY
    assert "ffmpeg" in result.details["message"] and not list(tmp_path.iterdir())


def test_atomic_render_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("PIL")
    output = tmp_path / "scanpath.gif"
    output.write_bytes(b"original")

    def fail(*args: object) -> None:
        raise OSError("replace blocked for test")

    monkeypatch.setattr("packscope.reporting.animation.os.replace", fail)
    result = render_gaze_scanpath_animation(gaze(), output_path=str(output))
    assert result.reason == MetricReason.ANIMATION_RENDER_FAILED
    assert output.read_bytes() == b"original" and list(tmp_path.iterdir()) == [output]


def test_cli_scanpath(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from dataclasses import asdict

    pytest.importorskip("matplotlib")
    pytest.importorskip("PIL")
    path = tmp_path / "gaze.json"
    path.write_text(json.dumps([asdict(s) for s in gaze()]))
    output = tmp_path / "cli.gif"
    assert main(["animate-scanpath", "--gaze-file", str(path), "--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "available"
    path.write_text("[]")
    assert main(["animate-scanpath", "--gaze-file", str(path), "--output", str(output)]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "NO_VALID_SAMPLES"
