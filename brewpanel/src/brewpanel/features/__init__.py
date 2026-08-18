"""Namespace package holding one subpackage per application-level feature.

Mirrors `hardware/devices/`: `FeatureRegistry.discover()` (see
`features/registry.py`) walks this package and collects each subpackage's
`PLUGIN`. See `features/telemetry_logger/` for the reference example.
"""
