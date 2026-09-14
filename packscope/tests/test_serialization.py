# SPDX-License-Identifier: Apache-2.0
"""Stable serialization and provenance validation across public contracts."""

import json
from pathlib import Path

import numpy as np
import pytest

from packscope.errors import ConfigurationError
from packscope.io.serialization import ExportMetadata, dumps, loads, read_json, to_dict, write_json
from packscope.models import GazeSample, MetricResult, MetricStatus
from packscope.privacy import ConsentScope, SessionConsent, SessionManifest
from packscope.testing.synthetic import generate_eeg_frames


def manifest() -> SessionManifest:
    return SessionManifest(
        "session",
        "stimulus",
        "a" * 64,
        SessionConsent.create("P1", "v1", [ConsentScope.DERIVED_METRICS]),
        "0.1.0",
        "2026-01-01T00:00:00Z",
    )


def metadata(calibration_id: str | None = None) -> ExportMetadata:
    return ExportMetadata("a" * 64, "0.1.0", (), calibration_id, ("derived_metrics",))


def test_round_trips(tmp_path: Path) -> None:
    objects = [
        next(generate_eeg_frames()),
        GazeSample(0, False),
        MetricResult("alpha", MetricStatus.AVAILABLE, 1),
        manifest(),
    ]
    for index, value in enumerate(objects):
        text = dumps(value, metadata())
        assert dumps(loads(text), metadata()) == text
        path = tmp_path / f"{index}.json"
        write_json(path, value, metadata())
        assert dumps(read_json(path), metadata()) == text
    np.testing.assert_array_equal(loads(dumps(objects[0], metadata())).samples, objects[0].samples)


@pytest.mark.parametrize(
    "key", ["stimulus_hash", "software_version", "quality_flags", "calibration_id", "consent_scopes"]
)
def test_mandatory_metadata(key: str) -> None:
    payload = to_dict(manifest(), metadata())
    del payload["metadata"][key]
    with pytest.raises(ConfigurationError):
        loads(json.dumps(payload))


def test_invalid_data_and_provenance() -> None:
    payload = to_dict(manifest(), metadata())
    payload["metadata"]["consent_scopes"] = ["eeg_raw"]
    with pytest.raises(ConfigurationError, match="provenance"):
        loads(json.dumps(payload))
    with pytest.raises(ConfigurationError, match="calibration"):
        dumps(GazeSample(0, True, 0.2, 0.3, calibration_id="cal1"), metadata())
    with pytest.raises(ConfigurationError, match="quality flags"):
        dumps(GazeSample(0, False, quality_flags=("dropout",)), metadata())
    with pytest.raises(ConfigurationError):
        loads('{"value": NaN}')
    with pytest.raises(ConfigurationError):
        loads("null")
    with pytest.raises(ConfigurationError):
        loads('{"schema_version": 2}')


def test_atomic_failure_preserves_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "session.json"
    path.write_text("original")

    def fail_replace(*args: object) -> None:
        raise OSError("replacement failed")

    monkeypatch.setattr("packscope.privacy.os.replace", fail_replace)
    with pytest.raises(OSError):
        write_json(path, manifest(), metadata())
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("timestamp", ["yesterday", "2026-01-01", "2026-01-01T00:00:00+01:00"])
def test_manifest_timestamps_are_utc(timestamp: str) -> None:
    from dataclasses import replace

    with pytest.raises(ConfigurationError):
        dumps(replace(manifest(), created_at_utc=timestamp), metadata())


def test_numeric_overflow_and_boolean_schema_version() -> None:
    text = dumps(MetricResult("alpha", MetricStatus.AVAILABLE, 1.5), metadata())
    with pytest.raises(ConfigurationError):
        loads(text.replace('"value": 1.5', '"value": 1e999'))
    with pytest.raises(ConfigurationError):
        loads(text.replace('"schema_version": 1', '"schema_version": true'))
