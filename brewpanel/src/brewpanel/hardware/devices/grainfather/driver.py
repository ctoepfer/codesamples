"""Not yet implemented -- see docs/hardware/grainfather.md.

The ASCII command language and telemetry record map are fully recovered
(docs/hardware/grainfather.md sections 1.3-1.4), so this isn't blocked on
missing protocol information. What's still needed before a real driver can be
written: `bleak`-based dynamic GATT characteristic discovery (the two known
UUIDs are not statically mapped to write/notify roles -- discover them live,
every connection, per section 1.1), notification reassembly for the
comma-delimited records, and validation against real hardware. This stub
exists so the plugin shape and capability metadata are already correct when
that work happens.
"""

from __future__ import annotations

from ...device import Device
from ...safety import SafetyGate


class GrainfatherDevice(Device):
    def __init__(
        self,
        device_id: str = "grainfather-1",
        display_name: str = "Grainfather",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)

    async def connect(self) -> None:
        raise NotImplementedError(
            "Grainfather driver not yet implemented -- see docs/hardware/grainfather.md "
            "for the recovered BLE UUIDs, ASCII command table, and telemetry record map."
        )

    async def disconnect(self) -> None:
        self._connected = False
