from ...registry import DevicePlugin
from ...types import DeviceInfo, RiskLevel, Transport
from .driver import SimulatorDevice

PLUGIN = DevicePlugin(
    info=DeviceInfo(
        device_id="simulator-1",
        display_name="Simulated Brew Controller",
        vendor="brewpanel",
        transport=Transport.SIMULATED,
        risk=RiskLevel.LOW,
        docs_reference="",
        capabilities=(
            "get_temperature",
            "get_gravity",
            "get_target_temperature",
            "set_target_temperature",
            "get_heater_state",
            "set_heater",
            "get_pump_state",
            "set_pump",
            "get_timer",
            "set_timer",
            "cancel_timer",
        ),
        implemented=True,
        notes="No real hardware. Safe to exercise the full actuator/confirmation path.",
    ),
    driver_cls=SimulatorDevice,
)

__all__ = ["PLUGIN", "SimulatorDevice"]
