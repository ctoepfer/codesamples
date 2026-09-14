# SPDX-License-Identifier: Apache-2.0
"""Run with python examples/quickstart_synthetic_demo.py after installing PackScope."""

from packscope.pipeline.runner import SessionRunner
from packscope.reporting.roi import NormalizedRect, RegionOfInterest
from packscope.testing.synthetic import generate_eeg_frames, generate_gaze_samples


def main() -> None:
    """Print synthetic measurements and independent spatial attribution."""
    rois = [
        RegionOfInterest("left", "Left panel", NormalizedRect(0, 0, 0.5, 1), "demo", "v1"),
        RegionOfInterest("right", "Right panel", NormalizedRect(0.5, 0, 0.5, 1), "demo", "v1"),
    ]
    summary = SessionRunner().run(generate_eeg_frames(), generate_gaze_samples(), rois)
    print("Synthetic data only; amplitudes are in synthetic units.\n")
    print("Window (s) | Measurement | Status | Value / reason")
    print("--- | --- | --- | ---")
    for window in (*summary.psd_metrics, *summary.faa_metrics):
        metric = window.result
        value = f"{metric.value:.4f}" if metric.value is not None else metric.reason
        print(f"{window.start_time_s:.2f}-{window.end_time_s:.2f} | {metric.name} | {metric.status} | {value}")
    print("\nWindow start (s) | ROI version | Fixation dwell (s)")
    print("--- | --- | ---")
    for attribution in summary.roi_attributions:
        for roi in summary.rois:
            print(
                f"{attribution.metric_window.start_time_s:.2f} | {roi.roi_id}@{roi.version} | "
                f"{attribution.roi_dwell_s.get(roi.roi_id, 0):.3f}"
            )
    print(f"\nRejected EEG frames: {summary.rejected_eeg_frames}/{summary.eeg_frame_count}")
    print(f"Rejected gaze samples: {summary.rejected_gaze_samples}/{summary.gaze_sample_count}")


if __name__ == "__main__":
    main()
