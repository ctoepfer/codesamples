# SPDX-License-Identifier: Apache-2.0
"""Offline CLI behavior and graceful failures."""

import builtins
import json
import os
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

import pytest

from packscope.cli import main
from packscope.io.serialization import ExportMetadata, write_json
from packscope.models import ArtifactPath, MetricReason, MetricResult, MetricStatus
from packscope.testing.synthetic import generate_eeg_frames


def eeg_path(tmp_path: Path) -> Path:
    path = tmp_path / "eeg.json"
    write_json(path, next(generate_eeg_frames()), ExportMetadata("a" * 64, "0.1.0", (), None, ("eeg_raw",)))
    return path


def test_quality_and_faa(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = eeg_path(tmp_path)
    assert main(["compute-faa", str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result[0]["result"]["status"] == "available"
    assert main(["run-quality-gates", str(path), "--max-absolute-amplitude", ".1"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["rejection_ratio"] == 1
    assert result["accepted_window_indices"] == []


def test_csv_and_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "raw.csv"
    frame = next(generate_eeg_frames(channel_names=("FP1",), alpha_amplitudes=(1,)))
    path.write_text(
        "timestamp_monotonic_s,FP1\n"
        + "".join(f"{t},{v}\n" for t, v in zip(frame.timestamps_monotonic_s, frame.samples[0], strict=True))
    )
    assert main(["compute-faa", str(path)]) == 2
    assert "sampling-rate" in capsys.readouterr().err
    assert main(["compute-faa", str(path), "--sampling-rate-hz", "250"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["result"]["status"] == "insufficient_channels"
    path.write_text("timestamp_monotonic_s,FP1\n0,NaN\n")
    assert main(["run-quality-gates", str(path), "--sampling-rate-hz", "250"]) == 2
    assert "NaN" in capsys.readouterr().err
    assert main(["compute-faa", str(tmp_path / "missing.json")]) == 2


def test_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from packscope.privacy import SessionConsent, SessionManifest

    manifest = SessionManifest(
        "s", "stim", "a" * 64, SessionConsent.create("p", "v1", []), "0.1.0", "2026-01-01T00:00:00Z"
    )
    path = tmp_path / "manifest.json"
    manifest.write_json(path)
    assert main(["validate-manifest", str(path)]) == 0
    payload = json.loads(path.read_text())
    del payload["consent_scopes"]
    path.write_text(json.dumps(payload))
    assert main(["validate-manifest", str(path)]) == 2
    assert "consent_scopes" in capsys.readouterr().err


def test_doctor_without_numeric_dependencies() -> None:
    script = """
import sys
sys.modules["numpy"] = None
sys.modules["scipy"] = None
from packscope.cli import main
assert main(["doctor"]) == 0
assert main(["generate-heatmap", "missing.json", "--output", "unused.png"]) == 2
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=os.environ.copy())
    assert result.returncode == 0, result.stderr
    assert "reporting" in result.stdout
    assert "Optional dependency" in result.stderr


def test_missing_matplotlib(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    original = builtins.__import__

    def guarded(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("matplotlib"):
            raise ImportError("blocked for test")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert main(["generate-heatmap", "unused.json", "--output", "unused.png"]) == 2
    assert "packscope[reporting]" in capsys.readouterr().err


# ============================================================================
# Tests for `packscope doctor`
# ============================================================================


def test_cli_doctor_all_extras_installed(capsys: pytest.CaptureFixture[str]) -> None:
    """Test `packscope doctor` output when optional extras are importable."""
    with patch("packscope.cli.main.importlib.util.find_spec", return_value=object()):
        exit_code = main(["doctor"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "runtime/device readiness is not tested" in captured.out
    assert "brainflow | available" in captured.out
    assert "reporting | available" in captured.out


def test_cli_doctor_missing_extras(capsys: pytest.CaptureFixture[str]) -> None:
    """Test installed-module diagnostics without connecting to any hardware."""

    def installed(name: str) -> object | None:
        return None if name in {"brainflow", "serial"} else object()

    with patch("packscope.cli.main.importlib.util.find_spec", side_effect=installed):
        exit_code = main(["doctor"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "brainflow | missing: brainflow" in captured.out
    assert "lsl | available" in captured.out


# ============================================================================
# Tests for `packscope run-quality-gates`
# ============================================================================


@pytest.fixture
def temp_eeg_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file containing synthetic raw EEG frame dicts."""
    frames = list(generate_eeg_frames(duration_s=12))
    frames[1] = replace(frames[1], quality_flags=("AMPLITUDE_SATURATION",))
    eeg_data = []
    for frame in frames:
        payload = asdict(frame)
        payload["samples"] = frame.samples.tolist()
        payload["timestamps_monotonic_s"] = frame.timestamps_monotonic_s.tolist()
        eeg_data.append(payload)
    file_path = tmp_path / "raw_eeg.json"
    file_path.write_text(json.dumps(eeg_data))
    return file_path


def test_cli_run_quality_gates_success(temp_eeg_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Read real raw-frame JSON and retain rejection accounting."""
    assert main(["run-quality-gates", str(temp_eeg_file)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["window_count"] == 3
    assert summary["accepted_window_indices"] == [0, 2]
    assert summary["rejection_ratio"] == pytest.approx(1 / 3)
    assert summary["windows"][1]["flags"] == ["AMPLITUDE_SATURATION"]


def test_cli_run_quality_gates_failed_quality(temp_eeg_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A successful report can describe a recording with every window rejected."""
    assert main(["run-quality-gates", str(temp_eeg_file), "--max-absolute-amplitude", ".01"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["rejection_ratio"] == 1
    assert summary["accepted_window_indices"] == []
    assert all("amplitude_exceeds_limit" in window["flags"] for window in summary["windows"])


def test_cli_run_quality_gates_invalid_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing input returns a nonzero status and an actionable error."""
    assert main(["run-quality-gates", str(tmp_path / "missing.json")]) == 2
    assert "Cannot read JSON log" in capsys.readouterr().err


@pytest.fixture
def temp_gaze_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file containing synthetic gaze sample dicts."""
    gaze_data = [
        {"timestamp_monotonic_s": 0.0, "valid": True, "x_norm": 0.2, "y_norm": 0.3, "confidence": 1.0},
        {"timestamp_monotonic_s": 0.1, "valid": True, "x_norm": 0.25, "y_norm": 0.32, "confidence": 1.0},
        {"timestamp_monotonic_s": 0.2, "valid": False, "x_norm": None, "y_norm": None, "confidence": 0.0},
        {"timestamp_monotonic_s": 0.3, "valid": True, "x_norm": 0.8, "y_norm": 0.1, "confidence": 1.0},
    ]
    for sample in gaze_data:
        sample["calibration_id"] = "test-calibration-v1"
    file_path = tmp_path / "gaze_samples.json"
    file_path.write_text(json.dumps(gaze_data))
    return file_path


def test_cli_animate_scanpath_success(temp_gaze_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test successful execution of the animate-scanpath CLI subcommand."""
    output_gif = tmp_path / "output_scanpath.gif"
    stimulus = tmp_path / "label-v1.png"
    mock_result = MetricResult("scanpath", MetricStatus.AVAILABLE, ArtifactPath(str(output_gif)))

    with patch("packscope.reporting.animation.render_gaze_scanpath_animation", return_value=mock_result) as mock_render:
        exit_code = main(
            [
                "animate-scanpath",
                "--gaze-file",
                str(temp_gaze_file),
                "--stimulus",
                str(stimulus),
                "--output",
                str(output_gif),
                "--fps",
                "20",
            ]
        )

    assert exit_code == 0
    mock_render.assert_called_once()
    samples, background, destination, fps = mock_render.call_args.args
    assert (background, destination, fps) == (str(stimulus), str(output_gif), 20)
    assert len(samples) == 4 and not samples[2].valid
    assert samples[2].x_norm is None and samples[2].y_norm is None
    assert all(sample.calibration_id == "test-calibration-v1" for sample in samples)
    payload = json.loads(capsys.readouterr().out)
    assert payload["value"] == str(output_gif) and payload["status"] == "available"


def test_cli_animate_scanpath_missing_dependency(
    temp_gaze_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test animate-scanpath subcommand when optional reporting dependencies are missing."""
    output_gif = tmp_path / "output_scanpath.gif"
    mock_result = MetricResult(
        "scanpath",
        MetricStatus.UNAVAILABLE,
        None,
        MetricReason.MISSING_DEPENDENCY,
    )

    with patch("packscope.reporting.animation.render_gaze_scanpath_animation", return_value=mock_result):
        exit_code = main(["animate-scanpath", "--gaze-file", str(temp_gaze_file), "--output", str(output_gif)])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["reason"] == "MISSING_DEPENDENCY"


def test_cli_animate_scanpath_missing_gaze_file(tmp_path: Path) -> None:
    """Test animate-scanpath CLI behavior when the gaze input file does not exist."""
    non_existent_file = tmp_path / "does_not_exist.json"

    assert main(["animate-scanpath", "--gaze-file", str(non_existent_file), "--output", str(tmp_path / "out.gif")]) == 2


def test_heatmap(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    path = tmp_path / "gaze.json"
    path.write_text(
        json.dumps(
            [{"timestamp_monotonic_s": 0, "valid": True, "x_norm": 0.2, "y_norm": 0.3, "calibration_id": "cal1"}]
        )
    )
    output = tmp_path / "heatmap.png"
    assert main(["generate-heatmap", str(path), "--output", str(output)]) == 0
    assert output.read_bytes().startswith(b"\x89PNG")
