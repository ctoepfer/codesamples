"""A NiceGUI confirmation dialog wired directly into the safety gate.

Install this as the application's confirmation handler so every actuator call
(anything wrapped with `hardware.safety.requires_confirmation`) pops a real
dialog in front of the operator, instead of the gate failing closed with
`ConfirmationRequired` because nothing answered it.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from ...hardware.safety import ActuatorCall, SafetyGate


def install_confirmation_dialog(safety_gate: "SafetyGate") -> None:
    async def handler(call: "ActuatorCall") -> bool:
        loop = asyncio.get_running_loop()
        result: asyncio.Future[bool] = loop.create_future()

        with ui.dialog() as dialog, ui.card():
            ui.label(f"Confirm: {call.method_name} on {call.device_id}").classes("text-lg font-semibold")
            if call.args or call.kwargs:
                ui.label(f"args={call.args!r} kwargs={call.kwargs!r}").classes("text-sm text-gray-500")
            with ui.row():
                ui.button("Cancel", on_click=lambda: _resolve(dialog, result, False))
                ui.button("Confirm", color="negative", on_click=lambda: _resolve(dialog, result, True))
        dialog.open()
        return await result

    safety_gate.set_confirmation_handler(handler)


def _resolve(dialog: ui.dialog, result: "asyncio.Future[bool]", value: bool) -> None:
    dialog.close()
    if not result.done():
        result.set_result(value)
