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
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

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

    quality_flags: tuple[str, ...] = ()
    calibration_id: str | None = None

    def write_json(self, destination: Path) -> None:
        """Atomically persist provenance, preserving the original top-level schema."""
        from packscope.io.serialization import ExportMetadata, to_dict

        metadata = ExportMetadata(self.stimulus_sha256, self.software_version, self.quality_flags,
                                  self.calibration_id, tuple(sorted(s.value for s in self.consent.granted_scopes)))
        envelope = to_dict(self, metadata)
        payload = envelope["data"] | envelope["metadata"] | {"schema_version": 1}
        atomic_write_json(destination, payload)


def atomic_write_json(destination: Path, payload: Any) -> None:
    """Validate JSON before writing and clean temporary files if replacement fails."""
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=destination.parent) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
