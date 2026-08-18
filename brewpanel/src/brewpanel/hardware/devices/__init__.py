"""Namespace package holding one subpackage per piece of equipment.

`DeviceRegistry.discover()` (see `hardware/registry.py`) walks this package
with `pkgutil.iter_modules` -- adding a device is purely a matter of adding a
folder here that exports a `PLUGIN` from its `__init__.py`. Nothing outside
this package needs to know a new device folder exists.
"""
