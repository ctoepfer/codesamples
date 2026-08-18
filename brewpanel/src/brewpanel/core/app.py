"""The composition root: wires the event bus, safety gate, and both plugin
registries into one object that the GUI (or a CLI, or a test) constructs once.
"""

from __future__ import annotations

from ..features.registry import FeatureRegistry
from ..hardware.registry import DeviceRegistry
from ..hardware.safety import SafetyGate
from .events import EventBus


class Application:
    def __init__(self) -> None:
        self.events = EventBus()
        self.safety_gate = SafetyGate()
        self.devices = DeviceRegistry()
        self.features = FeatureRegistry()

    def bootstrap(self) -> None:
        """Discover every device and feature plugin, then let each feature wire itself up.

        Call this once at startup, after `set_confirmation_handler` has been
        wired to something real if any actuator calls are expected to succeed.
        """
        self.devices.discover()
        self.features.discover()
        for plugin in self.features.all():
            plugin.feature_cls(self).register()
