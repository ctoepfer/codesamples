# SPDX-License-Identifier: Apache-2.0
"""Small, dependency-light command-line utilities for hardware bring-up."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from packscope.devices.arduino_csv import ArduinoBrainCsvDecoder
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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Decode a known Arduino Brain CSV line to JSON for transport troubleshooting."""
    args = build_parser().parse_args(argv)
    if args.command == "decode-arduino-csv":
        line = args.line if args.line is not None else sys.stdin.readline()
        if not line:
            print("No CSV line received on stdin.", file=sys.stderr)
            return 2
        try:
            snapshot = ArduinoBrainCsvDecoder(device_id=args.device_id).decode_line(line)
        except PackScopeError as error:
            print(f"Decode failed: {error}", file=sys.stderr)
            return 2
        print(json.dumps(asdict(snapshot), sort_keys=True, default=str))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
