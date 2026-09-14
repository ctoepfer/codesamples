# SPDX-License-Identifier: Apache-2.0
"""Read live Arduino Brain CSV output and print validated JSON snapshots.

Usage:
    python -m pip install 'packscope[serial]'
    python examples/parse_mindflex_arduino.py --port /dev/ttyACM0 --baud 9600

This script expects an Arduino sketch based on the Brain library to print one
readCSV() line per update. It does not write data to disk or make mental-state
claims; use it first to confirm wiring and signal-quality values.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict

from packscope.devices import ArduinoBrainSerialConfig, ArduinoBrainSerialSource
from packscope.errors import OptionalDependencyError


def main() -> int:
    """Poll the Arduino bridge until interrupted by the operator."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=9_600)
    args = parser.parse_args()

    source = ArduinoBrainSerialSource(ArduinoBrainSerialConfig(args.port, args.baud))
    try:
        source.start()
    except OptionalDependencyError as error:
        parser.error(str(error))
    try:
        while True:
            snapshot = source.read_snapshot()
            if snapshot is not None:
                print(json.dumps(asdict(snapshot), sort_keys=True, default=str))
            time.sleep(0.01)
    except KeyboardInterrupt:
        return 0
    finally:
        source.stop()


if __name__ == "__main__":
    raise SystemExit(main())
