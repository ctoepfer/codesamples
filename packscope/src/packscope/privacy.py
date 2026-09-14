# SPDX-License-Identifier: Apache-2.0
"""Minimal consent and data-minimization contracts for local study software.

This module is not legal advice. It exists to make privacy-relevant choices explicit
in a session manifest instead of burying them in application defaults.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from packscope.errors import ConfigurationError


class ConsentScope(StrEnum):
    """Separately revocable data-collection permissions."""

    EEG_RAW = "eeg_raw"
    GAZE_COORDINATES = "gaze_coordinates"
    CAMERA_VIDEO = "camera_video"
    DERIVED_METRICS = "derived_metrics"
    AGGREGATED_EXPORT = "aggregated_export"


@dataclass(frozen=True, slots=True)
class SessionConsent:
    """An affirmative, documented consent record tied to one pseudonymous session."""

    participant_code: str
    document_version: str
    granted_scopes: frozenset[ConsentScope]
    consented_at_utc: str

    @classmethod
    def create(
        cls,
        participant_code: str,
        document_version: str,
        granted_scopes: Iterable[ConsentScope],
    ) -> SessionConsent:
        """Create a record without collecting a participant's direct identity."""
        if not participant_code.strip() or not document_version.strip():
            raise ConfigurationError("participant_code and document_version are required.")
        return cls(
            participant_code=participant_code,
            document_version=document_version,
            granted_scopes=frozenset(granted_scopes),
            consented_at_utc=datetime.now(UTC).isoformat(),
        )

    def requires(self, *scopes: ConsentScope) -> None:
        """Raise before a capture mode begins without corresponding consent."""
        missing = set(scopes).difference(self.granted_scopes)
        if missing:
            requested = ", ".join(sorted(scope.value for scope in missing))
            raise ConfigurationError(f"Missing affirmative consent for: {requested}.")


@dataclass(frozen=True, slots=True)
class SessionManifest:
    """Portable processing provenance for a single local study session."""

    session_id: str
    stimulus_id: str
    stimulus_sha256: str
    consent: SessionConsent
    software_version: str
    created_at_utc: str
    notes: str = ""

    def write_json(self, destination: Path) -> None:
        """Atomically persist the manifest to avoid partial provenance files."""
        if not self.session_id or not self.stimulus_id or not self.stimulus_sha256:
            raise ConfigurationError("session_id, stimulus_id, and stimulus_sha256 are required.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        payload["consent"]["granted_scopes"] = sorted(scope.value for scope in self.consent.granted_scopes)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=destination.parent) as temporary:
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, destination)
