from __future__ import annotations

import pytest

from brewpanel.hardware.registry import DeviceRegistry


@pytest.mark.asyncio
async def test_every_unimplemented_device_raises_not_implemented_on_connect() -> None:
    registry = DeviceRegistry()
    registry.discover()

    for plugin in registry.all():
        if plugin.info.implemented:
            continue
        device = registry.create(plugin.info.device_id)
        with pytest.raises(NotImplementedError, match=r"docs/hardware/"):
            await device.connect()


@pytest.mark.asyncio
async def test_stub_device_disconnect_is_always_safe() -> None:
    registry = DeviceRegistry()
    registry.discover()

    for plugin in registry.all():
        if plugin.info.implemented:
            continue
        device = registry.create(plugin.info.device_id)
        await device.disconnect()  # must not raise even though never connected
        assert device.is_connected is False
