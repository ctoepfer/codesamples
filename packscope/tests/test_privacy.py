# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json

import pytest

from packscope.errors import ConfigurationError
from packscope.privacy import ConsentScope, SessionConsent, SessionManifest


def test_manifest_writes_only_pseudonymous_consent_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    consent = SessionConsent.create("P-001", "consent-v1", [ConsentScope.GAZE_COORDINATES])
    manifest = SessionManifest("S-001", "can-v1", "a" * 64, consent, "0.1.0", "2026-01-01T00:00:00+00:00")
    destination = tmp_path / "manifest.json"

    manifest.write_json(destination)

    payload = json.loads(destination.read_text())
    assert payload["consent"]["participant_code"] == "P-001"
    assert payload["consent"]["granted_scopes"] == ["gaze_coordinates"]


def test_consent_blocks_ungranted_capture_scope() -> None:
    consent = SessionConsent.create("P-001", "v1", [ConsentScope.DERIVED_METRICS])

    with pytest.raises(ConfigurationError, match="camera_video"):
        consent.requires(ConsentScope.CAMERA_VIDEO)
