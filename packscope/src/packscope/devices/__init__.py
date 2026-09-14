# SPDX-License-Identifier: Apache-2.0
"""EEG hardware adapters and their stable data contracts."""

from packscope.devices.arduino_csv import ArduinoBrainCsvDecoder
from packscope.devices.arduino_serial import ArduinoBrainSerialConfig, ArduinoBrainSerialSource
from packscope.devices.base import BandPowerSnapshot, DeviceCapabilities, EegSource
from packscope.devices.brainflow import BrainFlowConfig, BrainFlowEegSource
from packscope.devices.lsl import LslEegConfig, LslEegSource
from packscope.devices.thinkgear import ThinkGearPacket, ThinkGearParser
from packscope.devices.thinkgear_serial import ThinkGearSerialConfig, ThinkGearSerialSource

__all__ = [
    "ArduinoBrainCsvDecoder",
    "ArduinoBrainSerialConfig",
    "ArduinoBrainSerialSource",
    "BandPowerSnapshot",
    "BrainFlowConfig",
    "BrainFlowEegSource",
    "DeviceCapabilities",
    "EegSource",
    "LslEegConfig",
    "LslEegSource",
    "ThinkGearPacket",
    "ThinkGearParser",
    "ThinkGearSerialConfig",
    "ThinkGearSerialSource",
]
