"""NiceGUI entry point.

Run with the CLI: `brewpanel gui`. Requires the `gui` extra:
`pip install -e ".[gui]"`.

NOTE: `build_dashboard()` and the confirmation dialog wiring have been
verified to import and construct cleanly against a real NiceGUI install. The
live interactive parts -- `add_simulator_card()`'s polling timer, an actual
confirmation dialog round-trip in a browser -- have not been exercised
end-to-end in this environment. Run it and expect to fix small NiceGUI-API
drift before relying on it.
"""

from __future__ import annotations

from nicegui import ui

from ..core.app import Application
from .components.confirm_dialog import install_confirmation_dialog


def build_dashboard(app: Application) -> None:
    ui.label("BrewPanel").classes("text-2xl font-bold")
    ui.label("Modular brewing control panel").classes("text-sm text-gray-500")

    with ui.row().classes("gap-4 flex-wrap mt-4"):
        for plugin in app.devices.all():
            info = plugin.info
            with ui.card().classes("w-64"):
                ui.label(info.display_name).classes("text-lg font-semibold")
                ui.label(f"{info.vendor} · {info.transport.value}").classes("text-xs text-gray-500")
                with ui.row():
                    ui.badge("ready" if info.implemented else "not yet implemented",
                             color="positive" if info.implemented else "warning")
                    ui.badge(info.risk.value, color="negative" if info.risk.value == "high" else "grey")
                if info.docs_reference:
                    ui.label(info.docs_reference).classes("text-xs text-gray-400 mt-2")
                if info.notes:
                    ui.label(info.notes).classes("text-xs text-gray-400")


async def add_simulator_card(app: Application) -> None:
    """The one card in this scaffold that's actually live: connects the
    built-in simulator and shows a confirmation-gated heater toggle, so the
    full device -> safety gate -> GUI round trip is demonstrated without
    needing any real hardware.
    """
    plugin = app.devices.get("simulator-1")
    device = plugin.driver_cls(safety_gate=app.safety_gate)
    await device.connect()

    with ui.card().classes("w-64 mt-4"):
        ui.label("Simulator (live)").classes("text-lg font-semibold")
        temp_label = ui.label("-- °C").classes("text-3xl")
        heater_switch = ui.switch("Heater")

        async def on_heater_change(value: bool) -> None:
            try:
                await device.set_heater(value)
            except Exception as exc:  # noqa: BLE001 - surface denial/errors to the operator instead of raising
                ui.notify(str(exc), type="negative")
                heater_switch.value = await device.get_heater_state()

        heater_switch.on_value_change(lambda e: on_heater_change(e.value))

        async def poll() -> None:
            measurement = await device.get_temperature()
            temp_label.text = f"{measurement.value:.1f} °C"

        ui.timer(2.0, poll)


def main() -> None:
    app = Application()
    app.bootstrap()
    install_confirmation_dialog(app.safety_gate)
    build_dashboard(app)
    ui.timer(0.1, lambda: add_simulator_card(app), once=True)
    ui.run(title="BrewPanel", reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
