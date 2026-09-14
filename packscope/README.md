# PackScope

*Seeing what the data can — and cannot — tell us.*

Created by Charles Toepfer of Pacific Brewing Supplies.

PackScope grew out of a simple question: if eye tracking can tell us where someone looked, and EEG can tell us something about what was happening in the recorded signal at the same moment, can the two be combined in a useful way for packaging and advertising research? The answer is **yes — with some important limits**.

**PackScope** is a local-first Python toolkit for collecting, aligning, quality-checking, and analyzing gaze and EEG data around versioned visual stimuli such as labels, packages, ads, and other design treatments. It helps researchers compare label and ad variants using calibrated gaze, timestamped brain signals, and explicit uncertainty checks — preserving provenance, uncertainty, and the distinction between **what was measured** and **what we think it might mean**.

Historically, this kind of combined eye-tracking and EEG research has largely lived in the world of **large consumer brands, specialized market-research and neuromarketing firms, and well-equipped academic or corporate labs** — organizations with the budgets for dedicated hardware, proprietary analysis platforms, and commissioned studies. PackScope explores what happens when some of those tools and methods are made accessible to **homebrewers, small breweries, independent package designers, and curious makers** using open software and comparatively approachable hardware. It is not intended to turn a hobbyist setup into a commercial neuroscience laboratory; the goal is to make careful, useful experimentation possible without hiding the limitations of the equipment or the evidence.

> **PackScope does not read minds.** It does not diagnose emotion, determine intent, predict purchases, or prove that a package element caused a neurological response. Its purpose is to provide transparent, quality-gated evidence that can be used alongside traditional design research.

![Participant viewing packaging variants while EEG and gaze data are recorded](docs/images/gpt-image-2.5-sunburst_Sophisticated_editorial_scientific_illustration_for_an_open-source_research_proj-0.jpg)

*PackScope combines visual-stimulus research with time-aligned EEG and gaze measurements while keeping interpretation separate from observation.*

The project supports three distinct EEG input paths from the first commit:

| Input path | PackScope integration | What it provides | What it cannot provide |
| --- | --- | --- | --- |
| **MindFlex / NeuroSky / ThinkGear** | Direct pyserial source and independent documented packet parser | Poor signal, eSense fields, raw wave if emitted, relative device-derived bands | Bilateral F3/F4 alpha asymmetry or a validated psychological score |
| **MindFlex + Arduino Brain** | Strict decoder and pyserial source for the upstream `readCSV()` eleven-column output | Signal quality, Attention/Meditation fields, relative eight-band snapshots | Raw bilateral EEG; an Arduino bridge does not make the one-electrode device multichannel |
| **OpenBCI** | Optional BrainFlow source with explicit channel-to-electrode mapping | Timestamped raw multichannel EEG frames and PSD features; FAA only with both mapped F3 and F4 | Automatic electrode-location inference or universal data quality claims |
| **Existing LSL stream** | Optional LSL source with unambiguous discovery | Timestamped raw EEG frame for a declared channel schema | Guaranteed synchronization merely because the data arrived through LSL |

The gaze layer is equally explicit. It uses a top-left-origin normalized coordinate space, requires a recorded calibration, and can accept either an external dedicated tracker adapter or an optional MediaPipe webcam feature extractor. MediaPipe landmarks are input features—not validated gaze points—and are not turned into gaze coordinates until a display calibration has been fit.[1]

---

## The Idea

Traditional packaging research can answer many useful questions directly:

- Which package did a participant choose?
- Which claim did they remember?
- Which design was easier to find on a shelf?
- Which version did they say they preferred?

Eye tracking adds another dimension: **where did they actually look, and for how long?**

EEG can add a second stream of time-aligned physiological data. Depending on the hardware, that may include raw multi-channel brainwave recordings, spectral power estimates, device-derived band values, or proprietary fields such as NeuroSky's Attention and Meditation outputs.

PackScope's job is not to turn those measurements into a single magic score. Instead, it keeps the layers separate and lets a researcher ask better questions.

```mermaid
flowchart LR
    S[Visual stimulus\nlabel / package / ad] --> G[Gaze data]
    S --> E[EEG data]
    G --> C[Calibration + quality checks]
    E --> Q[Signal quality + spectral analysis]
    C --> F[Fixations]
    Q --> W[Metric windows]
    F --> A[Time + ROI attribution]
    W --> A
    A --> R[Transparent comparison\nacross stimulus variants]
```

