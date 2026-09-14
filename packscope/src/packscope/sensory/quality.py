# SPDX-License-Identifier: Apache-2.0
"""Consent and completeness gates for protocol-dependent self-reports."""

from dataclasses import replace

from packscope.models import MetricReason, MetricResult, MetricStatus, SessionConsent
from packscope.sensory.models import SensoryRating, TastingProtocolMetadata


def evaluate_sensory_quality(
    rating: SensoryRating,
    consent: SessionConsent | None,
    metadata: TastingProtocolMetadata | None,
) -> MetricResult[SensoryRating]:
    """Gate one rating without imputing scores or claiming protocol validity.

    Cross-record duplicate/rank conflicts are checked by the offline join. Optional
    intensity and rank fields are not fabricated or treated as required hedonic data.
    Any supplied free text, even an empty string, requires its own permission.
    """

    def unavailable(reason: MetricReason) -> MetricResult[SensoryRating]:
        return MetricResult("sensory_rating", MetricStatus.UNAVAILABLE, None, reason)

    if not isinstance(consent, SessionConsent) or not consent.allow_sensory_ratings:
        return unavailable(MetricReason.CONSENT_NOT_GRANTED)
    if not isinstance(rating, SensoryRating):
        return unavailable(MetricReason.INVALID_SENSORY_RECORD)
    if rating.free_text_notes is not None and not consent.allow_sensory_freetext:
        return unavailable(MetricReason.FREETEXT_CONSENT_NOT_GRANTED)
    if not isinstance(metadata, TastingProtocolMetadata):
        return unavailable(MetricReason.MISSING_PROTOCOL)
    try:
        # Revalidate and detach mutable dictionaries/lists before returning gated data.
        metadata = replace(metadata)
        rating = replace(rating)
    except (TypeError, ValueError):
        return unavailable(MetricReason.INVALID_SENSORY_RECORD)
    if rating.quality_flags:
        return MetricResult(
            "sensory_rating",
            MetricStatus.UNAVAILABLE,
            None,
            MetricReason.RATING_QUALITY_FAILED,
            details={"quality_flags": ", ".join(rating.quality_flags)},
        )
    if rating.hedonic_scale_9pt is None:
        return unavailable(MetricReason.MISSING_HEDONIC_SCORE)
    return MetricResult(
        "sensory_rating",
        MetricStatus.AVAILABLE,
        rating,
        details={
            "protocol_version": metadata.protocol_version,
            "blinding_type": metadata.blinding_type.value,
            "washout_seconds": metadata.washout_seconds,
            "serving_temperature_c": metadata.serving_temperature_c,
            "counterbalanced_order": metadata.counterbalanced_order,
            "allow_sensory_ratings": consent.allow_sensory_ratings,
            "allow_sensory_freetext": consent.allow_sensory_freetext,
        },
    )
