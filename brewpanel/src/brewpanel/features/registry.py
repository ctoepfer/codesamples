"""Feature plugin discovery -- the same pattern as `hardware/registry.py`, applied
to application-level features instead of equipment.

Adding a new feature (an alerting rule, a fermentation-profile scheduler, a
recipe importer, ...) is a matter of adding a folder under
`brewpanel/features/<feature_id>/` whose `__init__.py` exports a `PLUGIN`.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys

from .types import FeaturePlugin


class FeatureRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, FeaturePlugin] = {}

    def discover(self) -> None:
        features_pkg = sys.modules[__package__]
        for module_info in pkgutil.iter_modules(features_pkg.__path__, prefix=f"{features_pkg.__name__}."):
            module = importlib.import_module(module_info.name)
            plugin = getattr(module, "PLUGIN", None)
            if plugin is None:
                continue
            if not isinstance(plugin, FeaturePlugin):
                raise TypeError(f"{module_info.name}.PLUGIN must be a FeaturePlugin, got {type(plugin)!r}")
            self._plugins[plugin.info.feature_id] = plugin

    def register(self, plugin: FeaturePlugin) -> None:
        self._plugins[plugin.info.feature_id] = plugin

    def all(self) -> list[FeaturePlugin]:
        return sorted(self._plugins.values(), key=lambda p: p.info.display_name)
