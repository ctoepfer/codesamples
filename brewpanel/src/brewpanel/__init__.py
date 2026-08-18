"""brewpanel: a modular brewing control panel.

Structured as a modular monolith -- one deployable application, organized
into independently-pluggable modules:

- `brewpanel.hardware` -- the standardized device interface library, with one
  plugin folder per piece of equipment under `hardware/devices/`.
- `brewpanel.features` -- application-level feature plugins under `features/`.
- `brewpanel.core` -- the composition root wiring devices, features, the
  event bus, and the safety gate together (`core.app.Application`).
- `brewpanel.gui` -- the NiceGUI-based dashboard.

See the top-level README.md for the full architecture overview and the
"how to add a new device" / "how to add a new feature" guides.
"""

from .core.app import Application

__all__ = ["Application"]
