from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import ISpindelDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="ispindel-1",
        display_name="iSpindel",
        vendor="iSpindel (universam1)",
        transport=Transport.HTTP,
        risk=RiskLevel.READ_ONLY,
        docs_reference="docs/hardware/ispindel.md",
        capabilities=("get_temperature", "get_gravity", "get_battery"),
        implemented=True,
        notes="Local receiver for the device's 'Generic HTTP' output. Push-only: no control path exists.",
    ),
    driver_cls=ISpindelDevice,
)

__all__ = ["PLUGIN", "ISpindelDevice"]
