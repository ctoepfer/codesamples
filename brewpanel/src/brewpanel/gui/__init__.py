"""NiceGUI-based dashboard. Requires the `gui` extra (`pip install -e ".[gui]"`).

Deliberately not imported from `brewpanel/__init__.py` or `brewpanel/core/` --
the hardware library and core app must work with zero GUI dependencies
installed, for headless/CLI/scripted use.
"""
