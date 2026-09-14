# SPDX-License-Identifier: Apache-2.0
"""Optional pyserial source for direct MindFlex and ThinkGear-compatible streams."""

from __future__ import annotations

from dataclasses import dataclass

from packscope.devices.base import BandPowerSnapshot, DeviceCapabilities
from packscope.devices.thinkgear import ThinkGearParser
from packscope.errors import ConfigurationError, OptionalDependencyError


@dataclass(frozen=True, slots=True)
class ThinkGearSerialConfig:
    """Serial transport configuration; verify the baud rate for the hardware modification."""

    port: str
    baud_rate: int = 57_600
    device_id: str = "thinkgear-serial"
    read_size: int = 4_096


class ThinkGearSerialSource:
    """Read a direct ThinkGear byte stream without bundling a vendor SDK."""

    def __init__(self, config: ThinkGearSerialConfig) -> None:
        if config.baud_rate <= 0 or config.read_size <= 0:
            raise ConfigurationError("baud_rate and read_size must be positive.")
        self._config = config
        self._serial: object | None = None
        self._parser = ThinkGearParser()

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            source_name="thinkgear_serial",
            raw_eeg=True,
            frontal_asymmetry_possible=False,
            has_signal_quality=True,
            sample_rate_hz=None,
            notes=(
                "Single-channel ThinkGear data cannot produce bilateral F3/F4 alpha asymmetry.",
                "Band powers and eSense values are device-supplied relative measurements.",
            ),
        )

    def start(self) -> None:
        """Open the serial port with a short timeout suitable for event-loop polling."""
        if self._serial is not None:
            raise ConfigurationError("The ThinkGear serial source is already running.")
        try:
            import serial
        except ImportError as error:
            raise OptionalDependencyError("pyserial", "serial") from error
        self._serial = serial.Serial(self._config.port, self._config.baud_rate, timeout=0.0)

    def stop(self) -> None:
        """Close the serial port if it was opened."""
        if self._serial is not None:
            self._serial.close()  # type: ignore[union-attr]
            self._serial = None

    def read_snapshots(self) -> list[BandPowerSnapshot]:
        """Return each newly decoded band snapshot; raw-wave-only packets are omitted."""
        if self._serial is None:
            raise ConfigurationError("Call start() before reading from ThinkGear serial.")
        waiting = int(self._serial.in_waiting)  # type: ignore[union-attr]
        if waiting == 0:
            return []
        packets = self._parser.feed(self._serial.read(min(waiting, self._config.read_size)))  # type: ignore[union-attr]
        return [
            snapshot for packet in packets if (snapshot := packet.as_band_snapshot(self._config.device_id)) is not None
        ]
