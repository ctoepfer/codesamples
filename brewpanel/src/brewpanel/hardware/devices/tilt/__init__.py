from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import TiltDevice, decode_tilt_ibeacon

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="tilt-1",
        display_name="Tilt Hydrometer",
        vendor="Tilt",
        transport=Transport.BLE,
        risk=RiskLevel.READ_ONLY,
        docs_reference="docs/hardware/tilt.md",
        capabilities=("get_temperature", "get_gravity"),
        implemented=True,
        notes="Passive iBeacon listener. No pairing, no GATT connection, no actuator exists on this device.",
    ),
    driver_cls=TiltDevice,
)

__all__ = ["PLUGIN", "TiltDevice", "decode_tilt_ibeacon"]
