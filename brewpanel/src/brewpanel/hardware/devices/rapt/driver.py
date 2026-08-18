"""Not yet implemented -- see docs/hardware/rapt.md.

The official REST API (token exchange, device discovery, telemetry, and
documented control endpoints per equipment class) is fully specified in
docs/hardware/rapt.md sections 3.1-3.2 and is the intended first
implementation -- prefer it over local BLE, which remains model-specific and
partially unmapped (section 1.2). This stub exists so the plugin shape is
correct before that REST client is written.
"""

from __future__ import annotations

from ...device import Device
from ...safety import SafetyGate


class RaptDevice(Device):
    def __init__(
        self,
        device_id: str = "rapt-1",
        display_name: str = "RAPT",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)

    async def connect(self) -> None:
        raise NotImplementedError(
            "RAPT driver not yet implemented -- see docs/hardware/rapt.md for the "
            "official REST API token exchange and documented control endpoints."
        )

    async def disconnect(self) -> None:
        self._connected = False
