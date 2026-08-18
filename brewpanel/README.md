# brewpanel

A modular brewing control panel: a standardized hardware interface library plus a pluggable GUI, covering the equipment documented in [`docs/hardware/`](../docs/hardware/README.md) (Grainfather, RAPT, Tilt, Plaato, Inkbird, Nespresso, BrewPiLess, Brewblox, iSpindel).

**Status:** early scaffold. The plugin architecture, safety gate, and three real device drivers (a simulator, Tilt, and iSpindel) are working and tested — including an end-to-end test of iSpindel's real local HTTP receiver via an actual POST request. The remaining six devices are correctly-shaped stubs, ready to be filled in one at a time. The GUI's dashboard construction and confirmation-dialog wiring were verified to import and build cleanly against a real NiceGUI install, but the live interactive parts (the simulator card's polling timer, an actual confirmation dialog round-trip in a browser) were **not** exercised end-to-end in this environment — run it and expect to fix small NiceGUI-API drift.

## Architecture: a modular monolith

One deployable application, organized into modules with clear boundaries instead of one flat pile of code or a constellation of separate services:

```
src/brewpanel/
  hardware/       # the standardized device interface library
    types.py         Measurement, TimerState, DeviceInfo, RiskLevel, Transport
    capabilities.py  Protocol contracts: TemperatureSensor, HeaterControl, ...
    device.py        Device base class (connect/disconnect lifecycle)
    safety.py        SafetyGate + @requires_confirmation -- see "Safety model" below
    registry.py       DeviceRegistry: discovers devices/<id>/ plugin folders
    devices/
      simulator/      pure-software fake controller -- fully working
      tilt/           real passive-BLE driver -- fully working
      ispindel/       real local-HTTP-receiver driver -- fully working
      grainfather/    stub -- see docs/hardware/grainfather.md
      rapt/           stub -- see docs/hardware/rapt.md
      plaato/         stub -- see docs/hardware/plaato.md
      inkbird/        stub -- see docs/hardware/inkbird.md
      nespresso/      stub -- see docs/hardware/nespresso.md
      brewpiless/     stub -- see docs/hardware/brewpiless.md
      brewblox/       stub -- see docs/hardware/brewblox.md
  features/       # application-level feature plugins, same discovery pattern
    registry.py       FeatureRegistry: discovers features/<id>/ plugin folders
    telemetry_logger/  reference feature: CSV audit log of all telemetry
  core/           # composition root
    app.py            Application: wires devices + features + event bus + safety gate
    events.py         tiny async pub/sub EventBus
  gui/            # NiceGUI dashboard (optional -- requires the `gui` extra)
  cli.py          # `brewpanel devices` / `brewpanel gui`
```

The **hardware library has zero required dependencies** and works standalone (`pip install -e .`, no extras) for anything that doesn't need a specific transport. Each device's transport dependency (`bleak` for BLE, `aiohttp`/`httpx` for HTTP) is an optional extra, and the **GUI itself is optional** (`gui` extra) -- `core` and `hardware` never import anything under `gui/`, so headless/CLI/scripted use never needs NiceGUI installed.

## Standardization: how a Grainfather and a Tilt end up with the same `get_temperature()`

`docs/hardware/*.md` documents nine completely different wire protocols -- comma-delimited ASCII over BLE, iBeacon manufacturer-data frames, a JSON REST API, a block-patch MQTT event bus. The point of `brewpanel.hardware.capabilities` is that none of that leaks past the driver:

```python
from brewpanel.hardware.capabilities import TemperatureSensor

# True for a Grainfather driver, a Tilt driver, an iSpindel driver, ... regardless
# of transport, as long as the class implements `async def get_temperature(self) -> Measurement`.
isinstance(some_device, TemperatureSensor)
```

Every reading is a `hardware.types.Measurement` (`value`, `unit`, `timestamp`, optional `raw_value`, `source_device_id`) with internal values always in Celsius / specific gravity, matching the "keep internal state metric, convert only for display" guidance repeated across the hardware docs. A driver author doesn't need to invent a return shape -- they implement the matching protocol method and the rest of the application (GUI, telemetry logger, tests) already knows what to do with it.

Capabilities are split into **read** (`TemperatureSensor`, `GravitySensor`, `BatteryReporting`, `SignalStrengthReporting` -- always safe to call) and **actuator** (`TargetTemperatureControl`, `HeaterControl`, `PumpControl`, `TimerControl` -- state-changing, see below).

## Safety model

Every hardware reference in `docs/hardware/` repeats some version of the same warning: heater, pump, setpoint, mode, and firmware operations need explicit confirmation and an audit trail, and several real devices in that collection (BrewPiLess in particular) have little or no authentication of their own to fall back on.

`brewpanel.hardware.safety` makes that structural instead of a convention every driver author has to remember:

```python
class MyDevice(Device):
    @requires_confirmation
    async def set_heater(self, on: bool) -> None:
        ...  # actually talk to the hardware
```

`@requires_confirmation` routes the call through a `SafetyGate`, which:

1. **Fails closed** -- raises `ConfirmationRequired` if nothing has registered a confirmation handler. There is no way to accidentally ship a build where actuator calls silently succeed with no one watching.
2. Awaits the registered handler's approve/deny decision (`ConfirmationDenied` if declined).
3. Records every attempt -- approved or denied -- in `SafetyGate.audit_log`.

The GUI wires a real confirmation dialog (`gui/components/confirm_dialog.py`) into the gate. Tests and scripts wire an auto-approve or auto-deny stub. Either way, no driver can bypass it.

## Adding a new device

1. Create `src/brewpanel/hardware/devices/<device_id>/`.
2. `driver.py`: subclass `hardware.device.Device`, implement `connect()`/`disconnect()`, and whichever capability protocols apply -- wrap every actuator method with `@requires_confirmation`.
3. `__init__.py`: export a module-level `PLUGIN = DevicePlugin(info=DeviceInfo(...), driver_cls=YourDevice)`. Set `docs_reference` to the matching file under `docs/hardware/`.
4. That's it -- `DeviceRegistry.discover()` finds it automatically via `pkgutil.iter_modules`; nothing else needs to import or list it.

The seven stub devices already in this repo (`grainfather/`, `rapt/`, `plaato/`, `inkbird/`, `nespresso/`, `brewpiless/`, `brewblox/`) are the exact shape to copy -- and the `simulator/`, `tilt/`, and `ispindel/` drivers are the exact shape a *working* implementation should end up as.

## Adding a new feature

Same pattern, under `src/brewpanel/features/<feature_id>/`, exporting a `PLUGIN = FeaturePlugin(info=FeatureInfo(...), feature_cls=YourFeature)`. A feature class takes the `Application` instance in `__init__` and does its actual wiring (event subscriptions, background tasks) in `register()`. See `features/telemetry_logger/` for the reference example.

## Running it

```bash
python -m pip install -e .              # hardware library + CLI, no transport extras
python -m pip install -e ".[tilt]"       # + real Tilt BLE support
python -m pip install -e ".[gui]"        # + the NiceGUI dashboard
python -m pip install -e ".[all,dev]"    # everything, plus test dependencies

brewpanel devices -v    # list the discovered device catalog
brewpanel gui            # launch the dashboard (requires the `gui` extra)

pytest                   # run the test suite (requires the `dev` extra)
```

## Notes on `docs/hardware/`

Device manifests reference `docs/hardware/*.md` at the repo root by relative path (e.g. `docs/hardware/tilt.md`). Those files are present in this working tree but are git-ignored (see the repo's top-level `.gitignore`) -- treat them as local reference material, not a hard runtime dependency. They're independent interoperability research, not official vendor documentation; read the "evidence tier" note at the top of each file before trusting a specific claim.
