"""Standardized capability contracts.

Each capability is a `typing.Protocol` describing one thing a device might be
able to do (read a temperature, drive a heater, ...). A driver doesn't declare
which protocols it implements -- it just implements the matching methods, and
capability detection is structural (`isinstance(device, TemperatureSensor)`
works via `@runtime_checkable`).

This is the actual "standardization" layer requested for this library: a
Grainfather driver and a Tilt driver both expose `get_temperature()` returning
a `Measurement` in Celsius, even though on the wire one is a comma-delimited
ASCII BLE record and the other is a decoded iBeacon `major` field.

Capabilities are split into two families:

* **Read capabilities** -- safe to call at any time, never routed through the
  safety gate.
* **Actuator capabilities** -- change physical device state. Every method on
  these protocols is expected to be wrapped with
  `brewpanel.hardware.safety.requires_confirmation` in the concrete driver.
  This mirrors the Low/Medium/High risk tiers and "state-changing operation"
  warnings called out throughout docs/hardware/*.md.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Measurement, TimerState

# --- Read capabilities -------------------------------------------------


@runtime_checkable
class TemperatureSensor(Protocol):
    async def get_temperature(self) -> Measurement: ...


@runtime_checkable
class GravitySensor(Protocol):
    async def get_gravity(self) -> Measurement: ...


@runtime_checkable
class BatteryReporting(Protocol):
    async def get_battery(self) -> Measurement: ...


@runtime_checkable
class SignalStrengthReporting(Protocol):
    async def get_rssi(self) -> Measurement: ...


# --- Actuator capabilities ----------------------------------------------
# Every mutating method here MUST be decorated with
# `@requires_confirmation` in the concrete driver. See hardware/safety.py.


@runtime_checkable
class TargetTemperatureControl(Protocol):
    async def get_target_temperature(self) -> Measurement: ...
    async def set_target_temperature(self, celsius: float) -> None: ...


@runtime_checkable
class HeaterControl(Protocol):
    async def get_heater_state(self) -> bool: ...
    async def set_heater(self, on: bool) -> None: ...


@runtime_checkable
class PumpControl(Protocol):
    async def get_pump_state(self) -> bool: ...
    async def set_pump(self, on: bool) -> None: ...


@runtime_checkable
class TimerControl(Protocol):
    async def get_timer(self) -> TimerState: ...
    async def set_timer(self, seconds: int) -> None: ...
    async def cancel_timer(self) -> None: ...


READ_CAPABILITIES: tuple[type, ...] = (
    TemperatureSensor,
    GravitySensor,
    BatteryReporting,
    SignalStrengthReporting,
)

ACTUATOR_CAPABILITIES: tuple[type, ...] = (
    TargetTemperatureControl,
    HeaterControl,
    PumpControl,
    TimerControl,
)

ALL_CAPABILITIES: tuple[type, ...] = READ_CAPABILITIES + ACTUATOR_CAPABILITIES


def detect_capabilities(instance: object) -> frozenset[type]:
    """Structurally detect which capability protocols a live device instance satisfies."""
    return frozenset(cap for cap in ALL_CAPABILITIES if isinstance(instance, cap))
