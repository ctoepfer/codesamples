from __future__ import annotations

import pytest

from brewpanel.hardware.devices.ispindel.driver import ISpindelDevice


@pytest.mark.asyncio
async def test_ingest_populates_readings() -> None:
    device = ISpindelDevice(device_id="ispindel-test")
    device.ingest({"name": "Ferm1", "temperature": 19.8, "temp_units": "C", "battery": 3.98, "gravity": 1.042})

    temp = await device.get_temperature()
    gravity = await device.get_gravity()
    battery = await device.get_battery()

    assert temp.unit == "celsius"
    assert temp.value == 19.8
    assert gravity.value == 1.042
    assert battery.unit == "volts"
    assert battery.value == 3.98


@pytest.mark.asyncio
async def test_ingest_converts_fahrenheit() -> None:
    device = ISpindelDevice(device_id="ispindel-test")
    device.ingest({"temperature": 67.64, "temp_units": "F", "gravity": 1.042})

    temp = await device.get_temperature()
    assert temp.value == pytest.approx(19.8, abs=0.01)
    assert temp.raw_value == 67.64


@pytest.mark.asyncio
async def test_get_readings_before_ingest_raises() -> None:
    device = ISpindelDevice(device_id="ispindel-test")
    with pytest.raises(RuntimeError):
        await device.get_temperature()


def test_default_path_includes_device_id() -> None:
    device = ISpindelDevice(device_id="ferm-1")
    assert device.path == "/ispindel/ferm-1"
