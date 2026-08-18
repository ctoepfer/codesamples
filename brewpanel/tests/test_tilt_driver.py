from __future__ import annotations

import struct
import uuid

import pytest

from brewpanel.hardware.devices.tilt.driver import TiltDevice, decode_tilt_ibeacon


def _build_payload(color_uuid: str, major: int, minor: int) -> bytes:
    body = uuid.UUID(color_uuid).bytes + struct.pack(">HH", major, minor) + b"\xc5"  # + 1 byte tx power
    return b"\x02\x15" + body


def test_decode_standard_reading() -> None:
    # RED, 68.0F, SG 1.052 (standard scaling: minor/1000)
    payload = _build_payload("a495bb10-c5b1-4b44-b512-1370f02d74de", major=68, minor=1052)
    decoded = decode_tilt_ibeacon(payload)
    assert decoded is not None
    assert decoded["color"] == "RED"
    assert decoded["hd"] is False
    assert decoded["temperature_f"] == 68.0
    assert decoded["specific_gravity"] == 1.052


def test_decode_hd_reading_by_high_minor() -> None:
    # minor > 5000 triggers HD scaling: major/10, minor/10000
    payload = _build_payload("a495bb20-c5b1-4b44-b512-1370f02d74de", major=705, minor=10520)
    decoded = decode_tilt_ibeacon(payload)
    assert decoded is not None
    assert decoded["hd"] is True
    assert decoded["temperature_f"] == 70.5
    assert decoded["specific_gravity"] == 1.052


def test_decode_rejects_unknown_uuid() -> None:
    payload = _build_payload("00000000-0000-0000-0000-000000000000", major=68, minor=1052)
    assert decode_tilt_ibeacon(payload) is None


def test_decode_rejects_short_or_malformed_payload() -> None:
    assert decode_tilt_ibeacon(b"\x00\x00") is None
    assert decode_tilt_ibeacon(b"\x02\x15" + b"\x00" * 10) is None


@pytest.mark.asyncio
async def test_ingest_converts_fahrenheit_to_celsius() -> None:
    device = TiltDevice(device_id="tilt-test")
    device.ingest({"color": "RED", "hd": False, "temperature_f": 68.0, "specific_gravity": 1.052})

    temp = await device.get_temperature()
    gravity = await device.get_gravity()

    assert temp.unit == "celsius"
    assert temp.value == pytest.approx(20.0, abs=0.01)
    assert temp.raw_value == 68.0
    assert gravity.value == 1.052


@pytest.mark.asyncio
async def test_get_temperature_before_any_reading_raises() -> None:
    device = TiltDevice(device_id="tilt-test")
    with pytest.raises(RuntimeError):
        await device.get_temperature()
