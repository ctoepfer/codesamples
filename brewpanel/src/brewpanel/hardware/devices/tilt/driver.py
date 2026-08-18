"""Passive BLE iBeacon listener for a Tilt hydrometer.

Read-only by design -- see docs/hardware/tilt.md: "No normal Tilt command
protocol exists." Tilt is a transmitter, not an actuator, so this driver
implements only the read capabilities and never touches the safety gate.

The decode logic (UUID -> color, `major`/`minor` -> temperature/gravity,
including the HD-variant scaling rule) is ported verbatim from the reference
decoder in docs/hardware/tilt.md section 1 -- keep the two in sync if either
changes. `decode_tilt_ibeacon` has no dependency on `bleak` and is unit
tested directly; only `connect()` needs a real BLE adapter.
"""

from __future__ import annotations

import struct
import uuid
from datetime import datetime, timezone
from typing import TypedDict

from ...device import Device
from ...safety import SafetyGate
from ...types import Measurement

TILT_COLORS: dict[str, str] = {
    "a495bb10-c5b1-4b44-b512-1370f02d74de": "RED",
    "a495bb20-c5b1-4b44-b512-1370f02d74de": "GREEN",
    "a495bb30-c5b1-4b44-b512-1370f02d74de": "BLACK",
    "a495bb40-c5b1-4b44-b512-1370f02d74de": "PURPLE",
    "a495bb50-c5b1-4b44-b512-1370f02d74de": "ORANGE",
    "a495bb60-c5b1-4b44-b512-1370f02d74de": "BLUE",
    "a495bb70-c5b1-4b44-b512-1370f02d74de": "YELLOW",
    "a495bb80-c5b1-4b44-b512-1370f02d74de": "PINK",
}

APPLE_COMPANY_ID = 0x004C


class DecodedTilt(TypedDict):
    color: str
    hd: bool
    temperature_f: float
    specific_gravity: float


def decode_tilt_ibeacon(payload: bytes) -> DecodedTilt | None:
    """Decode an iBeacon manufacturer-data payload into a Tilt reading, or None if it isn't one."""
    if len(payload) < 23 or payload[:2] != b"\x02\x15":
        return None
    beacon_uuid = str(uuid.UUID(bytes=payload[2:18])).lower()
    color = TILT_COLORS.get(beacon_uuid)
    if color is None:
        return None
    major, minor = struct.unpack(">HH", payload[18:22])
    is_hd = minor > 5000 or (major == 999 and minor in {1005, 1006, 1007})
    return {
        "color": color,
        "hd": is_hd,
        "temperature_f": major / 10 if is_hd else float(major),
        "specific_gravity": minor / 10_000 if is_hd else minor / 1_000,
    }


class TiltDevice(Device):
    def __init__(
        self,
        device_id: str,
        display_name: str = "Tilt Hydrometer",
        *,
        address: str | None = None,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)
        self._address = address.lower() if address else None
        self._latest_temp: Measurement | None = None
        self._latest_gravity: Measurement | None = None
        self._scanner = None  # bleak.BleakScanner, created lazily in connect()

    async def connect(self) -> None:
        try:
            from bleak import BleakScanner
        except ImportError as exc:  # pragma: no cover - exercised only without the extra installed
            raise RuntimeError(
                "The 'bleak' package is required for Tilt support. Install with: pip install 'brewpanel[tilt]'"
            ) from exc
        self._scanner = BleakScanner(detection_callback=self._on_advertisement)
        await self._scanner.start()
        self._connected = True

    async def disconnect(self) -> None:
        if self._scanner is not None:
            await self._scanner.stop()
            self._scanner = None
        self._connected = False

    def _on_advertisement(self, bt_device: object, advertisement_data: object) -> None:
        address = getattr(bt_device, "address", "")
        if self._address is not None and address.lower() != self._address:
            return
        manufacturer_data = getattr(advertisement_data, "manufacturer_data", {})
        payload = manufacturer_data.get(APPLE_COMPANY_ID)
        if payload is None:
            return
        decoded = decode_tilt_ibeacon(payload)
        if decoded is None:
            return
        self.ingest(decoded)

    def ingest(self, decoded: DecodedTilt) -> None:
        """Update internal state from a decoded reading. Public so it's directly testable without BLE."""
        now = datetime.now(timezone.utc)
        temp_c = (decoded["temperature_f"] - 32) * 5 / 9
        self._latest_temp = Measurement(
            value=round(temp_c, 2),
            unit="celsius",
            raw_value=decoded["temperature_f"],
            timestamp=now,
            source_device_id=self.device_id,
        )
        self._latest_gravity = Measurement(
            value=decoded["specific_gravity"],
            unit="sg",
            timestamp=now,
            source_device_id=self.device_id,
        )

    async def get_temperature(self) -> Measurement:
        if self._latest_temp is None:
            raise RuntimeError(f"{self.device_id}: no Tilt advertisement received yet")
        return self._latest_temp

    async def get_gravity(self) -> Measurement:
        if self._latest_gravity is None:
            raise RuntimeError(f"{self.device_id}: no Tilt advertisement received yet")
        return self._latest_gravity