## Why This Architecture

The supplied packaging article proposes a two-axis "emotional response" / "cognitive response" map and links it to eye tracking. That is a potentially useful **hypothesis-generation** pattern for comparing label treatments, artwork, claims, typography, and information hierarchy. It is not enough evidence to treat a beta/theta ratio, frontal alpha asymmetry (FAA), or a webcam landmark as a direct read-out of emotion, confusion, attention, or buying intent.

PackScope therefore keeps four things separate: device-derived bands, raw EEG signal features, calibrated gaze allocation, and hypothesis-only visualization labels. It will return a typed unavailable result rather than calculate FAA from a single MindFlex electrode, or splice gaze across invalid/dropped samples.

See [the architecture document](docs/ARCHITECTURE.md) for the data-flow diagram, contracts, hardware design, and extension rules. See [the validity and safety guide](docs/VALIDITY_AND_SAFETY.md) before collecting participant data.

## What We Measure

It is tempting to reduce physiological and gaze measurements to simple axes such as "emotional response" or "cognitive response." Visualizations like that can be useful for generating hypotheses, but PackScope deliberately avoids treating broad psychological labels as directly measurable facts.

Instead, PackScope works with observable or explicitly derived quantities.

![Packaging research measurements kept as separate signal, gaze, spectral, and ROI layers](docs/images/gpt-image-2.5-sunburst_Clean_scientific_editorial_infographic_showing_how_packaging_research_measuremen-1.jpg)

*The useful inputs are kept distinct: recorded signals, derived features, calibrated gaze, and versioned regions of interest. None is automatically translated into an emotion or intent.*

| Layer | Examples | What it can support | What it does **not** establish |
| --- | --- | --- | --- |
| **Gaze** | calibrated x/y position, fixation duration, ROI dwell time | what part of the stimulus was visually examined | why the participant looked there |
| **EEG signal** | raw channels, PSD, alpha/beta/theta power | changes in recorded neural signal features | a specific emotion or purchase intention |
| **Device-derived metrics** | ThinkGear Attention, Meditation, relative bands | comparison of the device's own outputs | independently validated attention or calmness |
| **Combined attribution** | fixation overlaps a valid EEG metric window | what was being viewed when a signal feature occurred | causation between the viewed element and the signal |

### A safer replacement for the "emotion quadrant"

Rather than labeling quadrants as *Confusion*, *Interest*, *Easy Enjoyment*, or *Unengaged*, PackScope favors a descriptive comparison space.

```mermaid
quadrantChart
    title Example descriptive comparison — not an emotion classifier
    x-axis Lower baseline-relative feature --> Higher baseline-relative feature
    y-axis Lower gaze dwell --> Higher gaze dwell
    quadrant-1 High dwell / higher feature
    quadrant-2 High dwell / lower feature
    quadrant-3 Low dwell / lower feature
    quadrant-4 Low dwell / higher feature
```

The labels stay deliberately neutral. Interpretation belongs in the research context, not in the measurement pipeline.

## Architecture at a Glance

```mermaid
flowchart LR
    H[MindFlex / NeuroSky\nThinkGear or Arduino CSV] --> P[Relative band snapshot]
    O[OpenBCI via BrainFlow] --> R[Raw EEG frames]
    L[Existing LSL stream] --> R
    W[Dedicated tracker or\ncalibrated webcam features] --> G[Normalized gaze samples]
    R --> Q[Quality gates + PSD features]
    G --> F[Fixation detector]
    F --> A[ROI attribution]
    Q --> A
    A --> T[Transparent tables]
    F --> M[Gaze-density heatmap]
```

---

## Quickstart

### Prerequisites

Install Python 3.11 or later. The default package requires only NumPy and SciPy. Device, webcam, LSL, reporting, and development dependencies are optional, which keeps a clean checkout usable without hardware or proprietary SDKs.

```bash
git clone https://github.com/your-org/packscope.git
cd packscope
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,reporting]'
pytest
ruff check .
```

Install only the integrations required for a local experiment.

```bash
# Direct ThinkGear serial or Arduino Brain USB serial
python -m pip install -e '.[serial]'

# OpenBCI and other BrainFlow-supported boards
python -m pip install -e '.[brainflow]'

# Lab Streaming Layer; liblsl may also be required by the operating system
python -m pip install -e '.[lsl]'

# Experimental webcam landmark feature extraction
python -m pip install -e '.[webcam]'
```

