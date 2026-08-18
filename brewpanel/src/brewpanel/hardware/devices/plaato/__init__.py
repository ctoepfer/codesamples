from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import PlaatoDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="plaato-1",
        display_name="Plaato",
        vendor="Plaato",
        transport=Transport.HTTP,
        risk=RiskLevel.READ_ONLY,
        docs_reference="docs/hardware/plaato.md",
        capabilities=("get_temperature", "get_gravity", "get_battery"),
        implemented=False,
        notes="Official API is read-only monitoring only -- no actuator endpoint is published.",
    ),
    driver_cls=PlaatoDevice,
)

__all__ = ["PLUGIN", "PlaatoDevice"]
