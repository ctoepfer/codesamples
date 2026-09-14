# SPDX-License-Identifier: Apache-2.0
"""Adapter for the kitschpatrol Arduino Brain library's documented CSV output."""

from __future__ import annotations

import time

from packscope.devices.base import BandPowerSnapshot
from packscope.errors import DeviceProtocolError

# The Arduino Brain library's readCSV() order. Values are device-calculated,
# relative-band outputs—not bilateral raw EEG or a validated psychological metric.
_CSV_COLUMNS = (
    "signal_quality",
    "attention",
    "meditation",
    "delta",
    "theta",
    "low_alpha",
    "high_alpha",
    "low_beta",
    "high_beta",
    "low_gamma",
    "mid_gamma",
)


class ArduinoBrainCsvDecoder:
    """Decode one line emitted by an Arduino running the Brain library example."""

    def __init__(self, device_id: str = "mindflex-arduino") -> None:
        self.device_id = device_id
        self.lines_decoded = 0
        self.lines_rejected = 0

    def decode_line(self, line: str | bytes, received_at_monotonic_s: float | None = None) -> BandPowerSnapshot:
        """Parse strict eleven-column CSV and preserve the host receipt timestamp."""
        if isinstance(line, bytes):
            line = line.decode("ascii", errors="strict")
        fields = [field.strip() for field in line.strip().split(",")]
        if len(fields) != len(_CSV_COLUMNS):
            self.lines_rejected += 1
            raise DeviceProtocolError(
                f"Expected {len(_CSV_COLUMNS)} Arduino Brain CSV columns, received {len(fields)}."
            )
        try:
            values = [int(value) for value in fields]
        except ValueError as error:
            self.lines_rejected += 1
            raise DeviceProtocolError("Arduino Brain CSV contains a non-integer value.") from error

        signal_quality, attention, meditation, *bands = values
        if not 0 <= signal_quality <= 200:
            self.lines_rejected += 1
            raise DeviceProtocolError("MindFlex signal quality must be between 0 and 200.")
        if not 0 <= attention <= 100 or not 0 <= meditation <= 100:
            self.lines_rejected += 1
            raise DeviceProtocolError("MindFlex attention and meditation must be between 0 and 100.")
        if any(value < 0 for value in bands):
            self.lines_rejected += 1
            raise DeviceProtocolError("MindFlex band-power values must be non-negative.")

        flags: tuple[str, ...] = () if signal_quality == 0 else ("nonzero_poor_signal",)
        self.lines_decoded += 1
        return BandPowerSnapshot(
            timestamp_monotonic_s=(time.monotonic() if received_at_monotonic_s is None else received_at_monotonic_s),
            source="arduino_brain_csv",
            device_id=self.device_id,
            bands=dict(zip(_CSV_COLUMNS[3:], map(float, bands), strict=True)),
            signal_quality=signal_quality,
            attention=attention,
            meditation=meditation,
            quality_flags=flags,
        )
