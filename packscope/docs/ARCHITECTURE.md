# PackScope Architecture

> **Status:** initial reference implementation. PackScope is an exploratory, local-first research utility. It does not diagnose, detect emotion, determine purchase intent, or establish causal responses to packaging.

## Design decision

PackScope separates **device transport**, **measurement processing**, **gaze-space calibration**, **time-window attribution**, and **reporting**. This boundary is essential because a MindFlex reading, webcam face landmarks, and multichannel OpenBCI samples have materially different provenance and validity. The package retains that distinction in types and refuses unavailable calculations rather than fabricating a common score.

```mermaid
flowchart LR
    subgraph Acquisition
      MF[MindFlex / NeuroSky\nDirect ThinkGear serial]
      AR[MindFlex + Arduino\nBrain CSV bridge]
      OB[OpenBCI\nBrainFlow]
      LS[Existing streams\nLSL]
      WE[Webcam landmarks\nMediaPipe optional]
      ET[Dedicated tracker\nExternal/LSL adapter]
    end
    subgraph Normalization
      BP[BandPowerSnapshot\nrelative device bands]
      EF[EegFrame\nraw channels + timestamps]
      GF[Calibrated GazeSample\nnormalized display space]
    end
    subgraph Processing
      Q[Quality gates]
      PSD[PSD features\nFAA only with F3 + F4]
      FX[Fixation detector]
      AT[Time overlap attribution]
    end
    subgraph Outputs
      RO[Versioned ROIs]
      HM[Gaze-density heatmap]
      RM[Transparent metric tables\n+ session manifest]
    end
    MF --> BP
    AR --> BP
    OB --> EF
    LS --> EF
    WE --> GF
    ET --> GF
    EF --> Q --> PSD --> AT
    GF --> FX --> AT
    RO --> AT
    FX --> HM
    AT --> RM
    PSD --> RM
```

## Data contracts

| Contract | Produced by | Key properties | Deliberately not claimed |
| --- | --- | --- | --- |
| `BandPowerSnapshot` | Arduino Brain CSV and ThinkGear serial adapters | Device-derived relative bands, poor-signal value, eSense fields, host receipt time | Raw bilateral EEG, F3/F4 asymmetry, a universal focus score |
| `EegFrame` | BrainFlow and LSL adapters | Raw channels × samples, timestamps, explicit channel labels, sample rate and provenance | A common voltage unit without device metadata; inferred electrode locations |
| `GazeSample` | A calibrated source | Validity flag, top-left-origin normalized display coordinate, calibration ID | Dedicated-tracker accuracy from a webcam feature alone |
| `MetricResult` | Signal-processing functions | Value or typed reason for unavailability, processing details | Emotion, diagnosis, intent, or causal attribution |
| `WindowAttribution` | Multimodal join | Fixation dwell overlapping a metric window by ROI | Evidence that an ROI caused the metric change |

## Hardware adapters

### MindFlex, Arduino Brain, and NeuroSky / ThinkGear

The direct ThinkGear adapter implements an independent finite-state parser for the documented `0xAA 0xAA`, payload-length, payload, checksum framing. It decodes poor signal, Attention, Meditation, raw wave, and both documented eight-band payload formats. Unknown data rows are skipped safely for protocol forward compatibility. The `ThinkGearSerialSource` is a pyserial transport wrapper for a direct headset modification or Bluetooth serial bridge.[1]

The Arduino path is specifically compatible with the `readCSV()` output documented by the **kitschpatrol Brain** Arduino library: `signal strength, attention, meditation, delta, theta, low alpha, high alpha, low beta, high beta, low gamma, high gamma`. The `ArduinoBrainCsvDecoder` and `ArduinoBrainSerialSource` parse those exact eleven fields. Its default USB baud rate is `9600`, matching the BrainGrapher example, but this should be changed to match the user's sketch.[2] [3]

Both MindFlex paths expose a single-channel device's *relative* band values. They do not return bilateral frontal channels, and PackScope therefore returns `insufficient_channels` rather than calculating frontal alpha asymmetry (FAA). Attention and Meditation are retained only as device-provided eSense fields. The software does not relabel them as independently validated measures.

### OpenBCI and BrainFlow

`BrainFlowEegSource` uses lazy imports and supplies `EegFrame` blocks only after callers have explicitly mapped channel indices to electrode labels. A configuration cannot accidentally call `EEG_0` “F3.” This supports OpenBCI Cyton, Cyton+Daisy, Ganglion, and other boards documented by BrainFlow, subject to their own connection settings. OpenBCI currently points Python integrations to BrainFlow and recommends verifying signals in its GUI before direct integration.[4] [5]

A practical FAA-capable start is Cyton with an electrode montage that explicitly labels both `F3` and `F4`. Cyton provides eight channels at 250 Hz; Cyton+Daisy increases channel count but has a documented 125 Hz sampling-rate tradeoff; Ganglion provides four channels at 200 Hz. The exact electrode placement, reference, sampling rate, and hardware quality must be recorded for every session.[5]

### Lab Streaming Layer

`LslEegSource` is an optional bridge for acquisition systems already exposing a unique LSL EEG stream. It does not make synchronization promises merely because LSL is present. Stream identity, timestamp origin, channel schema, and clock-correction procedure must be persisted alongside the recording. For high-value studies, record raw LSL streams into an interoperable archival format and conduct final clock correction offline.[6]

