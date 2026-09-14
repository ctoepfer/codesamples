# SPDX-License-Identifier: Apache-2.0
"""Small, dependency-light command-line utilities for hardware bring-up."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

from packscope.errors import PackScopeError


def build_parser() -> argparse.ArgumentParser:
    """Build the public PackScope command parser."""
    parser = argparse.ArgumentParser(prog="packscope", description="PackScope local utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    arduino = subparsers.add_parser(
        "decode-arduino-csv", help="decode one Arduino Brain readCSV() line from stdin or --line"
    )
    arduino.add_argument("--line", help="one eleven-column Arduino Brain CSV line")
    arduino.add_argument("--device-id", default="mindflex-arduino")
    subparsers.add_parser("doctor", help="check installed optional extras without connecting to hardware")
    manifest = subparsers.add_parser("validate-manifest", help="validate version-one manifest provenance")
    manifest.add_argument("path", type=Path)
    for command in ("run-quality-gates", "compute-faa"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("path", type=Path)
        command_parser.add_argument("--sampling-rate-hz", type=float)
        command_parser.add_argument("--window-s", type=float, default=4.0)
        command_parser.add_argument("--min-duration-s", type=float, default=2.0)
        command_parser.add_argument("--max-absolute-amplitude", type=float)
        command_parser.add_argument("--saturation-amplitude", type=float)
        command_parser.add_argument("--max-saturation-fraction", type=float, default=0.01)
        command_parser.add_argument("--line-noise-hz", type=float, choices=(50.0, 60.0), default=50.0)
        command_parser.add_argument("--max-line-noise-ratio", type=float)
        command_parser.add_argument("--flatline-duration-s", type=float)
    heatmap = subparsers.add_parser("generate-heatmap", help="render calibrated gaze density from a JSON log")
    heatmap.add_argument("path", type=Path)
    heatmap.add_argument("--output", type=Path, required=True)
    scanpath = subparsers.add_parser("animate-scanpath", help="export a calibrated gaze replay as GIF or MP4")
    scanpath.add_argument("--gaze-file", type=Path, required=True)
    scanpath.add_argument("--stimulus", type=Path)
    scanpath.add_argument("--output", type=Path, required=True)
    scanpath.add_argument("--fps", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Decode a known Arduino Brain CSV line to JSON for transport troubleshooting."""
    args = build_parser().parse_args(argv)
    if args.command != "decode-arduino-csv":
        try:
            return _run_command(args)
        except (PackScopeError, OSError, ValueError, TypeError, KeyError) as error:
            print(f"PackScope: {error}", file=sys.stderr)
            return 2
    if args.command == "decode-arduino-csv":
        line = args.line if args.line is not None else sys.stdin.readline()
        if not line:
            print("No CSV line received on stdin.", file=sys.stderr)
            return 2
        try:
            from packscope.devices.arduino_csv import ArduinoBrainCsvDecoder

            snapshot = ArduinoBrainCsvDecoder(device_id=args.device_id).decode_line(line)
        except PackScopeError as error:
            print(f"Decode failed: {error}", file=sys.stderr)
            return 2
        print(json.dumps(asdict(snapshot), sort_keys=True, default=str))
        return 0
    return 2


