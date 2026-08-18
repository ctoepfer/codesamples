from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import InkbirdDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="inkbird-1",
        display_name="Inkbird Smart",
        vendor="Inkbird (Tuya platform)",
        transport=Transport.MQTT,
        risk=RiskLevel.MEDIUM,
        docs_reference="docs/hardware/inkbird.md",
        capabilities=("get_temperature",),
        implemented=False,
        notes=(
            "Product-specific DP schema is required and was not recovered -- this is "
            "blocked on missing information, not missing effort. Never guess a DP id/value."
        ),
    ),
    driver_cls=InkbirdDevice,
)

__all__ = ["PLUGIN", "InkbirdDevice"]
