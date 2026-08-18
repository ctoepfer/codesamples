"""Not yet implemented -- see docs/hardware/nespresso.md.

The GATT service/characteristic layout is known per machine family (Vertuo
Next / Barista / Vmini), but the actual command IDs, payloads, and the
pairing/token/crypto sequence needed to open an authorized session are not
verified (docs/hardware/nespresso.md section 1). Do not attempt actuator
calls -- brew, Wi-Fi, pairing, or firmware -- without an authorized,
model-specific session capture first; a mis-issued write can brick the
machine.
"""

from __future__ import annotations

from ...device import Device
from ...safety import SafetyGate


class NespressoDevice(Device):
    def __init__(
        self,
        device_id: str = "nespresso-1",
        display_name: str = "Nespresso Smart",
        *,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)

    async def connect(self) -> None:
        raise NotImplementedError(
            "Nespresso driver not yet implemented -- see docs/hardware/nespresso.md. "
            "Command IDs/payloads and the pairing/crypto sequence are unverified; do "
            "not implement actuator calls without an authorized session capture."
        )

    async def disconnect(self) -> None:
        self._connected = False
