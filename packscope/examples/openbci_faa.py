# SPDX-License-Identifier: Apache-2.0
"""Compute a quality-gated FAA convention from a user-mapped OpenBCI Cyton stream.

Usage:
    python -m pip install 'packscope[brainflow]'
    python examples/openbci_faa.py --port /dev/ttyUSB0

Set F3 and F4 to the physical Cyton channels in the montage used for the session.
The output is a spectral convention only, not an affective or clinical finding.
"""

from __future__ import annotations

import argparse
import time

from packscope.analysis import frontal_alpha_asymmetry
from packscope.devices import BrainFlowConfig, BrainFlowEegSource


def main() -> int:
    """Acquire one four-second raw EEG block and calculate FAA if quality permits."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, help="BrainFlow Cyton serial port")
    parser.add_argument("--f3-index", type=int, required=True, help="physical channel index mapped to F3")
    parser.add_argument("--f4-index", type=int, required=True, help="physical channel index mapped to F4")
    args = parser.parse_args()

    source = BrainFlowEegSource(
        BrainFlowConfig(
            board_id="CYTON_BOARD",
            serial_port=args.port,
            channel_labels={args.f3_index: "F3", args.f4_index: "F4"},
            device_id="openbci-cyton",
        )
    )
    source.start()
    try:
        # Cyton runs at 250 Hz. Accumulate at least four seconds before a single
        # buffered read so the default two-second quality gate can pass.
        time.sleep(4.2)
        frame = source.read_frame(max_samples=2_000)
        if frame is None:
            parser.error("No EEG data arrived. Check the OpenBCI GUI and serial port first.")
        # Production recording should retain every block and calculate condition
        # contrasts against a participant-specific baseline.
        print(frontal_alpha_asymmetry(frame))
    finally:
        source.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
