from __future__ import annotations

from brewpanel.features.registry import FeatureRegistry
from brewpanel.hardware.registry import DeviceRegistry

EXPECTED_DEVICE_IDS = {
    "simulator-1",
    "tilt-1",
    "ispindel-1",
    "grainfather-1",
    "rapt-1",
    "plaato-1",
    "inkbird-1",
    "nespresso-1",
    "brewpiless-1",
    "brewblox-1",
}

EXPECTED_IMPLEMENTED = {"simulator-1", "tilt-1", "ispindel-1"}


def test_discover_finds_every_device_plugin() -> None:
    registry = DeviceRegistry()
    registry.discover()
    found_ids = {plugin.info.device_id for plugin in registry.all()}
    assert found_ids == EXPECTED_DEVICE_IDS


def test_implemented_devices_match_expectations() -> None:
    registry = DeviceRegistry()
    registry.discover()
    implemented_ids = {plugin.info.device_id for plugin in registry.implemented()}
    assert implemented_ids == EXPECTED_IMPLEMENTED


def test_every_device_has_a_docs_reference_or_is_local_only() -> None:
    registry = DeviceRegistry()
    registry.discover()
    for plugin in registry.all():
        if plugin.info.device_id == "simulator-1":
            continue  # pure-software, no external hardware doc
        assert plugin.info.docs_reference.startswith("docs/hardware/")


def test_create_instantiates_the_driver() -> None:
    registry = DeviceRegistry()
    registry.discover()
    device = registry.create("simulator-1")
    assert device.device_id == "simulator-1"


def test_feature_registry_discovers_telemetry_logger() -> None:
    registry = FeatureRegistry()
    registry.discover()
    feature_ids = {plugin.info.feature_id for plugin in registry.all()}
    assert "telemetry_logger" in feature_ids
