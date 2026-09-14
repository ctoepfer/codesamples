# SPDX-License-Identifier: Apache-2.0
"""Scale validation, permission boundaries and backward-compatible metric contracts."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from packscope.errors import ConfigurationError
from packscope.io.serialization import ExportMetadata, dumps, loads
from packscope.models import MetricReason, MetricResult, MetricStatus, SessionConsent
from packscope.privacy import ConsentScope, SessionManifest
from packscope.sensory.models import BlindingType, SensoryRating, TastingProtocolMetadata
from packscope.sensory.quality import evaluate_sensory_quality


def rating() -> SensoryRating:
    return SensoryRating("r", "s", "stim", "variant@v1", "product", datetime(2026, 1, 2, tzinfo=UTC), 5)


def protocol() -> TastingProtocolMetadata:
    return TastingProtocolMetadata("v1", BlindingType.DOUBLE_BLIND, 60, 20, True)


def consent() -> SessionConsent:
    return SessionConsent.create("p", "v1", [], allow_sensory_ratings=True)


@pytest.mark.parametrize("score", [1, 9, None])
def test_hedonic_boundaries(score: int | None) -> None:
    assert replace(rating(), hedonic_scale_9pt=score).hedonic_scale_9pt == score


@pytest.mark.parametrize(
    "changes",
    [
        {"hedonic_scale_9pt": 0},
        {"hedonic_scale_9pt": 10},
        {"hedonic_scale_9pt": True},
        {"hedonic_scale_9pt": 5.0},
        {"hedonic_scale_9pt": "5"},
        {"preference_rank": 0},
        {"preference_rank": False},
        {"intensity_ratings": {"aroma": float("nan")}},
        {"intensity_ratings": {"aroma": 11}},
        {"intensity_ratings": {"aroma": -1}},
        {"intensity_ratings": {"aroma": True}},
        {"quality_flags": "bad"},
        {"free_text_notes": 1},
        {"timestamp": datetime(2026, 1, 1)},
        {"variant_id": ""},
    ],
)
def test_invalid_rating_fields(changes: dict) -> None:
    with pytest.raises(ValueError):
        replace(rating(), **changes)


def test_frozen_and_defensive_copies() -> None:
    intensities, flags = {"taste": 10.0, "aroma": 0.0}, []
    record = replace(rating(), intensity_ratings=intensities, quality_flags=flags)
    intensities["taste"] = float("nan")
    flags.append("bad")
    assert record.intensity_ratings["taste"] == 10 and record.quality_flags == []
    with pytest.raises(FrozenInstanceError):
        record.rating_id = "new"
    record.intensity_ratings["taste"] = float("nan")
    assert evaluate_sensory_quality(record, consent(), protocol()).reason == MetricReason.INVALID_SENSORY_RECORD


@pytest.mark.parametrize(
    "changes",
    [
        {"blinding_type": "DOUBLE_BLIND"},
        {"washout_seconds": -1},
        {"serving_temperature_c": float("inf")},
        {"counterbalanced_order": 1},
    ],
)
def test_invalid_protocol(changes: dict) -> None:
    with pytest.raises(ValueError):
        replace(protocol(), **changes)


def test_consent_defaults_and_gates() -> None:
    old = SessionConsent("p", "v1", frozenset(), "2026-01-01T00:00:00Z")
    assert not old.allow_sensory_ratings and not old.allow_sensory_freetext
    assert evaluate_sensory_quality(rating(), old, protocol()).reason == MetricReason("CONSENT_NOT_GRANTED")
    result = evaluate_sensory_quality(rating(), consent(), protocol())
    assert result.status == MetricStatus.AVAILABLE and result.value == rating()
    assert result.details["blinding_type"] == "DOUBLE_BLIND"
    assert evaluate_sensory_quality(rating(), consent(), None).reason == MetricReason.MISSING_PROTOCOL
    assert evaluate_sensory_quality(replace(rating(), hedonic_scale_9pt=None), consent(), protocol()).reason == (
        MetricReason.MISSING_HEDONIC_SCORE
    )
    flagged = evaluate_sensory_quality(replace(rating(), quality_flags=["incomplete"]), consent(), protocol())
    assert flagged.status == MetricStatus.UNAVAILABLE and flagged.value is None


def test_freetext_requires_separate_grant() -> None:
    record = replace(rating(), free_text_notes="private note")
    result = evaluate_sensory_quality(record, consent(), protocol())
    assert result.reason == MetricReason.FREETEXT_CONSENT_NOT_GRANTED
    assert "private note" not in repr(result)
    allowed = SessionConsent.create("p", "v1", [ConsentScope.SENSORY_RATINGS, ConsentScope.SENSORY_FREETEXT])
    assert allowed.allow_sensory_ratings and allowed.allow_sensory_freetext
    assert evaluate_sensory_quality(record, allowed, protocol()).status == MetricStatus.AVAILABLE
    with pytest.raises(ConfigurationError):
        SessionConsent.create("p", "v1", [], allow_sensory_ratings="yes")


def test_consent_manifest_roundtrip() -> None:
    record = SessionManifest("s", "stim", "a" * 64, consent(), "0.1.0", "2026-01-01T00:00:00Z")
    metadata = ExportMetadata("a" * 64, "0.1.0", (), None, ("sensory_ratings",))
    assert loads(dumps(record, metadata)).consent == record.consent


def test_numeric_and_structured_metric_invariants() -> None:
    assert MetricResult[float]("test", MetricStatus.AVAILABLE, 1.0).value == 1.0
    for value in (float("nan"), float("inf"), True, "score"):
        with pytest.raises(ValueError):
            MetricResult("test", MetricStatus.AVAILABLE, value)
    invalid = rating()
    invalid.intensity_ratings["taste"] = float("inf")
    with pytest.raises(ValueError):
        MetricResult("test", MetricStatus.AVAILABLE, invalid)
    with pytest.raises(ValueError):
        MetricResult("test", MetricStatus.UNAVAILABLE, rating(), MetricReason.RATING_QUALITY_FAILED)


def test_revocation_removes_named_scope() -> None:
    revoked = replace(consent(), allow_sensory_ratings=False)
    assert ConsentScope.SENSORY_RATINGS not in revoked.granted_scopes
    assert evaluate_sensory_quality(rating(), revoked, protocol()).reason == MetricReason.CONSENT_NOT_GRANTED


def test_structured_result_does_not_silently_use_numeric_json_schema() -> None:
    result = evaluate_sensory_quality(rating(), consent(), protocol())
    metadata = ExportMetadata("a" * 64, "0.1.0", (), None, ("sensory_ratings",))
    with pytest.raises(ConfigurationError, match="numeric MetricResult"):
        dumps(result, metadata)
