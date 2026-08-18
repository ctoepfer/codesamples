"""Append every published telemetry reading to a local CSV file.

This is the reference feature plugin, and it directly implements the "Audit
log: store timestamps, decoded responses, ..." requirement repeated across
every device's implementation-guidance section in docs/hardware/*.md --
applied once, generically, to every device's telemetry instead of being
reimplemented per driver.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.app import Application
    from ...hardware.types import Measurement

DEFAULT_LOG_PATH = Path("brewpanel_telemetry.csv")


class TelemetryLoggerFeature:
    def __init__(self, app: "Application", log_path: Path | None = None) -> None:
        self._app = app
        self._log_path = log_path or DEFAULT_LOG_PATH

    def register(self) -> None:
        self._app.events.subscribe("telemetry", self._on_telemetry)

    async def _on_telemetry(self, measurement: "Measurement") -> None:
        is_new = not self._log_path.exists()
        with self._log_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if is_new:
                writer.writerow(["timestamp", "device_id", "value", "unit", "raw_value"])
            writer.writerow(
                [
                    measurement.timestamp.isoformat(),
                    measurement.source_device_id,
                    measurement.value,
                    measurement.unit,
                    measurement.raw_value,
                ]
            )
