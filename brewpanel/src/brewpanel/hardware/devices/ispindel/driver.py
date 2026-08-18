"""Local HTTP receiver for an iSpindel's "Generic HTTP" output.

See docs/hardware/ispindel.md section 3: "There is no control/write path
back to an iSpindel beyond its own local configuration portal." iSpindel
devices push a reading to a configured server on their own sleep/wake
schedule -- there's nothing to poll or command, so this driver only
implements read capabilities, populated by whatever the device last posted.

Point the iSpindel's "Generic HTTP" (or "HTTP" service) target at:

    http://<this-host>:<port><path>

Field names/shape match docs/hardware/ispindel.md section 6.1 exactly:
``name``, ``temperature``, ``temp_units`` (optional), ``battery``, ``gravity``,
plus whatever else the firmware sends (ignored here beyond what we use).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ...device import Device
from ...safety import SafetyGate
from ...types import Measurement


def _to_celsius(value: float, units: str) -> float:
    if units == "F":
        return (value - 32) * 5 / 9
    if units == "K":
        return value - 273.15
    return value


class ISpindelDevice(Device):
    def __init__(
        self,
        device_id: str,
        display_name: str = "iSpindel",
        *,
        host: str = "0.0.0.0",
        port: int = 9501,
        path: str | None = None,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        super().__init__(device_id, display_name, safety_gate=safety_gate)
        self._host = host
        self._port = port
        self._path = path or f"/ispindel/{device_id}"
        self._runner = None  # aiohttp.web.AppRunner, created lazily in connect()
        self._latest_temp: Measurement | None = None
        self._latest_gravity: Measurement | None = None
        self._latest_battery: Measurement | None = None

    @property
    def path(self) -> str:
        return self._path

    async def connect(self) -> None:
        try:
            from aiohttp import web
        except ImportError as exc:  # pragma: no cover - exercised only without the extra installed
            raise RuntimeError(
                "The 'aiohttp' package is required for iSpindel support. Install with: pip install 'brewpanel[ispindel]'"
            ) from exc
        app = web.Application()
        app.router.add_post(self._path, self._handle_post)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        self._connected = True

    async def disconnect(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        self._connected = False

    async def _handle_post(self, request: object):  # pragma: no cover - thin aiohttp glue, exercised via ingest()
        from aiohttp import web

        payload = await request.json()  # type: ignore[attr-defined]
        self.ingest(payload)
        return web.json_response({})

    def ingest(self, payload: dict[str, object]) -> None:
        """Update internal state from a decoded JSON payload. Public so it's directly testable without aiohttp."""
        now = datetime.now(timezone.utc)
        raw_temp = float(payload["temperature"])  # type: ignore[arg-type]
        units = str(payload.get("temp_units", "C"))
        self._latest_temp = Measurement(
            value=round(_to_celsius(raw_temp, units), 2),
            unit="celsius",
            raw_value=raw_temp,
            timestamp=now,
            source_device_id=self.device_id,
        )
        self._latest_gravity = Measurement(
            value=float(payload["gravity"]),  # type: ignore[arg-type]
            unit="sg",
            timestamp=now,
            source_device_id=self.device_id,
        )
        if "battery" in payload:
            self._latest_battery = Measurement(
                value=float(payload["battery"]),  # type: ignore[arg-type]
                unit="volts",
                timestamp=now,
                source_device_id=self.device_id,
            )

    async def get_temperature(self) -> Measurement:
        if self._latest_temp is None:
            raise RuntimeError(f"{self.device_id}: no iSpindel payload received yet")
        return self._latest_temp

    async def get_gravity(self) -> Measurement:
        if self._latest_gravity is None:
            raise RuntimeError(f"{self.device_id}: no iSpindel payload received yet")
        return self._latest_gravity

    async def get_battery(self) -> Measurement:
        if self._latest_battery is None:
            raise RuntimeError(f"{self.device_id}: no iSpindel payload received yet")
        return self._latest_battery
