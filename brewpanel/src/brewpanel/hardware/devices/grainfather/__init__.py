from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import GrainfatherDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="grainfather-1",
        display_name="Grainfather",
        vendor="Grainfather",
        transport=Transport.BLE,
        risk=RiskLevel.HIGH,
        docs_reference="docs/hardware/grainfather.md",
        capabilities=(
            "get_temperature",
            "get_target_temperature",
            "set_target_temperature",
            "get_heater_state",
            "set_heater",
            "get_pump_state",
            "set_pump",
            "get_timer",
            "set_timer",
        ),
        implemented=False,
        notes=(
            "Protocol is fully recovered (see docs). Blocked on dynamic GATT "
            "characteristic-role discovery and hardware-in-hand validation, not "
            "missing information."
        ),
    ),
    driver_cls=GrainfatherDevice,
)

__all__ = ["PLUGIN", "GrainfatherDevice"]
