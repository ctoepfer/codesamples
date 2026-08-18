from __future__ import annotations

import pytest

from brewpanel.core.app import Application
from brewpanel.features.telemetry_logger.feature import TelemetryLoggerFeature
from brewpanel.hardware.types import Measurement


@pytest.mark.asyncio
async def test_telemetry_logger_appends_csv_row(tmp_path) -> None:
    app = Application()
    log_path = tmp_path / "telemetry.csv"
    feature = TelemetryLoggerFeature(app, log_path=log_path)
    feature.register()

    measurement = Measurement(value=19.8, unit="celsius", source_device_id="tilt-1")
    await app.events.publish("telemetry", measurement)

    assert log_path.exists()
    rows = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert rows[0] == "timestamp,device_id,value,unit,raw_value"
    assert "tilt-1" in rows[1]
    assert "19.8" in rows[1]


@pytest.mark.asyncio
async def test_application_bootstrap_registers_telemetry_logger(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = Application()
    app.bootstrap()

    measurement = Measurement(value=1.05, unit="sg", source_device_id="ispindel-1")
    await app.events.publish("telemetry", measurement)

    assert (tmp_path / "brewpanel_telemetry.csv").exists()
