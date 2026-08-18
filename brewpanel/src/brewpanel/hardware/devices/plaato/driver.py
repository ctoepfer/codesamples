"""Not yet implemented -- see docs/hardware/plaato.md.

The official read-only REST API (`x-plaato-api-key` header, `/devices`,
`/devices/{id}/readings`, ...) is documented in docs/hardware/plaato.md
section 2. There is no published actuator endpoint for this system, so this
driver -- once implemented -- is expected to remain read-only.
"""

from __future__ import annotations

from ...device import Device
from ...safety import SafetyGate


class PlaatoDevice(Device):
    def __init__(
        self,
        device_id: str = "plaato-1",
        display_name: str = "Plaato",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)

    async def connect(self) -> None:
        raise NotImplementedError(
            "Plaato driver not yet implemented -- see docs/hardware/plaato.md for the "
            "official read-only REST API (x-plaato-api-key header)."
        )

    async def disconnect(self) -> None:
        self._connected = False