## Getting the Data

PackScope supports several EEG acquisition paths because the available hardware can vary dramatically in capability.

### MindFlex / NeuroSky / ThinkGear

A MindFlex-class device can provide signal-quality information, proprietary eSense outputs, relative band snapshots, and — on some paths — raw samples. It is inexpensive and useful for experimentation, but it is still a single-electrode consumer device.

That matters. A single electrode cannot be treated like a multi-channel research EEG system, and it cannot provide bilateral measurements such as F3/F4 frontal alpha asymmetry.

```python
from packscope.devices import ThinkGearParser

parser = ThinkGearParser()
with open("captured-thinkgear.bin", "rb") as stream:
    for packet in parser.feed(stream.read()):
        snapshot = packet.as_band_snapshot(device_id="mindflex-a")
        if snapshot is not None:
            print(snapshot.signal_quality, snapshot.bands["theta"])
```

The finite-state parser validates packet length and checksum before exposing any values. It keeps documented `0xAA 0xAA` framing, unknown data rows, and malformed-packet recovery outside the rest of the analysis pipeline.[6]

### MindFlex + Arduino Brain

PackScope can also consume the common Arduino Brain CSV stream. This is useful for inexpensive experimental setups and provides a straightforward serial path into the toolkit.

The Arduino bridge does not add electrodes or increase what the headset itself measures. It simply provides another way to obtain the device output.

