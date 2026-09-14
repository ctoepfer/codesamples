# SPDX-License-Identifier: Apache-2.0
"""Offline identity joins, rejection accounting and independent measurements."""

from dataclasses import replace
from datetime import timedelta

import pytest

from packscope.analysis.sensory_join import join_attributions_with_sensory
from packscope.errors import ConfigurationError
from packscope.models import MetricReason, MetricResult, MetricStatus
from packscope.testing.synthetic import SyntheticSensoryDataset, generate_synthetic_sensory_ratings


@pytest.fixture
def dataset() -> SyntheticSensoryDataset:
    return generate_synthetic_sensory_ratings(session_count=1)


def join(dataset: SyntheticSensoryDataset) -> MetricResult:
    return join_attributions_with_sensory(
        dataset.attributions, dataset.ratings, consents=dataset.consents, protocols=dataset.protocols
    )


def test_post_exposure_join_ignores_timing(dataset: SyntheticSensoryDataset) -> None:
    shifted = tuple(replace(r, timestamp=r.timestamp + timedelta(days=90)) for r in dataset.ratings)
    result = join(replace(dataset, ratings=shifted))
    assert result.status == MetricStatus.AVAILABLE
    summary = result.value
    assert summary.n == summary.n_eeg_pairs == 2
    assert summary.missing_rating_count == summary.rejected_rating_count == 0
    assert [r.hedonic_rating.value for r in summary.rows] == [1, 2]
    assert all(r.gaze_dwell_s.value.roi_dwell_s["panel"] > 3 for r in summary.rows)
    assert all(r.protocol.blinding_type.value == "DOUBLE_BLIND" for r in summary.rows)
    assert all("sensory_ratings" in r.consent_scopes for r in summary.rows)


def test_missing_and_rejected_rows_are_retained(dataset: SyntheticSensoryDataset) -> None:
    ratings = (replace(dataset.ratings[0], hedonic_scale_9pt=None),)
    summary = join(replace(dataset, ratings=ratings)).value
    assert summary.n == 0
    assert len(summary.rows) == 2
    assert summary.missing_rating_count == summary.missing_hedonic_count == summary.rejected_rating_count == 1
    assert all(r.hedonic_rating.value is None for r in summary.rows)
    assert summary.rejection_reasons[MetricReason.MISSING_RATING] == 1
    orphan = join(replace(dataset, attributions=())).value
    assert orphan.n == 0 and orphan.missing_attribution_count == 2
    assert all(r.hedonic_rating.value is not None for r in orphan.rows)
    assert all(r.gaze_dwell_s.value is None for r in orphan.rows)
    assert join(replace(dataset, attributions=(), ratings=())).reason == MetricReason.NO_QUALIFYING_PAIRS


def test_consent_protocol_and_notes(dataset: SyntheticSensoryDataset) -> None:
    summary = join(replace(dataset, consents={})).value
    assert summary.n == 0 and summary.rejection_reasons[MetricReason.CONSENT_NOT_GRANTED] == 2
    summary = join(replace(dataset, protocols={})).value
    assert summary.n == 0 and summary.rejection_reasons[MetricReason.MISSING_PROTOCOL] == 2
    ratings = tuple(replace(r, free_text_notes="DO NOT DISCLOSE") for r in dataset.ratings)
    result = join(replace(dataset, ratings=ratings))
    assert result.value.n == 0 and "DO NOT DISCLOSE" not in repr(result)


def test_duplicates_and_rank_conflicts(dataset: SyntheticSensoryDataset) -> None:
    summary = join(replace(dataset, ratings=(*dataset.ratings, dataset.ratings[0]))).value
    assert summary.rejection_reasons[MetricReason.AMBIGUOUS_RATING] == 1
    ranks = tuple(replace(r, preference_rank=1) for r in dataset.ratings)
    summary = join(replace(dataset, ratings=ranks)).value
    assert summary.n == 0 and summary.rejection_reasons[MetricReason.PREFERENCE_RANK_CONFLICT] == 2
    duplicate_ids = tuple(replace(r, rating_id="duplicate") for r in dataset.ratings)
    assert join(replace(dataset, ratings=duplicate_ids)).value.n == 0


def test_provenance_mismatch_and_no_cross_session_matching(dataset: SyntheticSensoryDataset) -> None:
    ratings = tuple(replace(r, product_id="different") for r in dataset.ratings)
    summary = join(replace(dataset, ratings=ratings)).value
    assert summary.n == 0
    assert all(r.hedonic_rating.reason == MetricReason.PROVENANCE_MISMATCH for r in summary.rows)
    ratings = tuple(replace(r, session_id="other") for r in dataset.ratings)
    summary = join(replace(dataset, ratings=ratings)).value
    assert len(summary.rows) == 4 and summary.n == 0
    assert summary.missing_rating_count == summary.missing_attribution_count == 2


def test_dwell_not_repeated_across_metrics(dataset: SyntheticSensoryDataset) -> None:
    record = dataset.attributions[0]
    duplicate = replace(
        record,
        attribution=replace(
            record.attribution,
            metric_window=replace(
                record.attribution.metric_window, result=MetricResult("alpha", MetricStatus.AVAILABLE, 0.5)
            ),
        ),
    )
    original = join(dataset).value.rows[0].gaze_dwell_s.value
    summary = join(replace(dataset, attributions=(*dataset.attributions, duplicate))).value
    assert summary.n == 2
    assert summary.rows[0].window_count == 2
    assert summary.rows[0].gaze_dwell_s.value == original


def test_failed_eeg_retains_gaze_and_self_report(dataset: SyntheticSensoryDataset) -> None:
    records = tuple(
        replace(
            r,
            attribution=replace(
                r.attribution,
                metric_window=replace(
                    r.attribution.metric_window,
                    result=MetricResult("faa", MetricStatus.FAILED_QUALITY_GATE, None, "bad EEG"),
                ),
            ),
        )
        for r in dataset.attributions
    )
    summary = join(replace(dataset, attributions=records)).value
    assert summary.n == 2 and summary.n_eeg_pairs == 0
    assert summary.rejected_eeg_window_count == 2
    assert summary.rejection_reasons["bad EEG"] == 2


def test_invalid_dwell_and_overlapping_windows(dataset: SyntheticSensoryDataset) -> None:
    record = dataset.attributions[0]
    invalid = replace(record, attribution=replace(record.attribution, roi_dwell_s={"panel": float("nan")}))
    summary = join(replace(dataset, attributions=(invalid, dataset.attributions[1]))).value
    assert summary.rows[0].gaze_dwell_s.reason == MetricReason.INVALID_ATTRIBUTION
    overlapping = replace(
        record,
        attribution=replace(
            record.attribution, metric_window=replace(record.attribution.metric_window, start_time_s=1, end_time_s=5)
        ),
    )
    summary = join(replace(dataset, attributions=(*dataset.attributions, overlapping))).value
    assert summary.rows[0].gaze_dwell_s.reason == MetricReason.INVALID_ATTRIBUTION


def test_fixture_reproducible_scores_and_explicit_versions() -> None:
    first, second = generate_synthetic_sensory_ratings(), generate_synthetic_sensory_ratings(seed=10)
    assert first.ratings == second.ratings  # Different EEG noise never determines self-report scores.
    assert all("@v1" in r.variant_id for r in first.ratings)
    with pytest.raises(ConfigurationError, match="positive integer"):
        generate_synthetic_sensory_ratings(session_count=0)
