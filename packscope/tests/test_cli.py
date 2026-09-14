# SPDX-License-Identifier: Apache-2.0
"""Offline CLI behavior and graceful failures."""

import builtins
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from packscope.cli import main
from packscope.io.serialization import ExportMetadata, write_json
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