def _run_command(args: argparse.Namespace) -> int:
    if args.command == "animate-scanpath":
        from packscope.io.logs import read_gaze_log
        from packscope.models import MetricStatus
        from packscope.reporting.animation import render_gaze_scanpath_animation

        result = render_gaze_scanpath_animation(read_gaze_log(args.gaze_file),
                                                str(args.stimulus) if args.stimulus else None,
                                                str(args.output), args.fps)
        print(json.dumps(asdict(result), indent=2, allow_nan=False))
        return 0 if result.status == MetricStatus.AVAILABLE else 2
    if args.command == "doctor":
        extras = {
            "brainflow": ("brainflow",),
            "lsl": ("pylsl",),
            "serial": ("serial",),
            "webcam": ("mediapipe", "cv2"),
            "reporting": ("PIL", "matplotlib", "numpy"),
        }
        print("Extra | Installed modules (runtime/device readiness is not tested)")
        print("--- | ---")
        for extra, modules in extras.items():
            missing = [name for name in modules if importlib.util.find_spec(name) is None]
            print(f"{extra} | " + ("missing: " + ", ".join(missing) if missing else "available"))
        return 0
    if args.command == "validate-manifest":
        from packscope.io.logs import read_payload
        from packscope.io.serialization import from_dict
        from packscope.privacy import SessionManifest

        payload = read_payload(args.path)
        if isinstance(payload, dict) and "type" not in payload:
            metadata_names = ("stimulus_hash", "software_version", "quality_flags", "calibration_id", "consent_scopes")
            metadata = {key: payload[key] for key in metadata_names}
            data = {
                key: value
                for key, value in payload.items()
                if key not in ("stimulus_hash", "consent_scopes", "schema_version")
            }
            payload = {
                "schema_version": payload["schema_version"],
                "type": "SessionManifest",
                "metadata": metadata,
                "data": data,
            }
        if not isinstance(from_dict(payload), SessionManifest):
            raise ValueError("Expected a SessionManifest.")
        print("Manifest valid (schema version 1; provenance fields verified).")
        return 0
    if args.command == "generate-heatmap":
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError as error:
            from packscope.errors import OptionalDependencyError

            raise OptionalDependencyError("matplotlib/numpy", "reporting") from error
        from packscope.io.logs import read_gaze_log

        samples = [s for s in read_gaze_log(args.path) if s.valid and s.calibration_id and not s.quality_flags]
        if not samples:
            raise ValueError("No valid calibrated gaze samples available.")
        density, _, _ = np.histogram2d(
            [s.y_norm for s in samples], [s.x_norm for s in samples], bins=64, range=((0, 1), (0, 1))
        )
        figure, axis = plt.subplots()
        try:
            plotted = axis.imshow(density, origin="upper", extent=(0, 1, 1, 0), cmap="viridis")
            axis.set(xlabel="Normalized x", ylabel="Normalized y", title="Gaze sample density")
            figure.colorbar(plotted, ax=axis, label="Sample count")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            figure.savefig(args.output)
        finally:
            plt.close(figure)
        print(f"Rendered {len(samples)} calibrated samples to {args.output}")
        return 0
    from packscope.analysis.quality import EegQualityConfig, assess_eeg_quality
    from packscope.analysis.spectral import frontal_alpha_asymmetry
    from packscope.io.logs import read_eeg_log

    config = EegQualityConfig(
        **{
            key: getattr(args, key)
            for key in (
                "min_duration_s",
                "max_absolute_amplitude",
                "saturation_amplitude",
                "max_saturation_fraction",
                "line_noise_hz",
                "max_line_noise_ratio",
                "flatline_duration_s",
            )
        }
    )
    frames = read_eeg_log(args.path, sampling_rate_hz=args.sampling_rate_hz, window_s=args.window_s)
    if args.command == "compute-faa":
        results = [
            {
                "start_time_s": frame.start_time_s,
                "end_time_s": frame.end_time_s,
                "result": asdict(frontal_alpha_asymmetry(frame, quality_config=config)),
            }
            for frame in frames
        ]
        print(json.dumps(results, indent=2, allow_nan=False))
    else:
        reports = [assess_eeg_quality(frame, config) for frame in frames]
        rejected = sum(not report.passed for report in reports)
        total_samples = sum(frame.samples.shape[1] for frame in frames)
        rejected_samples = sum(
            frame.samples.shape[1] for frame, report in zip(frames, reports, strict=True) if not report.passed
        )
        print(
            json.dumps(
                {
                    "window_count": len(frames),
                    "rejected_windows": rejected,
                    "rejection_ratio": rejected / len(frames) if frames else None,
                    "sample_count": total_samples,
                    "rejected_samples": rejected_samples,
                    "sample_rejection_ratio": rejected_samples / total_samples if total_samples else None,
                    "accepted_window_indices": [i for i, r in enumerate(reports) if r.passed],
                    "windows": [asdict(report) for report in reports],
                },
                indent=2,
                allow_nan=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
