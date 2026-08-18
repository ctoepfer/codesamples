from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import BrewbloxDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="brewblox-1",
        display_name="Brewblox / BrewPi Spark",
        vendor="Brewblox (open source)",
        transport=Transport.HTTP,
        risk=RiskLevel.HIGH,
        docs_reference="docs/hardware/brewblox.md",
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
            "Client of a running Brewblox Spark service (block-based REST/MQTT), never "
            "the Spark controller's raw wire protocol directly. Exact block field names "
            "must be pulled from the target deployment's live /openapi.json."
        ),
    ),
    driver_cls=BrewbloxDevice,
)

__all__ = ["PLUGIN", "BrewbloxDevice"]
