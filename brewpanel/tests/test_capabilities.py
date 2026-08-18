from __future__ import annotations

from brewpanel.hardware.capabilities import (
    GravitySensor,
    HeaterControl,
    PumpControl,
    TargetTemperatureControl,
    TemperatureSensor,
    TimerControl,
    detect_capabilities,
)
from brewpanel.hardware.devices.simulator.driver import SimulatorDevice
from brewpanel.hardware.devices.tilt.driver import TiltDevice


def test_simulator_satisfies_all_capability_protocols() -> None:
    device = SimulatorDevice()
    assert isinstance(device, TemperatureSensor)
    assert isinstance(device, GravitySensor)
    assert isinstance(device, TargetTemperatureControl)
    assert isinstance(device, HeaterControl)
    assert isinstance(device, PumpControl)
    assert isinstance(device, TimerControl)


def test_tilt_only_satisfies_read_capabilities() -> None:
    device = TiltDevice(device_id="tilt-test")
    assert isinstance(device, TemperatureSensor)
    assert isinstance(device, GravitySensor)
    assert not isinstance(device, HeaterControl)
    assert not isinstance(device, PumpControl)


def test_detect_capabilities_matches_isinstance_checks() -> None:
    device = SimulatorDevice()
    detected = detect_capabilities(device)
    assert TemperatureSensor in detected
    assert HeaterControl in detected

    tilt = TiltDevice(device_id="tilt-test")
    tilt_detected = detect_capabilities(tilt)
    assert TemperatureSensor in tilt_detected
    assert HeaterControl not in tilt_detected
