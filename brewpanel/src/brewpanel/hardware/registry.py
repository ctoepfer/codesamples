"""Device plugin discovery.

Adding a new piece of equipment is a matter of adding a folder under
`brewpanel/hardware/devices/<device_id>/` -- no central list to edit. Each
device package's `__init__.py` exports a module-level `PLUGIN` object; at
startup, `DeviceRegistry.discover()` walks the `devices` package with
`pkgutil.iter_modules`, imports every submodule, and collects whatever
`PLUGIN` it finds. See `hardware/devices/simulator/__init__.py` for the
minimal example, or `docs/hardware-plugins.md` in this project for the full
how-to.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass

from . import devices as _devices_pkg
from .device import Device
from .types import DeviceInfo


@dataclass(frozen=True, slots=True)
class DevicePlugin:
    info: DeviceInfo
    driver_cls: type[Device]


class DeviceRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, DevicePlugin] = {}

    def discover(self) -> None:
        """Import every submodule of `hardware.devices` and register its `PLUGIN`, if any."""
        for module_info in pkgutil.iter_modules(_devices_pkg.__path__, prefix=f"{_devices_pkg.__name__}."):
            module = importlib.import_module(module_info.name)
            plugin = getattr(module, "PLUGIN", None)
            if plugin is None:
                continue
            if not isinstance(plugin, DevicePlugin):
                raise TypeError(f"{module_info.name}.PLUGIN must be a DevicePlugin, got {type(plugin)!r}")
            self._plugins[plugin.info.device_id] = plugin

    def register(self, plugin: DevicePlugin) -> None:
        """Register a plugin directly, bypassing discovery (useful in tests)."""
        self._plugins[plugin.info.device_id] = plugin

    def all(self) -> list[DevicePlugin]:
        return sorted(self._plugins.values(), key=lambda p: p.info.display_name)

    def implemented(self) -> list[DevicePlugin]:
        return [p for p in self.all() if p.info.implemented]

    def get(self, device_id: str) -> DevicePlugin:
        return self._plugins[device_id]

    def create(self, device_id: str, **kwargs: object) -> Device:
        """Instantiate a driver for the given device id. Raises KeyError if unknown."""
        plugin = self.get(device_id)
        return plugin.driver_cls(**kwargs)  # type: ignore[arg-type]