The adapter accepts the documented `readCSV()` field order from the [kitschpatrol Brain Arduino library](https://github.com/kitschpatrol/Brain):

```bash
packscope decode-arduino-csv --line '0,51,40,1,2,3,4,5,6,7,8'
```

A successful result is JSON with `signal_quality`, `attention`, `meditation`, and the eight device-derived relative band values. In this upstream library, `0` is good signal and `200` is no signal. PackScope does not reinterpret Attention or Meditation as independently validated metrics.[2]

Configure a user-owned Arduino sketch using the upstream Brain library to emit one `readCSV()` row per update. The default bridge baud rate is `9600`, matching the BrainGrapher example; pass a different baud rate if the sketch uses one.[3]

```bash
python examples/parse_mindflex_arduino.py --port /dev/ttyACM0 --baud 9600
```

For exact serial wiring and sketch setup, see [the Arduino bridge guide](examples/arduino_brain_csv/README.md). The Arduino Brain library is LGPL-3.0 and is **not** included, linked, or redistributed by PackScope; the PackScope adapter reads the plain serial output after it reaches the host.[2]

### OpenBCI / BrainFlow

With explicitly mapped channels, OpenBCI hardware provides raw multi-channel EEG data suitable for spectral analysis and metrics that actually require multiple electrodes.

For example, PackScope can compute the convention:

```text
ln(alpha power F4) - ln(alpha power F3)
```

—but only when both F3 and F4 are explicitly present and the data window passes the required quality checks.

First verify a stable hardware signal in the OpenBCI GUI, as OpenBCI recommends, then explicitly state which physical channels are mounted at F3 and F4. Cyton, Cyton+Daisy, and Ganglion have different channel/rate trade-offs documented by BrainFlow.[4] [5]

```bash
python examples/openbci_faa.py \
  --port /dev/ttyUSB0 \
  --f3-index 0 \
  --f4-index 1
```

The script returns `ln(alpha_power(F4)) - ln(alpha_power(F3))` only when both named channels are present and the window passes basic quality gates. It does not label that scalar "positive emotion," "negative emotion," or "engagement."

```python
from packscope.analysis import frontal_alpha_asymmetry
from packscope.models import EegFrame

# frame must be raw, contemporaneous data with explicit F3 and F4 channel labels.
result = frontal_alpha_asymmetry(frame)
if result.value is None:
    print(f"Metric unavailable: {result.reason}")
else:
    print(f"FAA convention = {result.value:.4f}")
```

`MetricResult` always carries an availability status and reason. A one-channel ThinkGear/MindFlex path returns `insufficient_channels`; it will not produce a misleading asymmetry score.

### Existing LSL streams

PackScope can also consume a declared Lab Streaming Layer EEG stream, allowing it to participate in larger experimental setups without owning every device integration itself.

---

## Eye Tracking: Knowing What Was on Screen

EEG alone does not tell us what a participant was looking at.

The gaze side of PackScope uses a normalized coordinate system tied to the actual displayed stimulus. A dedicated eye tracker can provide gaze data directly through an adapter. An experimental webcam path can instead extract eye/iris features with MediaPipe, but those features do not become valid gaze coordinates until they have been calibrated against known positions on the display.

A typical calibration uses five or nine known points:

```text
●-----------------------●
|                       |
|          ●            |
|                       |
●-----------------------●
```

PackScope records the calibration and its error rather than assuming that a detected iris position automatically equals a point on screen.

```python
import numpy as np
from packscope.gaze import AffineGazeCalibration

# Raw features might be left/right iris landmark x/y values or vendor coordinates.
# Targets are points rendered on the actual physical stimulus display.
features = np.array(
    [
        [0.12, 0.10, 0.18, 0.10],
        [0.82, 0.10, 0.88, 0.10],
        [0.12, 0.80, 0.18, 0.80],
        [0.82, 0.80, 0.88, 0.80],
        [0.47, 0.45, 0.53, 0.45],
    ]
)
targets = np.array([[0.1, 0.1], [0.9, 0.1], [0.1, 0.9], [0.9, 0.9], [0.5, 0.5]])
calibration = AffineGazeCalibration.fit(features, targets)
print(calibration.validation.percentile_95_error_norm)
```

Use five or nine targets, immediately validate against known display points, save the error summary, repeat drift checks, and treat a webcam result as exploratory unless it is validated for the operating conditions.[7]

---

## From a Package to Regions of Interest

A package image can be divided into versioned **regions of interest (ROIs)** before a study begins.

For a beer label, for example:

```text
┌──────────────────────────────────────┐
│             BRAND / LOGO             │
│                                      │
│             BEER NAME                │
│                                      │
│          [ central artwork ]         │
│                                      │
│  STYLE          ABV          VOLUME  │
└──────────────────────────────────────┘
```

Possible ROIs might include:

- brand mark
- beer name
- illustration
- style descriptor
- ABV
- package claim
- required regulatory copy

Each ROI belongs to a specific stimulus and version. That prevents later analysis from quietly assuming that an area meant the same thing after a label changed.

![Fictional beverage package with gaze fixations, gaze path, and regions of interest](docs/images/gpt-image-2.5-sunburst_Technical_packaging_research_visualization_using_a_fictional_craft_beverage_can_-0.jpg)

*An ROI view turns a package into a versioned research stimulus: gaze can be attributed to defined areas without claiming why the participant looked there.*

```python
from packscope.analysis import attribute_metric_windows, detect_fixations
from packscope.reporting import NormalizedRect, RegionOfInterest

rois = [
    RegionOfInterest(
        roi_id="beer-name",
        label="Beer name",
        bounds=NormalizedRect(0.15, 0.10, 0.70, 0.18),
        stimulus_id="can-v3",
        version="1",
    )
]
fixations = detect_fixations(gaze_samples)
attributions = attribute_metric_windows(metric_windows, fixations, rois)
```

The attribution says only that a valid fixation's dwell time overlapped a metric window. It does not establish why a viewer looked at that region or what that metric "means."

---

## What Happens During a Study

A simple PackScope packaging study can use repeated measures: the same participant views two or more label variants in counterbalanced order.

```mermaid
flowchart TD
    A[Consent + participant code] --> B[Device setup]
    B --> C[Gaze calibration + validation]
    C --> D[Quiet baseline]
    D --> E[Stimulus A]
    E --> F[Short reset / neutral interval]
    F --> G[Stimulus B]
    G --> H[Optional additional variants]
    H --> I[Quality review]
    I --> J[Within-participant comparison]
```

For each trial, PackScope can retain:

- stimulus identity and file hash
- stimulus version
- ROI definitions
- device and channel configuration
- gaze calibration record and error
- EEG sampling details
- timestamps and clock origin
- fixation data
- metric windows
- exclusions and quality failures
- software/version provenance

This is intentionally more tedious than producing a single score. The extra context is what makes later results interpretable.

---

## Linking Gaze and EEG

The interesting part happens when the two streams are aligned in time.

Suppose a participant fixates on a beer name from 8.4 to 9.1 seconds. PackScope can examine which **valid** EEG-derived metric windows overlap that fixation.

```text
Time →       8.0        8.5        9.0        9.5

Gaze       ───────[ BEER NAME FIXATION ]────────

EEG metric     [window A] [window B] [window C]
                  ✓          ✓          ✕
```

That produces a defensible statement such as:

> During a valid fixation on the beer-name ROI, the participant's baseline-relative alpha-band feature differed from the corresponding window in the alternate design.

It does **not** justify:

> The beer name made the participant feel happier.

That distinction is central to PackScope.

---

## Quality Gates Matter More Than a Pretty Graph

Physiological data are noisy. PackScope therefore treats a metric being **unavailable** as a legitimate result.

Examples include:

- insufficient EEG channels
- missing F3 or F4 for a bilateral metric
- invalid or dropped samples
- poor signal quality
- failed gaze calibration
- excessive gaze dropout
- unsupported hardware capability
- a metric window that does not overlap valid data

Rather than manufacture a number, PackScope returns a typed unavailable result with a reason.

```python
result = frontal_alpha_asymmetry(frame)

if result.value is None:
    print(result.reason)
else:
    print(result.value)
```

For research tooling, **"we cannot calculate this from these data" is often the correct answer.**

![EEG and gaze data moving through validation gates before reaching analysis outputs](docs/images/gpt-image-2.5-sunburst_Abstract_scientific_data-pipeline_editorial_illustration._On_the_left_EEG_wavefo-1.jpg)

*PackScope treats validation as part of the analysis. Data that do not meet calibration, channel, or signal-quality requirements are excluded rather than forced into a result.*

---

## A Packaging Example

Imagine three proposed labels for the same beer:

![Two fictional package variants presented side by side for controlled comparison](docs/images/gpt-image-2.5-sunburst_Side-by-side_A_B_packaging_design_research_illustration._Two_fictional_craft_bev-1.jpg)

*Even simple A/B comparisons can isolate meaningful differences in hierarchy, artwork, and information placement before extending the study to additional variants.*

- **A:** large illustration, small style name
- **B:** large beer name, simplified artwork
- **C:** stronger brewery branding with more secondary copy

A PackScope pilot could ask descriptive questions such as:

1. Which ROIs received the longest dwell time?
2. How quickly was the beer name fixated?
3. Was required information actually viewed?
4. Were differences consistent across participants or driven by one subject?
5. Did baseline-relative EEG features differ during comparable ROI fixations?
6. How much usable data remained after quality exclusions?

Those results can then be considered together with preference surveys, recall, shelf-search performance, interviews, or actual choice behavior.

The goal is not to replace those methods. It is to add another carefully documented layer of evidence.

## Suggested Homebrew Packaging Protocol

Start with a repeated-measures pilot: one participant sees two or more label/ad variants in counterbalanced order, with matched exposure time and predefined ROIs. Capture a quiet baseline before the packaging trials, calibrate/validate gaze against the actual screen, and retain quality exclusions. Compare **within-participant, baseline-relative** distributions across variants rather than using absolute universal cutoffs.[8]

| Study step | PackScope component | Required record |
| --- | --- | --- |
| Consent | `SessionConsent` | Pseudonymous participant code, consent document version, specific scopes |
| Stimulus preparation | `RegionOfInterest` | Image hash, stimulus version, ROI ID/version, display geometry |
| Device bring-up | Device source / CLI | Device model, source, sampling rate, channel map, serial or LSL settings |
| Gaze calibration | `AffineGazeCalibration` | Target set, validation error, calibration ID, drift checks, dropout |
| EEG acquisition | `EegFrame` | Montage/reference, units, raw/processed provenance, clock origin, quality flags |
| Analysis | `MetricResult`, `MetricWindow` | PSD band/window, baseline procedure, exclusion reasons, software version |
| Reporting | Heatmap + attribution table | Usable-trial count, missing data, uncertainty, descriptive—not diagnostic—language |

---

## Why PackScope Is Deliberately Conservative

Neuromarketing is attractive partly because it seems to promise access to reactions that people cannot or will not verbalize. That makes it especially easy to overstate what a signal means.

PackScope takes the opposite approach.

It separates:

1. **device output** — what the hardware actually produced;
2. **derived signal features** — what was mathematically calculated;
3. **gaze behavior** — where calibrated gaze was assigned;
4. **attribution** — which valid measurements overlapped in time;
5. **interpretation** — the research hypothesis applied afterward.

That separation makes the software less magical, but much more useful for reproducible work.

## What PackScope Is — and Is Not

### It is

- a transparent analysis toolkit
- a way to combine gaze and EEG timelines
- a framework for versioned visual stimuli and ROIs
- a place to enforce calibration and signal-quality requirements
- a way to compare variants using descriptive measurements
- an experimental platform for packaging and advertising research

### It is not

- an emotion detector
- a lie detector
- a medical or diagnostic system
- a purchase predictor
- an automatic measure of attention
- proof that one visual element caused a physiological change

## The Useful Question Is Usually "What Changed?"

The strongest use of PackScope is not trying to assign an absolute psychological meaning to a number.

It is asking controlled comparative questions:

> When the same person viewed two versions of the same package under the same conditions, what changed in where they looked, how long they looked there, and in the quality-gated physiological features recorded during those moments?

That is a narrower question than "How did this package make them feel?"

It is also a question the data have a much better chance of answering.

---

## Code Structure

```text
src/packscope/
├── analysis/
│   ├── quality.py        # Transparent raw-EEG quality gates
│   ├── spectral.py       # Welch PSD, F3/F4 FAA convention, beta/theta ratio
│   ├── baseline.py       # Within-session robust normalization
│   ├── fixations.py      # Valid-sample I-DT fixation detector
│   └── attribution.py    # Temporal overlap between metric windows and ROIs
├── devices/
│   ├── thinkgear.py      # Independent documented ThinkGear packet parser
│   ├── thinkgear_serial.py
│   ├── arduino_csv.py    # kitschpatrol Brain readCSV decoder
│   ├── arduino_serial.py
│   ├── brainflow.py      # Optional OpenBCI / BrainFlow raw EEG source
│   └── lsl.py            # Optional LSL EEG source
├── gaze/
│   ├── base.py           # Display coordinate and source contracts
│   ├── calibration.py    # Affine feature-to-display calibration
│   ├── mediapipe.py      # Optional iris feature extraction, not gaze inference
│   └── quality.py
├── reporting/
│   ├── roi.py            # Versioned normalized packaging regions
│   └── heatmap.py        # Local gaze-density visualization
├── models.py             # Validated shared data contracts
├── privacy.py            # Consent scopes and atomic session manifest
└── errors.py             # Actionable domain exceptions
```

## Dependency and License Policy

The repository and its original code are released under **Apache License 2.0**, selected because the project involves hardware integration and benefits from Apache's explicit patent grant. It does not bundle a proprietary NeuroSky SDK, device firmware, participant recordings, or captured camera data. The direct ThinkGear decoder is independently written against the published protocol.[6]

Optional integrations have their own licenses and runtime/distribution obligations. BrainFlow is MIT-licensed but contains downstream distribution notices. `pylsl`, NumPy, SciPy, pyserial, MediaPipe, OpenCV, and Pillow must be reviewed in the version actually shipped. PyGaze is GPL-3.0, so it is intentionally not a dependency of this Apache-2.0 core; use it only through a separately reviewed integration or an external LSL bridge.[9] See [NOTICE](NOTICE) for current third-party pointers.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes. In particular, new adapters must state source provenance, units, timestamp origin, licences, hardware capabilities, and raw-versus-processed status. New signal metrics must state channel/montage requirements, quality gates, preprocessing, artifact policy, unavailable conditions, and interpretive limits. Every change needs offline tests; default tests must not require a device or contain participant data.

## License

Copyright 2026 PackScope contributors. Licensed under the [Apache License 2.0](LICENSE).

## References

[1]: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python "MediaPipe Face Landmarker for Python"
[2]: https://github.com/kitschpatrol/Brain "kitschpatrol Brain Arduino Library"
[3]: https://github.com/kitschpatrol/brain-grapher "kitschpatrol BrainGrapher"
[4]: https://docs.openbci.com/ForDevelopers/SoftwareDevelopment/ "OpenBCI Software Development"
[5]: https://brainflow.readthedocs.io/en/stable/SupportedBoards.html "BrainFlow Supported Boards"
[6]: https://developer.neurosky.com/docs/doku.php?id=thinkgear_communications_protocol "ThinkGear Communications Protocol"
[7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11225961/ "Guidelines for minimum reporting of eye-tracking studies"
[8]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10794660/ "Challenges in EEG-based emotion recognition"
[9]: https://github.com/esdalmaijer/PyGaze "PyGaze Source Repository"
