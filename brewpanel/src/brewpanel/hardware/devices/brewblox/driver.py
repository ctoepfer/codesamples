"""Not yet implemented -- see docs/hardware/brewblox.md.

Brewblox is a service-oriented platform, not a single device -- this driver
is expected to be an HTTP/MQTT client of a running Brewblox Spark service
(never the Spark controller's raw wire protocol; see docs/hardware/brewblox.md
sections 1-2). The block-based REST/MQTT API is documented, but exact
per-block-type field names (e.g. a Setpoint block's target-value key) must be
pulled from the target deployment's live `/openapi.json` before writing --
see section 2.8/3.2 of the reference.
"""

from __future__ import annotations

from ...device import Device
from ...safety import SafetyGate


class BrewbloxDevice(Device):
    def __init__(
        self,
        device_id: str = "brewblox-1",
        display_name: str = "Brewblox / BrewPi Spark",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)

    async def connect(self) -> None:
        raise NotImplementedError(
            "Brewblox driver not yet implemented -- see docs/hardware/brewblox.md for "
            "the block-based REST/MQTT API this should target."
        )

    async def disconnect(self) -> None:
        self._connected = False
