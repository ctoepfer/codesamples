# SPDX-License-Identifier: Apache-2.0
"""Independent parser for the documented ThinkGear serial packet format.

No NeuroSky SDK code or binary is bundled. The parser handles packet framing,
checksums, known values, and forward-compatible skipping of unknown DataRows.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from typing import Final

from packscope.devices.base import BandPowerSnapshot
from packscope.errors import DeviceProtocolError

_SYNC: Final[int] = 0xAA
_MAX_PAYLOAD_LENGTH: Final[int] = 169
_EXCODE: Final[int] = 0x55
_POOR_SIGNAL: Final[int] = 0x02
_ATTENTION: Final[int] = 0x04
_MEDITATION: Final[int] = 0x05
_RAW_WAVE: Final[int] = 0x80
_EEG_POWER_FLOAT: Final[int] = 0x81
_ASIC_EEG_POWER: Final[int] = 0x83
_BAND_NAMES: Final[tuple[str, ...]] = (
    "delta",
    "theta",
    "low_alpha",
    "high_alpha",
    "low_beta",
    "high_beta",
    "low_gamma",
    "mid_gamma",
)


@dataclass(frozen=True, slots=True)
class ThinkGearPacket:
    """Decoded values from one valid ThinkGear packet."""

    timestamp_monotonic_s: float
    poor_signal: int | None = None
    attention: int | None = None
    meditation: int | None = None
    raw_wave: int | None = None
    band_powers: dict[str, float] = field(default_factory=dict)
    unknown_codes: tuple[int, ...] = ()

    def as_band_snapshot(self, device_id: str) -> BandPowerSnapshot | None:
        """Expose device-calculated bands with clear relative-measurement provenance."""
        if not self.band_powers:
            return None
        flags = () if self.poor_signal in (None, 0) else ("nonzero_poor_signal",)
        return BandPowerSnapshot(
            timestamp_monotonic_s=self.timestamp_monotonic_s,
            source="thinkgear",
            device_id=device_id,
            bands=self.band_powers,
            signal_quality=self.poor_signal,
            attention=self.attention,
            meditation=self.meditation,
            quality_flags=flags,
        )


class ThinkGearParser:
    """Incrementally decode ThinkGear packets from arbitrary serial byte chunks."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.valid_packets = 0
        self.invalid_checksums = 0
        self.invalid_lengths = 0

    def feed(self, data: bytes | bytearray, received_at_monotonic_s: float | None = None) -> list[ThinkGearPacket]:
        """Consume bytes and return each complete, checksum-valid packet in order.

        A bad header or checksum drops only one byte before resynchronizing. This
        preserves the chance to recover a valid sync sequence that overlaps a
        corrupted packet.
        """
        timestamp = time.monotonic() if received_at_monotonic_s is None else received_at_monotonic_s
        self._buffer.extend(data)
        packets: list[ThinkGearPacket] = []

        while True:
            sync_at = self._buffer.find(bytes((_SYNC, _SYNC)))
            if sync_at < 0:
                # Retain a trailing sync byte because its partner may arrive next.
                self._buffer[:] = self._buffer[-1:] if self._buffer[-1:] == bytes((_SYNC,)) else b""
                return packets
            if sync_at > 0:
                del self._buffer[:sync_at]
            if len(self._buffer) < 3:
                return packets

            payload_length = self._buffer[2]
            if payload_length > _MAX_PAYLOAD_LENGTH:
                self.invalid_lengths += 1
                del self._buffer[0]
                continue

            packet_length = 4 + payload_length
            if len(self._buffer) < packet_length:
                return packets

            payload = bytes(self._buffer[3 : 3 + payload_length])
            checksum = self._buffer[3 + payload_length]
            expected = (~sum(payload)) & 0xFF
            if checksum != expected:
                self.invalid_checksums += 1
                del self._buffer[0]
                continue

            del self._buffer[:packet_length]
            packets.append(self._decode_payload(payload, timestamp))
            self.valid_packets += 1

    @staticmethod
    def _decode_payload(payload: bytes, timestamp_monotonic_s: float) -> ThinkGearPacket:
        values: dict[int, bytes] = {}
        unknown_codes: list[int] = []
        index = 0
        while index < len(payload):
            excode_level = 0
            while index < len(payload) and payload[index] == _EXCODE:
                excode_level += 1
                index += 1
            if index >= len(payload):
                raise DeviceProtocolError("ThinkGear payload ended after an EXCODE byte.")

            code = payload[index]
            index += 1
            if code < 0x80:
                value_length = 1
            else:
                if index >= len(payload):
                    raise DeviceProtocolError("ThinkGear multi-byte DataRow lacks a value length.")
                value_length = payload[index]
                index += 1
            if index + value_length > len(payload):
                raise DeviceProtocolError("ThinkGear DataRow exceeds the validated payload boundary.")

            value = payload[index : index + value_length]
            index += value_length
            if excode_level == 0 and code in {
                _POOR_SIGNAL,
                _ATTENTION,
                _MEDITATION,
                _RAW_WAVE,
                _EEG_POWER_FLOAT,
                _ASIC_EEG_POWER,
            }:
                values[code] = value
            else:
                unknown_codes.append(code)

        band_powers: dict[str, float] = {}
        if _ASIC_EEG_POWER in values:
            raw_bands = values[_ASIC_EEG_POWER]
            if len(raw_bands) != 24:
                raise DeviceProtocolError("ASIC EEG power DataRow must contain exactly 24 bytes.")
            band_powers = {
                name: float(int.from_bytes(raw_bands[offset : offset + 3], "big"))
                for offset, name in zip(range(0, 24, 3), _BAND_NAMES, strict=True)
            }
        elif _EEG_POWER_FLOAT in values:
            raw_bands = values[_EEG_POWER_FLOAT]
            if len(raw_bands) != 32:
                raise DeviceProtocolError("Floating EEG power DataRow must contain exactly 32 bytes.")
            decoded = struct.unpack(">8f", raw_bands)
            band_powers = dict(zip(_BAND_NAMES, decoded, strict=True))

        raw_wave: int | None = None
        if _RAW_WAVE in values:
            raw_value = values[_RAW_WAVE]
            if len(raw_value) != 2:
                raise DeviceProtocolError("Raw-wave DataRow must contain exactly two bytes.")
            raw_wave = int.from_bytes(raw_value, byteorder="big", signed=True)

        return ThinkGearPacket(
            timestamp_monotonic_s=timestamp_monotonic_s,
            poor_signal=_read_single_byte(values, _POOR_SIGNAL),
            attention=_read_single_byte(values, _ATTENTION),
            meditation=_read_single_byte(values, _MEDITATION),
            raw_wave=raw_wave,
            band_powers=band_powers,
            unknown_codes=tuple(unknown_codes),
        )


def _read_single_byte(values: dict[int, bytes], code: int) -> int | None:
    value = values.get(code)
    if value is None:
        return None
    if len(value) != 1:
        raise DeviceProtocolError(f"ThinkGear code 0x{code:02X} must contain one byte.")
    return value[0]
