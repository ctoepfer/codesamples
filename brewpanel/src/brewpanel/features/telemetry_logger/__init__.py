from ..types import FeatureInfo, FeaturePlugin
from .feature import TelemetryLoggerFeature

PLUGIN = FeaturePlugin(
    info=FeatureInfo(
        feature_id="telemetry_logger",
        display_name="Telemetry Logger",
        description="Appends every published telemetry reading to a local CSV audit log.",
    ),
    feature_cls=TelemetryLoggerFeature,
)

__all__ = ["PLUGIN", "TelemetryLoggerFeature"]
