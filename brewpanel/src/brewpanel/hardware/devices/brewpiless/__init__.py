from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import BrewPiLessDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="brewpiless-1",
        display_name="BrewPiLess",
        vendor="BrewPiLess (vitotai, open source)",
        transport=Transport.HTTP,
        risk=RiskLevel.HIGH,
        docs_reference="docs/hardware/brewpiless.md",
        capabilities=(
            "get_temperature",
            "get_gravity",
            "get_target_temperature",
            "set_target_temperature",
            "get_heater_state",
            "set_heater",
            "get_pump_state",
            "set_pump",
        ),
        implemented=False,
        notes=(
            "Protocol is fully documented (source-verified). Device's own default auth is "
            "weak/absent on several endpoints -- the confirmation gate in this app is the "
            "only thing standing between a bug and an unattended heater/pump change."
        ),
    ),
    driver_cls=BrewPiLessDevice,
)

__all__ = ["PLUGIN", "BrewPiLessDevice"]
