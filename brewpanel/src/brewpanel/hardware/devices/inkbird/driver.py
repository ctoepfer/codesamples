"""Not yet implemented -- see docs/hardware/inkbird.md.

Unlike the other stubs in this package, this one is blocked on missing
information rather than missing implementation effort: the reviewed source
only confirms the generic Tuya DP/DPS platform architecture, not any specific
Inkbird product's data-point schema (docs/hardware/inkbird.md section 1).
Implementing this driver requires first obtaining the real DP function schema
for the exact owned model through an authorized Tuya developer project --
never guess a DP id or value for hardware that may control heating or cooling.
"""

from __future__ import annotations

from ...device import Device
from ...safety import SafetyGate


class InkbirdDevice(Device):
    def __init__(
        self,
        device_id: str = "inkbird-1",
        display_name: str = "Inkbird Smart",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)

    async def connect(self) -> None:
        raise NotImplementedError(
            "Inkbird driver not yet implemented -- and cannot be, generically. See "
            "docs/hardware/inkbird.md: this requires the real Tuya DP schema for your "
            "specific product, obtained through an authorized Tuya developer project."
        )

    async def disconnect(self) -> None:
        self._connected = False
