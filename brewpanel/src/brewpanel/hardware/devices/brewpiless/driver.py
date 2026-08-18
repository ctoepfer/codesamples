"""Not yet implemented -- see docs/hardware/brewpiless.md.

The full HTTP endpoint table, MQTT topics, and WebSocket-tunneled serial
command set are source-verified and documented (docs/hardware/brewpiless.md
sections 7, 10-12). This isn't blocked on missing information -- it's next in
line for implementation.

IMPORTANT: BrewPiLess's own authentication is inconsistent by default (many
state-changing endpoints, and the entire `/ws` WebSocket, have no auth at
all -- see docs/hardware/brewpiless.md section 13). When this driver is
implemented, every actuator method must still go through
`brewpanel.hardware.safety.requires_confirmation` even though the device
itself won't stop an unconfirmed write.
"""

from __future__ import annotations

from ...device import Device
from ...safety import SafetyGate


class BrewPiLessDevice(Device):
    def __init__(
        self,
        device_id: str = "brewpiless-1",
        display_name: str = "BrewPiLess",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)

    async def connect(self) -> None:
        raise NotImplementedError(
            "BrewPiLess driver not yet implemented -- see docs/hardware/brewpiless.md "
            "for the full HTTP/MQTT/WebSocket protocol tables."
        )

    async def disconnect(self) -> None:
        self._connected = False
