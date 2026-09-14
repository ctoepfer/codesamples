# SPDX-License-Identifier: Apache-2.0
"""Offline bottle-share pilot for homebrewers and craft producers; all data synthetic."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from packscope.analysis.sensory_join import SensoryAttribution, join_attributions_with_sensory
from packscope.models import MetricStatus
from packscope.pipeline.runner import SessionRunner
from packscope.reporting.animation import render_gaze_scanpath_animation
from packscope.reporting.roi import NormalizedRect, RegionOfInterest
from packscope.sensory.models import BlindingType
from packscope.testing.synthetic import generate_synthetic_sensory_ratings

LABELS = ("Vintage Botanical Stout", "Minimalist Modern Stout")


def _label_background(output_dir: Path, variant: int) -> str | None:
    """Draw a small schematic label locally when the optional Pillow extra is present."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    image = Image.new("RGB", (180, 240), "#f4f0e6" if variant == 0 else "white")
    draw = ImageDraw.Draw(image)
    if variant == 0:
        draw.rectangle((8, 8, 171, 231), outline="#36534a", width=2)
        for x in (22, 158):
            draw.line((x, 70, x, 190), fill="#36534a", width=2)
            for y in range(80, 180, 20):
                draw.ellipse((x - 8, y, x + 8, y + 8), outline="#36534a")
        title = "VINTAGE\nBOTANICAL\nSTOUT"
    else:
        draw.rectangle((12, 12, 168, 35), fill="#333333")
        draw.line((24, 165, 155, 165), fill="#333333", width=2)
        title = "MINIMALIST\nMODERN\nSTOUT"
    draw.multiline_text((40, 95), title, fill="#222222", spacing=8)
    draw.text((28, 205), "SYNTHETIC LABEL v1", fill="#333333")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"label-{variant + 1}.png"
    image.resize((540, 720)).save(path)
    return str(path)


def main(argv: list[str] | None = None) -> int:
    """Print descriptive tables and optionally save a GIF for each synthetic label."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("homebrew_demo_output"))
    args = parser.parse_args(argv)
    fixture = generate_synthetic_sensory_ratings(session_count=3)
    # Participants see the labels in this scenario: record OPEN, never claim double-blinding.
    protocols = {
        key: replace(
            protocol,
            protocol_version="bottle-share-open-v1",
            blinding_type=BlindingType.OPEN,
            counterbalanced_order=False,
        )
        for key, protocol in fixture.protocols.items()
    }
    attributions = []
    rejected_frames = total_frames = 0
    for key, frames in fixture.eeg_frames.items():
        rating = next(r for r in fixture.ratings if (r.session_id, r.variant_id) == key)
        roi = RegionOfInterest("label", "Label panel", NormalizedRect(0, 0, 1, 1), rating.stimulus_id, "v1")
        summary = SessionRunner().run(frames, fixture.gaze_samples[key], [roi])
        rejected_frames += summary.rejected_eeg_frames
        total_frames += summary.eeg_frame_count
        attributions.extend(
            SensoryAttribution(*key, rating.stimulus_id, rating.product_id, a) for a in summary.roi_attributions
        )
    result = join_attributions_with_sensory(
        attributions, fixture.ratings, consents=fixture.consents, protocols=protocols
    )
    print("Homebrew bottle-share: two label designs, one synthetic stout recipe.")
    print("For homebrewers, craft soda makers, microbreweries and artisan package designers.\n")
    print("SYNTHETIC DATA ONLY — a fun, low-stakes workflow demonstration.")
    print("Post-exposure taste scores are supplied fixtures, never estimated from EEG or gaze.")
    print("Protocol: open label exposure, fixed demonstration order, 60-second declared washout.\n")
    if result.status != MetricStatus.AVAILABLE:
        print(f"Summary unavailable: {result.reason}")
        return 2
    summary = result.value
    print("Session | Label design (v1) | Gaze dwell (s) | FAA | Post-exposure hedonic (1–9)")
    print("--- | --- | --- | --- | ---")
    for row in summary.rows:
        label = LABELS[0 if "variant-0" in row.variant_id else 1]
        dwell = row.gaze_dwell_s
        seconds = f"{sum(dwell.value.roi_dwell_s.values()):.2f}" if dwell.value is not None else str(dwell.reason)
        faa = row.eeg_metrics[0]
        power = f"{faa.value:.3f}" if faa.value is not None else str(faa.reason)
        hedonic = row.hedonic_rating.value if row.hedonic_rating.value is not None else row.hedonic_rating.reason
        print(f"{row.session_id} | {label} | {seconds} | {power} | {hedonic}")
    print(f"\nN={summary.n} session/variant observations from 3 synthetic participants; repeated variants are paired.")
    print(
        f"EEG frames rejected: {rejected_frames}/{total_frames}; missing ratings: {summary.missing_rating_count}; "
        f"rejected ratings: {summary.rejected_rating_count}"
    )
    print(f"Rejection reasons: {summary.rejection_reasons or 'none'}\n")
    for variant in range(2):
        key = "synthetic-session-0", f"synthetic-variant-{variant}@v1"
        output = args.output_dir / f"label-{variant + 1}-scanpath.gif"
        background = _label_background(args.output_dir, variant)
        animation = render_gaze_scanpath_animation(
            list(fixture.gaze_samples[key]), background_image_path=background, output_path=str(output)
        )
        if animation.status == MetricStatus.AVAILABLE:
            print(f"{LABELS[variant]}: {animation.value} (normalized label viewport)")
        else:
            print(
                f"{LABELS[variant]} animation unavailable: {animation.reason}. {animation.details.get('message', '')}"
            )
    print("\nUse these tables to plan club bottle-shares or taproom pilots, not to rank labels by neural liking.")
    print("This open synthetic scenario cannot establish that packaging changes flavor perception.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
