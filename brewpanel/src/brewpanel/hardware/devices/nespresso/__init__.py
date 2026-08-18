from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import NespressoDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="nespresso-1",
        display_name="Nespresso Smart",
        vendor="Nespresso",
        transport=Transport.BLE,
        risk=RiskLevel.HIGH,
        docs_reference="docs/hardware/nespresso.md",
        capabilities=(),
        implemented=False,
        notes=(
            "Not a brewing/fermentation device -- included for completeness. Command "
            "IDs/payloads and pairing/crypto sequence are unverified; do not implement "
            "actuator calls without an authorized session capture."
        ),
    ),
    driver_cls=NespressoDevice,
)

__all__ = ["PLUGIN", "NespressoDevice"]
