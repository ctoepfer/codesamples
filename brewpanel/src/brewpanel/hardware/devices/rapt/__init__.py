from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import RaptDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="rapt-1",
        display_name="RAPT",
        vendor="RAPT",
        transport=Transport.HTTP,
        risk=RiskLevel.HIGH,
        docs_reference="docs/hardware/rapt.md",
        capabilities=(
            "get_temperature",
            "get_target_temperature",
            "set_target_temperature",
            "get_heater_state",
            "set_heater",
            "get_pump_state",
            "set_pump",
        ),
        implemented=False,
        notes=(
            "Implement against the official REST API first (bearer token exchange + "
            "documented per-equipment-class endpoints). Local BLE is model-specific "
            "and only partially mapped -- do not implement it from UUIDs alone."
        ),
    ),
    driver_cls=RaptDevice,
)

__all__ = ["PLUGIN", "RaptDevice"]