### Eye tracking

PackScope defines only one gaze coordinate space: normalized `[0, 1] × [0, 1]`, with origin at the physical display’s top-left. A source must provide calibration provenance. `AffineGazeCalibration` maps an arbitrary source feature vector to that coordinate system using at least five paired measurements and reports validation error in normalized display units.

The optional MediaPipe component extracts iris-center *features* from a compatible Face Landmarker model. It does not claim that facial landmarks are gaze points. Webcam use therefore requires a per-session calibration and validation procedure, and its outputs should be treated as exploratory area-of-interest estimates.[7]

PyGaze remains a viable integration option for a separately distributed, GPL-compatible connector or for an LSL bridge from a dedicated tracker. It is deliberately **not** a PackScope dependency because PyGaze is GPL-3.0, whereas this repository is Apache-2.0.[8] The open core avoids importing, packaging, or distributing PyGaze.

## Measurement pipeline

The raw-EEG pipeline runs quality checks before it estimates power spectral density (PSD) by Welch’s method. Quality gates flag short windows, flatlined channels, long timestamp gaps, predeclared source flags, and optional amplitude limits. These checks are intentionally conservative and do not prove that a retained signal is neural rather than ocular, muscle, or motion artifact.

`frontal_alpha_asymmetry()` uses the declared convention `ln(alpha_power(F4)) − ln(alpha_power(F3))`. It requires both channels, the same quality-passed window, finite positive powers, and explicit channel labels. `beta_to_theta_power_ratio()` is named as a signal-derived spectral ratio rather than “cognitive load.” Both functions return a typed unavailable result rather than attempting an imputed value.

A simple I-DT fixation detector operates on contiguous valid gaze samples. It neither spans invalid samples nor bridges long time gaps. `attribute_metric_windows()` then measures only the temporal overlap between each fixation and each spectral window, assigning dwell time to a versioned region of interest (ROI). The output is a descriptive co-occurrence measure, not evidence of causal neural or emotional effect.

## Session and privacy model

`SessionConsent` is an affirmative, pseudonymous consent record with independent scope flags for raw EEG, gaze coordinates, camera video, derived metrics, and aggregate exports. A capture process should check the needed scope before it begins. `SessionManifest` writes stimulus hash, consent version, software version, and local-session provenance atomically. It does not itself collect name, email, face image, or cloud identifier.

Raw EEG, gaze traces, and camera video can be sensitive. PackScope is intentionally local-first. A production study application should encrypt retained data, define retention and deletion procedures, keep consent revocable, and avoid using outputs for employment, insurance, eligibility, safety-critical, or other high-impact decisions.[9]

## Repository layout

```text
packscope/
├── src/packscope/
│   ├── analysis/             # Quality gates, PSD features, baseline, fixation, attribution
│   ├── devices/              # Arduino CSV, ThinkGear serial/parser, BrainFlow, LSL
│   ├── gaze/                 # Display geometry, calibration, MediaPipe feature extraction
│   ├── reporting/            # ROIs and gaze-density heatmap renderer
│   ├── models.py             # Validated shared contracts
│   ├── privacy.py            # Consent and atomic session-manifest support
│   └── errors.py             # Actionable domain exceptions
├── tests/                    # Offline unit tests; no hardware required
├── examples/                 # User-operated acquisition and processing snippets
├── docs/                     # Architecture and validity guidance
├── pyproject.toml            # Extras keep device stacks optional
├── LICENSE                   # Apache-2.0
└── README.md                 # Quickstart and contribution guide
```

## Extension rules

| Change | Correct location | Required guardrail |
| --- | --- | --- |
| New headset transport | `devices/` | Preserve raw versus device-derived provenance; lazy-import optional dependencies |
| New eye tracker | `gaze/` | Document coordinate origin, calibration, validation error, and drift policy |
| New EEG feature | `analysis/` | Return `MetricResult`; declare channels, band/window, quality and artifact policy |
| New packaging element | `reporting/roi.py` | Give it stable ID, stimulus ID, semantic label, and version |
| New visual output | `reporting/` | Avoid color schemes that imply a mental-state diagnosis or causal conclusion |

## References

[1]: https://developer.neurosky.com/docs/doku.php?id=thinkgear_communications_protocol "ThinkGear Communications Protocol"
[2]: https://github.com/kitschpatrol/Brain "kitschpatrol Brain Arduino Library"
[3]: https://github.com/kitschpatrol/brain-grapher "kitschpatrol BrainGrapher"
[4]: https://docs.openbci.com/ForDevelopers/SoftwareDevelopment/ "OpenBCI Software Development"
[5]: https://brainflow.readthedocs.io/en/stable/SupportedBoards.html "BrainFlow Supported Boards"
[6]: https://labstreaminglayer.readthedocs.io/info/time_synchronization.html "Lab Streaming Layer Time Synchronization"
[7]: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python "MediaPipe Face Landmarker for Python"
[8]: https://github.com/esdalmaijer/PyGaze "PyGaze Source Repository"
[9]: https://www.unesco.org/en/legal-affairs/recommendation-ethics-neurotechnology "UNESCO Recommendation on the Ethics of Neurotechnology"
