from __future__ import annotations

import pytest

from brewpanel.hardware.safety import (
    ActuatorCall,
    ConfirmationDenied,
    ConfirmationRequired,
    SafetyGate,
)


@pytest.mark.asyncio
async def test_confirm_raises_when_no_handler_registered() -> None:
    gate = SafetyGate()
    call = ActuatorCall(device_id="dev-1", method_name="set_heater", args=(True,), kwargs={})
    with pytest.raises(ConfirmationRequired):
        await gate.confirm(call)


@pytest.mark.asyncio
async def test_confirm_records_audit_entry_on_approval() -> None:
    gate = SafetyGate()
    gate.set_confirmation_handler(lambda call: _approve())
    call = ActuatorCall(device_id="dev-1", method_name="set_heater", args=(True,), kwargs={})

    approved = await gate.confirm(call)

    assert approved is True
    assert len(gate.audit_log) == 1
    assert gate.audit_log[0].call is call
    assert gate.audit_log[0].approved is True


@pytest.mark.asyncio
async def test_confirm_records_audit_entry_on_denial() -> None:
    gate = SafetyGate()
    gate.set_confirmation_handler(lambda call: _deny())
    call = ActuatorCall(device_id="dev-1", method_name="set_heater", args=(True,), kwargs={})

    approved = await gate.confirm(call)

    assert approved is False
    assert gate.audit_log[0].approved is False


async def _approve() -> bool:
    return True


async def _deny() -> bool:
    return False


@pytest.mark.asyncio
async def test_requires_confirmation_decorator_end_to_end() -> None:
    from brewpanel.hardware.device import Device
    from brewpanel.hardware.safety import requires_confirmation

    class _Toy(Device):
        def __init__(self, safety_gate: SafetyGate) -> None:
            super().__init__("toy-1", "Toy", safety_gate=safety_gate)
            self.on = False

        async def connect(self) -> None:
            self._connected = True

        async def disconnect(self) -> None:
            self._connected = False

        @requires_confirmation
        async def set_on(self, value: bool) -> None:
            self.on = value

    gate = SafetyGate()
    toy = _Toy(gate)

    # No handler registered yet: fails closed.
    with pytest.raises(ConfirmationRequired):
        await toy.set_on(True)
    assert toy.on is False

    # Denied: raises, state unchanged.
    gate.set_confirmation_handler(lambda call: _deny())
    with pytest.raises(ConfirmationDenied):
        await toy.set_on(True)
    assert toy.on is False

    # Approved: actually runs.
    gate.set_confirmation_handler(lambda call: _approve())
    await toy.set_on(True)
    assert toy.on is True
