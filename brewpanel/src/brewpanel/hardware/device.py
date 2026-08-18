"""Base class every device driver extends."""

from __future__ import annotations

import abc

from .safety import SafetyGate


class Device(abc.ABC):
    """Common lifecycle shared by every device, regardless of transport.

    Subclasses implement whichever capability protocols
    (`brewpanel.hardware.capabilities`) apply to the real hardware -- a
    passive telemetry device like Tilt implements only the read capabilities,
    while a full controller like Grainfather implements read *and* actuator
    capabilities.
    """

    def __init__(self, device_id: str, display_name: str, *, safety_gate: SafetyGate | None = None) -> None:
        self.device_id = device_id
        self.display_name = display_name
        self.safety_gate = safety_gate
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish the underlying transport (BLE connection, HTTP session, listener socket, ...)."""

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Tear down the underlying transport. Must be safe to call even if never connected."""

    async def __aenter__(self) -> Device:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.disconnect()
