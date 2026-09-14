# SPDX-License-Identifier: Apache-2.0
"""Optional pyserial source for an Arduino emitting Arduino Brain readCSV() lines."""

from __future__ import annotations

from dataclasses import dataclass

from packscope.devices.arduino_csv import ArduinoBrainCsvDecoder
from packscope.devices.base import BandPowerSnapshot, DeviceCapabilities
from packscope.errors import ConfigurationError, DeviceProtocolError, OptionalDependencyError


@dataclass(frozen=True, slots=True)
class ArduinoBrainSerialConfig:
    """USB serial settings for a user-controlled Arduino Brain sketch."""

    port: str
    baud_rate: int = 9_600
    device_id: str = "mindflex-arduino"


class ArduinoBrainSerialSource:
    """Read MindFlex values from a transparent Arduino CSV bridge over USB serial."""

    def __init__(self, config: ArduinoBrainSerialConfig) -> None:
        if config.baud_rate <= 0:
            raise ConfigurationError("baud_rate must be positive.")
        self._config = config
        self._serial: object | None = None
        self._decoder = ArduinoBrainCsvDecoder(device_id=config.device_id)

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            source_name="arduino_brain_csv",
            raw_eeg=False,
            frontal_asymmetry_possible=False,
            has_signal_quality=True,
            sample_rate_hz=1.0,
            notes=(
                "Receives relative ThinkGear band values emitted by the Arduino Brain library.",
                "The bridge does not provide bilateral raw EEG or F3/F4 asymmetry.",
            ),
        )

    def start(self) -> None:
        """Open the USB serial port; call read_snapshot() in a polling loop."""
        if self._serial is not None:
            raise ConfigurationError("The Arduino serial source is already running.")
        try:
            import serial
        except ImportError as error:
            raise OptionalDependencyError("pyserial", "serial") from error
        self._serial = serial.Serial(self._config.port, self._config.baud_rate, timeout=0.0)

    def stop(self) -> None:
        """Close the USB serial port."""
        if self._serial is not None:
            self._serial.close()  # type: ignore[union-attr]
            self._serial = None

    def read_snapshot(self) -> BandPowerSnapshot | None:
        """Decode one available line; malformed lines are rejected without poisoning the stream."""
        if self._serial is None:
            raise ConfigurationError("Call start() before reading from Arduino serial.")
        line = self._serial.readline()  # type: ignore[union-attr]
        if not line:
            return None
        try:
            return self._decoder.decode_line(line)
        except (UnicodeDecodeError, DeviceProtocolError):
            # Serial reconnect banners and interrupted writes are expected in hobby
            # hardware. The decoder count records the failure for session reporting.
            return None
