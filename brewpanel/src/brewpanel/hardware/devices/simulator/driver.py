"""A pure-software fake brew controller.

No real hardware, no external dependencies. Exists so the rest of the
application (GUI, safety gate, telemetry logging) can be developed and
exercised end-to-end -- including the actuator/confirmation path -- without
risking real equipment. This is the reference implementation to copy when
building a real controller driver (see grainfather/driver.py for the stub
version of the same shape).
"""

from __future__ import annotations

import random

from ...device import Device
from ...safety import SafetyGate, requires_confirmation
from ...types import Measurement, TimerState


class SimulatorDevice(Device):
    def __init__(
        self,
        device_id: str = "simulator-1",
        display_name: str = "Simulated Brew Controller",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)
        self._target_c = 66.0
        self._current_c = 20.0
        self._heater = False
        self._pump = False
        self._timer_total = 0
        self._timer_remaining = 0
        self._timer_active = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    # --- read capabilities ------------------------------------------------

    async def get_temperature(self) -> Measurement:
        # Drift toward target while the heater is on, and toward ambient otherwise,
        # so the simulator feels alive on a dashboard instead of static.
        if self._heater:
            self._current_c += max(0.0, self._target_c - self._current_c) * 0.1
        else:
            self._current_c -= max(0.0, self._current_c - 20.0) * 0.02
        self._current_c += random.uniform(-0.05, 0.05)
        return Measurement(value=round(self._current_c, 2), unit="celsius", source_device_id=self.device_id)

    async def get_gravity(self) -> Measurement:
        return Measurement(value=round(random.uniform(1.010, 1.050), 3), unit="sg", source_device_id=self.device_id)

    # --- actuator capabilities ---------------------------------------------

    async def get_target_temperature(self) -> Measurement:
        return Measurement(value=self._target_c, unit="celsius", source_device_id=self.device_id)

    @requires_confirmation
    async def set_target_temperature(self, celsius: float) -> None:
        self._target_c = celsius

    async def get_heater_state(self) -> bool:
        return self._heater

    @requires_confirmation
    async def set_heater(self, on: bool) -> None:
        self._heater = on

    async def get_pump_state(self) -> bool:
        return self._pump

    @requires_confirmation
    async def set_pump(self, on: bool) -> None:
        self._pump = on

    async def get_timer(self) -> TimerState:
        return TimerState(active=self._timer_active, remaining_seconds=self._timer_remaining, total_seconds=self._timer_total)

    @requires_confirmation
    async def set_timer(self, seconds: int) -> None:
        self._timer_total = seconds
        self._timer_remaining = seconds
        self._timer_active = True

    @requires_confirmation
    async def cancel_timer(self) -> None:
        self._timer_active = False
        self._timer_remaining = 0
