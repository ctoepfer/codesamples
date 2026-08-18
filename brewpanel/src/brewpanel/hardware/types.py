"""Shared value types used across every device driver.

Standardizing on these types (instead of each driver returning bare floats or
device-native units) is what lets application code call ``get_temperature()``
on a Grainfather, a Tilt, or an iSpindel and get back the same shape. Internal
values are always metric (Celsius, specific gravity) per the unit-normalization
guidance repeated across docs/hardware/*.md -- convert to display units only at
the GUI layer.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class RiskLevel(enum.Enum):
    """Mirrors the risk classification used throughout docs/hardware/*.md."""

    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Transport(enum.Enum):
    BLE = "ble"
    HTTP = "http"
    MQTT = "mqtt"
    SIMULATED = "simulated"


@dataclass(frozen=True, slots=True)
class Measurement:
    """A single standardized reading from any device."""

    value: float
    unit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_value: float | None = None
    source_device_id: str | None = None


@dataclass(frozen=True, slots=True)
class TimerState:
    active: bool
    remaining_seconds: int
    total_seconds: int


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Static metadata about a device plugin, independent of any live instance."""

    device_id: str
    display_name: str
    vendor: str
    transport: Transport
    risk: RiskLevel
    docs_reference: str
    capabilities: tuple[str, ...] = ()
    implemented: bool = True
    notes: str | None = None
