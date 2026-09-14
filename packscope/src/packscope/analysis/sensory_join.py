# SPDX-License-Identifier: Apache-2.0
"""Offline descriptive joins of discrete self-reports and visual-exposure windows."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from packscope.analysis.attribution import WindowAttribution
from packscope.models import MetricReason, MetricResult, MetricStatus, SessionConsent
from packscope.sensory.models import SensoryRating, TastingProtocolMetadata
from packscope.sensory.quality import evaluate_sensory_quality


@dataclass(frozen=True, slots=True)
class SensoryAttribution:
    """Explicit study context absent from a bare WindowAttribution.

    variant_id identifies an immutable version in the session's stimulus manifest.
    No identifiers are inferred from source names, timestamps or ROI labels.
    """

    session_id: str
    variant_id: str
    stimulus_id: str
    product_id: str
    attribution: WindowAttribution

    def __post_init__(self) -> None:
        if any(
            not isinstance(v, str) or not v.strip()
            for v in (self.session_id, self.variant_id, self.stimulus_id, self.product_id)
        ):
            raise ValueError("Explicit session, versioned variant, stimulus and product IDs are required.")
        if not isinstance(self.attribution, WindowAttribution):
            raise ValueError("attribution must be a WindowAttribution.")


@dataclass(frozen=True, slots=True)
class SensoryJoinRow:
    """One session/variant observation, irrespective of the number of EEG windows.

    Free text never appears in descriptive tables. Unavailable measurements remain
    independent: rejecting EEG does not erase valid gaze dwell or a valid self-report.
    """

    session_id: str
    variant_id: str
    stimulus_id: str | None
    product_id: str | None
    window_count: int
    gaze_dwell_s: MetricResult[DwellSummary]
    eeg_metrics: tuple[MetricResult[float], ...]
    hedonic_rating: MetricResult[int]
    protocol: TastingProtocolMetadata | None
    consent_scopes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DwellSummary:
    """Non-overlapping exposure dwell, counting repeated metric windows only once."""

    roi_dwell_s: dict[str, float]
    unassigned_dwell_s: float


@dataclass(frozen=True, slots=True)
class SensoryJoinSummary:
    """Full outer join table; N counts session/variant pairs, never EEG windows.

    n is the number with available dwell and hedonic ratings. n_eeg_pairs additionally
    requires at least one available EEG metric. Neither count asserts independence
    between sessions from the same participant. Zero is an observed count, not a score.
    """

    rows: tuple[SensoryJoinRow, ...]
    n: int
    n_eeg_pairs: int
    missing_rating_count: int
    missing_hedonic_count: int
    missing_attribution_count: int
    rejected_rating_count: int
    rejected_eeg_window_count: int
    rejection_reasons: dict[str, int]


def _unavailable(name: str, reason: MetricReason) -> MetricResult:
    return MetricResult(name, MetricStatus.UNAVAILABLE, None, reason)


def _dwell(records: Sequence[SensoryAttribution]) -> MetricResult[DwellSummary]:
    if not records:
        return _unavailable("gaze_dwell", MetricReason.MISSING_ATTRIBUTION)
    intervals = {}
    for record in records:
        attribution = record.attribution
        window = attribution.metric_window
        start, end = window.start_time_s, window.end_time_s
        values = (*attribution.roi_dwell_s.values(), attribution.unassigned_dwell_s)
        if (
            not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0 for v in values
            )
            or not all(math.isfinite(v) for v in (start, end))
            or end < start
            or sum(values) > end - start + 1e-9
        ):
            return _unavailable("gaze_dwell", MetricReason.INVALID_ATTRIBUTION)
        dwell = (dict(attribution.roi_dwell_s), attribution.unassigned_dwell_s)
        if (start, end) in intervals and intervals[start, end] != dwell:
            return _unavailable("gaze_dwell", MetricReason.INVALID_ATTRIBUTION)
        intervals[start, end] = dwell
    ordered = sorted(intervals)
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:], strict=False)):
        return _unavailable("gaze_dwell", MetricReason.INVALID_ATTRIBUTION)
    totals: dict[str, float] = defaultdict(float)
    unassigned = 0.0
    for roi_dwell, other in intervals.values():
        for roi, seconds in roi_dwell.items():
            totals[roi] += seconds
        unassigned += other
    if not all(math.isfinite(v) for v in (*totals.values(), unassigned)):
        return _unavailable("gaze_dwell", MetricReason.INVALID_ATTRIBUTION)
    return MetricResult("gaze_dwell", MetricStatus.AVAILABLE, DwellSummary(dict(totals), unassigned))


def join_attributions_with_sensory(
    attributions: Sequence[SensoryAttribution],
    ratings: Sequence[SensoryRating],
    *,
    consents: Mapping[str, SessionConsent],
    protocols: Mapping[tuple[str, str], TastingProtocolMetadata],
) -> MetricResult[SensoryJoinSummary]:
    """Full outer join by (session_id, variant_id), with explicit per-session consent.

    Protocols are keyed by the same pair. A variant is one tasting per session; use
    separate session IDs for repeat tastings. No nearest-time matching, interpolation,
    neural prediction, or cross-protocol pooling is performed. Ranking is one-based
    without ties within each session/protocol version; incomplete rankings are allowed.
    An available summary means a table exists, even when N=0; each missing or rejected
    row measurement has its own UNAVAILABLE result. Empty inputs return UNAVAILABLE.
    """
    grouped_attributions: dict[tuple[str, str], list[SensoryAttribution]] = defaultdict(list)
    grouped_ratings: dict[tuple[str, str], list[SensoryRating]] = defaultdict(list)
    for record in attributions:
        grouped_attributions[record.session_id, record.variant_id].append(record)
    for rating in ratings:
        grouped_ratings[rating.session_id, rating.variant_id].append(rating)
    keys = sorted(grouped_attributions.keys() | grouped_ratings.keys())
    if not keys:
        return _unavailable("sensory_join", MetricReason.NO_QUALIFYING_PAIRS)
    gated = {
        id(r): evaluate_sensory_quality(r, consents.get(r.session_id), protocols.get((r.session_id, r.variant_id)))
        for r in ratings
    }
    ids = Counter(r.rating_id for r in ratings)
    ranks = Counter(
        (r.session_id, protocols[r.session_id, r.variant_id].protocol_version, r.preference_rank)
        for r in ratings
        if gated[id(r)].status == MetricStatus.AVAILABLE and r.preference_rank is not None
    )
    rows = []
    n = n_eeg = missing = missing_hedonic = missing_attribution = rejected = rejected_eeg = 0
    reasons: Counter[str] = Counter()
    for key in keys:
        records, candidates = grouped_attributions[key], grouped_ratings[key]
        protocol = protocols.get(key)
        consent = consents.get(key[0])
        identities = {(a.stimulus_id, a.product_id) for a in records}
        identities.update((r.stimulus_id, r.product_id) for r in candidates)
        identity = next(iter(identities)) if len(identities) == 1 else (None, None)
        dwell = _dwell(records)
        if not candidates:
            hedonic = _unavailable("hedonic_scale_9pt", MetricReason.MISSING_RATING)
            missing += 1
        else:
            unavailable = next(
                (gated[id(r)] for r in candidates if gated[id(r)].status != MetricStatus.AVAILABLE), None
            )
            if unavailable is not None:
                hedonic = MetricResult(
                    "hedonic_scale_9pt", MetricStatus.UNAVAILABLE, None, unavailable.reason, details=unavailable.details
                )
            elif len(candidates) != 1 or ids[candidates[0].rating_id] > 1:
                hedonic = _unavailable("hedonic_scale_9pt", MetricReason.AMBIGUOUS_RATING)
            elif len(identities) != 1:
                hedonic = _unavailable("hedonic_scale_9pt", MetricReason.PROVENANCE_MISMATCH)
            else:
                rating = gated[id(candidates[0])].value
                if (
                    rating.preference_rank is not None
                    and ranks[key[0], protocol.protocol_version, rating.preference_rank] > 1
                ):
                    hedonic = _unavailable("hedonic_scale_9pt", MetricReason.PREFERENCE_RANK_CONFLICT)
                else:
                    hedonic = MetricResult("hedonic_scale_9pt", MetricStatus.AVAILABLE, rating.hedonic_scale_9pt)
            if hedonic.status != MetricStatus.AVAILABLE:
                rejected += 1
            missing_hedonic += hedonic.reason == MetricReason.MISSING_HEDONIC_SCORE
        if len(identities) != 1:
            dwell = _unavailable("gaze_dwell", MetricReason.PROVENANCE_MISMATCH)
        missing_attribution += not records
        eeg = tuple(a.attribution.metric_window.result for a in records)
        rejected_eeg += sum(m.status != MetricStatus.AVAILABLE for m in eeg)
        for result in (hedonic, dwell, *eeg):
            if result.status != MetricStatus.AVAILABLE:
                reasons[str(result.reason)] += 1
        paired = hedonic.status == dwell.status == MetricStatus.AVAILABLE
        n += paired
        n_eeg += paired and any(m.status == MetricStatus.AVAILABLE for m in eeg)
        rows.append(
            SensoryJoinRow(
                *key,
                *identity,
                len(records),
                dwell,
                eeg,
                hedonic,
                protocol,
                tuple(sorted(s.value for s in consent.granted_scopes)) if consent else (),
            )
        )
    return MetricResult(
        "sensory_join",
        MetricStatus.AVAILABLE,
        SensoryJoinSummary(
            tuple(rows), n, n_eeg, missing, missing_hedonic, missing_attribution, rejected, rejected_eeg, dict(reasons)
        ),
    )
