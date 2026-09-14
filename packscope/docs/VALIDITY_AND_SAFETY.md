<!-- SPDX-License-Identifier: Apache-2.0 -->
# Measurement Validity, Safety, and Responsible Use

> PackScope produces exploratory measurements for comparative design research. It does **not** read minds, identify emotion, assess mental health, determine purchasing intent, or provide medical advice.

## Interpretation boundary

A packaging-research article supplied with this project describes quadrants labelled “Interest,” “Confusion,” “Easy Enjoyment,” and “Unengaged.” Those labels can be useful as **predeclared design hypotheses**, but the article does not validate a universal mapping from a beta/theta ratio or FAA to a person’s emotion, cognition, or shopping decision. PackScope consequently keeps the underlying metrics separate from any optional quadrant visualization.

| PackScope reports | PackScope does not report |
| --- | --- |
| Calibrated gaze location and fixation dwell | Whether a viewer “looked because they liked it” |
| Relative PSD change in a named channel and band | Emotion, preference, attention, confusion, or purchase intent |
| `ln(alpha(F4)) − ln(alpha(F3))` when conditions are satisfied | A direct measurement of positive or negative affect |
| Temporal overlap of a gaze fixation and metric window | A causal effect of a label element on the signal |
| Data loss, calibration error, and excluded windows | Guaranteed tracker accuracy or artifact-free EEG |

## Minimum defensible study workflow

A homebrew pilot should focus on within-participant comparisons, not a population-wide score. Use the same display, task, headset placement, reference, lighting, and viewing conditions for each variant. Counterbalance presentation order, give each design matched exposure time, define ROIs before collection, and retain a neutral or control condition.

Perform a five- or nine-point eye-tracker calibration against the actual display. Immediately validate against known points and record median and 95th-percentile error. Repeat drift checks during the session. If using a webcam, record its resolution, placement, distance, image mirror/rotation policy, head movement constraints, lighting, glasses/occlusion failures, dropout rate, and validation performance. A webcam feature extractor is not a dedicated eye tracker.[1]

Record a quiet EEG baseline for each participant and session. For raw EEG, define montage, reference, channel labels, sample rate, filter policy, PSD window, alpha band, and artifact rules. Use only baseline-relative participant-level comparisons and include data-quality exclusions in every output. EEG artifacts can resemble signal of interest, and no single artifact-removal technique is adequate for every recording.[2]

## Quality gates

The initial implementation performs basic, auditable gates. A research protocol should tune and extend them to its hardware.

| Signal | Initial gates | Add before consequential interpretation |
| --- | --- | --- |
| Raw EEG | Duration, flatline, large timing gaps, source flags, optional amplitude cap | Electrode impedance/connectivity, line-noise checks, saturation, EOG/EMG/motion markers, visual review and sensitivity analyses |
| ThinkGear / Arduino Brain bands | Device poor-signal field and parse validity | Stable electrode contact, per-subject repeatability, comparison with an independent reference if claims require it |
| Dedicated eye tracker | Validity and source-reported confidence | Calibration/validation accuracy, precision, drift, blink loss, glasses and head-pose stratification |
| Webcam features | Detection success and calibration validation | Controlled camera geometry, illumination, head-motion tolerance, external validation versus a reference tracker |

Rejecting a window does not mean the participant did something wrong. Retain the number of rejected and retained observations, the reason codes, and their distribution by condition.

## Human-subject protections

This repository includes a minimal consent model, but it is not an ethics protocol or legal advice. A real study should provide plain-language, affirmative, documented, and revocable consent that specifies raw EEG, gaze traces, camera video, derived metrics, storage location, retention period, sharing, reuse, and deletion. Researchers should collect only what is necessary and should default to local processing and pseudonymous IDs.[3]

Do not use PackScope outputs to make employment, insurance, educational, medical, credit, legal, law-enforcement, eligibility, or other high-impact decisions. Do not use the tool with minors or vulnerable participants without an appropriate, jurisdiction-specific review process. Do not claim that an ad, can, or bottle label “caused” an emotional or neurological state from a single participant, a single metric, or an unvalidated model.

## Reporting checklist

Every chart, heatmap, or comparison table should state the study limitations and retain the following context.

| Category | Record |
| --- | --- |
| Stimulus | Image hash, display resolution, variant ID, ROI ID/version, display duration |
| Participant/session | Pseudonymous code, consent document version, baseline protocol, randomized order |
| EEG | Device, electrode montage/reference, labels, sample rate, timestamp source, preprocessing/version, rejected windows |
| Gaze | Tracker/camera, calibration targets, validation error, drift checks, dropout, sample rate, coordinate policy |
| Analysis | Band definitions, PSD parameters, baseline normalization, fixation rules, metrics, uncertainty, exclusions |
| Interpretation | Descriptive language, sample/trial counts, alternative explanations, no diagnostic/categorical claims |

## References

[1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11225961/ "Guidelines for minimum reporting of eye-tracking studies"
[2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6427454/ "Review of artefact removal and denoising in EEG biosignal processing"
[3]: https://www.unesco.org/en/legal-affairs/recommendation-ethics-neurotechnology "UNESCO Recommendation on the Ethics of Neurotechnology"

## Scientific boundary for taste and sensory self-reports

Taste, aroma, intensity, and hedonic ratings are **protocol-dependent self-reports**.
They record what a participant reported on a declared scale under recorded serving
and exposure conditions. They are not objective flavor measurements, neural liking
scores, emotion labels, or automated preference classifications. A reported
preference rank is distinct from a prediction of preference or purchase behavior.

Any analysis of relationships between gaze/EEG measurements and taste ratings is
strictly exploratory and descriptive or correlation-based. Correlation does not
establish neural causality. PackScope does not fit predictive liking models or
classifiers. Report sample size, missingness, exclusions, scale definitions, protocol
versions, and participant/session structure. Repeated EEG windows or repeated
variants from one participant must not be treated as independent participants.
Keep packaging expectations and post-tasting experiences separately identified;
never reconstruct a missing rating from gaze, EEG, rank, or another participant.

Packaging exposure **cannot be claimed to cause flavor-perception changes** from
these joins without rigorous protocol controls and an appropriate causal study
design. Controls include counterbalancing exposure and serving order, documented
washouts, matched serving conditions, and double-blinding where the experimental
condition permits it. Record who was blinded, what information was hidden, and any
unblinding or carryover concerns in the study protocol. A recorded `DOUBLE_BLIND`
flag is not proof of successful blinding; `SINGLE_BLIND` and `OPEN` are explicit
conditions requiring corresponding limitations. Passing a software quality gate
is not validation of the study's causal interpretation.

Obtain explicit sensory-rating consent before collection and a separate permission
for optional free-text notes. Notes can contain identifying or sensitive information;
they are excluded from descriptive join tables. Missing consent, flagged ratings,
and missing hedonic scores produce unavailable results with reasons, never imputed
hedonic values. A zero paired sample count describes absence of qualifying pairs;
it must not be presented as a neutral or zero-liking response.
