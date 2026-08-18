from __future__ import annotations

import pytest

from brewpanel.hardware.devices.simulator.driver import SimulatorDevice
from brewpanel.hardware.safety import ConfirmationRequired, SafetyGate


async def _approve(call: object) -> bool:
    return True


@pytest.mark.asyncio
async def test_connect_disconnect_lifecycle() -> None:
    device = SimulatorDevice()
    assert device.is_connected is False
    await device.connect()
    assert device.is_connected is True
    await device.disconnect()
    assert device.is_connected is False


@pytest.mark.asyncio
async def test_get_temperature_returns_celsius_measurement() -> None:
    async with SimulatorDevice() as device:
        measurement = await device.get_temperature()
    assert measurement.unit == "celsius"
    assert measurement.source_device_id == "simulator-1"


@pytest.mark.asyncio
async def test_set_heater_requires_confirmation() -> None:
    gate = SafetyGate()
    device = SimulatorDevice(safety_gate=gate)
    await device.connect()

    with pytest.raises(ConfirmationRequired):
        await device.set_heater(True)
    assert await device.get_heater_state() is False

    gate.set_confirmation_handler(_approve)
    await device.set_heater(True)
    assert await device.get_heater_state() is True


@pytest.mark.asyncio
async def test_heater_on_drives_temperature_toward_target() -> None:
    gate = SafetyGate()
    gate.set_confirmation_handler(_approve)
    device = SimulatorDevice(safety_gate=gate)
    await device.connect()

    await device.set_target_temperature(80.0)
    await device.set_heater(True)

    first = await device.get_temperature()
    for _ in range(20):
        latest = await device.get_temperature()
    assert latest.value >= first.value
