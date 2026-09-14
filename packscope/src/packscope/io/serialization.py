# SPDX-License-Identifier: Apache-2.0
"""Version-one JSON envelopes with mandatory, explicit provenance metadata."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from packscope.errors import ConfigurationError
from packscope.models import EegFrame, GazeSample, MetricResult, MetricStatus
from packscope.privacy import ConsentScope, SessionConsent, SessionManifest, atomic_write_json


@dataclass(frozen=True, slots=True)
class ExportMetadata:
    """Required provenance; null calibration explicitly means no calibration applies."""

    stimulus_hash: str
    software_version: str
    quality_flags: tuple[str, ...]
    calibration_id: str | None
    consent_scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.stimulus_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", self.stimulus_hash):
            raise ConfigurationError("stimulus_hash must be a SHA-256 hex digest.")
        if not isinstance(self.software_version, str) or not self.software_version.strip():
            raise ConfigurationError("software_version is required.")
        if self.calibration_id is not None and (
            not isinstance(self.calibration_id, str) or not self.calibration_id.strip()
        ):
            raise ConfigurationError("calibration_id must be null or a non-empty string.")
        for values in (self.quality_flags, self.consent_scopes):
            if not isinstance(values, (tuple, list)) or any(not isinstance(v, str) or not v.strip() for v in values):
                raise ConfigurationError("Flags and consent scopes must be arrays of non-empty strings.")
        if any(scope not in {s.value for s in ConsentScope} for scope in self.consent_scopes):
            raise ConfigurationError("Unknown consent scope.")


Serializable = EegFrame | GazeSample | MetricResult | SessionManifest


def to_dict(value: Serializable, metadata: ExportMetadata) -> dict[str, Any]:
    """Encode a supported contract into a schema-versioned provenance envelope."""
    if not isinstance(metadata, ExportMetadata):
        raise ConfigurationError("ExportMetadata is required.")
    if isinstance(value, MetricResult) and is_dataclass(value.value):
        raise ConfigurationError("Version-one serialization supports numeric MetricResult values only.")
    payload = asdict(value)
    if isinstance(value, EegFrame):
        payload["samples"] = value.samples.tolist()
        payload["timestamps_monotonic_s"] = value.timestamps_monotonic_s.tolist()
    elif isinstance(value, MetricResult):
        payload["status"] = value.status.value
    elif isinstance(value, SessionManifest):
        payload["consent"]["granted_scopes"] = sorted(s.value for s in value.consent.granted_scopes)
    elif not isinstance(value, GazeSample):
        raise ConfigurationError("Unsupported serialization type.")
    _check_provenance(value, metadata)
    return {"schema_version": 1, "type": type(value).__name__, "metadata": asdict(metadata), "data": payload}


def _check_provenance(value: Serializable, metadata: ExportMetadata) -> None:
    if not set(getattr(value, "quality_flags", ())).issubset(metadata.quality_flags):
        raise ConfigurationError("Export metadata must retain all data quality flags.")
    if isinstance(value, (GazeSample, SessionManifest)) and value.calibration_id != metadata.calibration_id:
        raise ConfigurationError("Conflicting calibration provenance.")
    if isinstance(value, SessionManifest):
        if (
            value.stimulus_sha256 != metadata.stimulus_hash
            or value.software_version != metadata.software_version
            or set(metadata.consent_scopes) != {s.value for s in value.consent.granted_scopes}
        ):
            raise ConfigurationError("Conflicting manifest provenance.")
        if any(
            not isinstance(v, str) or not v.strip()
            for v in (
                value.session_id,
                value.stimulus_id,
                value.created_at_utc,
                value.consent.participant_code,
                value.consent.document_version,
                value.consent.consented_at_utc,
            )
        ):
            raise ConfigurationError("Manifest session, stimulus, timestamps and consent record are required.")
        for timestamp in (value.created_at_utc, value.consent.consented_at_utc):
            try:
                parsed = datetime.fromisoformat(timestamp)
            except ValueError as error:
                raise ConfigurationError("Manifest timestamps must be ISO-8601 timestamps.") from error
            if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
                raise ConfigurationError("Manifest timestamps must specify UTC.")


def from_dict(envelope: dict[str, Any]) -> Serializable:
    """Validate and reconstruct an envelope, reporting malformed data as domain errors."""
    try:
        if (
            set(envelope) != {"schema_version", "type", "metadata", "data"}
            or type(envelope["schema_version"]) is not int
            or envelope["schema_version"] != 1
        ):
            raise ConfigurationError("Expected schema_version 1 and type, metadata, data fields.")
        json.dumps(envelope, allow_nan=False)
        metadata = ExportMetadata(**envelope["metadata"])
        payload = dict(envelope["data"])
        kind = envelope["type"]
        if kind == "EegFrame":
            payload["channel_names"] = tuple(payload["channel_names"])
            payload["quality_flags"] = tuple(payload.get("quality_flags", ()))
            value = EegFrame(**payload)
        elif kind == "GazeSample":
            if type(payload["valid"]) is not bool:
                raise ConfigurationError("Gaze valid must be a boolean.")
            payload["quality_flags"] = tuple(payload.get("quality_flags", ()))
            value = GazeSample(**payload)
        elif kind == "MetricResult":
            payload["status"] = MetricStatus(payload["status"])
            value = MetricResult(**payload)
        elif kind == "SessionManifest":
            consent = dict(payload["consent"])
            consent["granted_scopes"] = frozenset(ConsentScope(s) for s in consent["granted_scopes"])
            payload["consent"] = SessionConsent(**consent)
            payload["quality_flags"] = tuple(payload.get("quality_flags", ()))
            value = SessionManifest(**payload)
        else:
            raise ConfigurationError(f"Unknown serialized type: {kind}.")
        _check_provenance(value, metadata)
        return value
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ConfigurationError(f"Invalid serialized data: {error}") from error


def dumps(value: Serializable, metadata: ExportMetadata) -> str:
    """Return stable JSON, refusing non-finite values anywhere in the document."""
    try:
        return json.dumps(to_dict(value, metadata), sort_keys=True, indent=2, allow_nan=False) + "\n"
    except (ValueError, TypeError) as error:
        raise ConfigurationError(f"Cannot serialize data: {error}") from error


def loads(text: str) -> Serializable:
    """Read strict JSON; NaN and Infinity are not valid JSON numbers."""

    def reject_constant(value: str) -> None:
        raise ConfigurationError(f"Non-finite JSON constant: {value}")

    try:
        return from_dict(json.loads(text, parse_constant=reject_constant))
    except (ValueError, TypeError) as error:
        raise ConfigurationError(f"Invalid JSON: {error}") from error


def write_json(destination: Path, value: Serializable, metadata: ExportMetadata) -> None:
    """Atomically replace a file only after successful validation and serialization."""
    atomic_write_json(destination, json.loads(dumps(value, metadata)))


def read_json(source: Path) -> Serializable:
    """Read an exported contract from disk."""
    try:
        return loads(source.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigurationError(f"Cannot read {source}: {error}") from error
