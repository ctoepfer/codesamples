# SPDX-License-Identifier: Apache-2.0
"""Optional LSL adapter for streams already synchronized through Lab Streaming Layer."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from packscope.devices.base import DeviceCapabilities
from packscope.errors import ConfigurationError, OptionalDependencyError
from packscope.models import EegFrame


@dataclass(frozen=True, slots=True)
class LslEegConfig:
    """Stable schema required to interpret a discovered LSL EEG stream."""

    channel_names: tuple[str, ...]
    sampling_rate_hz: float
    stream_name: str | None = None
    stream_type: str = "EEG"
    source_id: str = "lsl-eeg"
    timeout_s: float = 3.0


class LslEegSource:
    """Pull raw EEG chunks from exactly one discovered LSL stream."""

    def __init__(self, config: LslEegConfig) -> None:
        self._config = config
        self._inlet: object | None = None

    @property
    def capabilities(self) -> DeviceCapabilities:
        labels = {name.upper() for name in self._config.channel_names}
        return DeviceCapabilities(
            source_name="lsl",
            raw_eeg=True,
            frontal_asymmetry_possible={"F3", "F4"}.issubset(labels),
            has_signal_quality=False,
            sample_rate_hz=self._config.sampling_rate_hz,
            notes=("LSL clock correction should be retained in the recording provenance.",),
        )

    def start(self) -> None:
        """Resolve an unambiguous stream by name or type."""
        if self._inlet is not None:
            raise ConfigurationError("The LSL source is already running.")
        try:
            from pylsl import StreamInlet, resolve_byprop
        except ImportError as error:
            raise OptionalDependencyError("pylsl", "lsl") from error

        property_name = "name" if self._config.stream_name else "type"
        property_value = self._config.stream_name or self._config.stream_type
        streams = resolve_byprop(property_name, property_value, timeout=self._config.timeout_s)
        if len(streams) != 1:
            raise ConfigurationError(
                f"Expected exactly one LSL stream where {property_name}='{property_value}', "
                f"found {len(streams)}. Use a unique name or isolate the network."
            )
        self._inlet = StreamInlet(streams[0], processing_flags=0)

    def stop(self) -> None:
        """Drop the inlet; pylsl closes it when its reference is released."""
        self._inlet = None

    def read_frame(self, max_samples: int) -> EegFrame | None:
        """Pull an immediately available chunk without blocking the presentation loop."""
        if self._inlet is None:
            raise ConfigurationError("Call start() before reading from LSL.")
        if max_samples <= 0:
            raise ConfigurationError("max_samples must be positive.")
        samples, timestamps = self._inlet.pull_chunk(timeout=0.0, max_samples=max_samples)  # type: ignore[union-attr]
        if not samples:
            return None
        array = np.asarray(samples, dtype=np.float64)
        if array.ndim != 2 or array.shape[1] != len(self._config.channel_names):
            raise ConfigurationError("LSL sample width does not match configured channel_names.")
        return EegFrame(
            samples=array.T,
            timestamps_monotonic_s=np.asarray(timestamps, dtype=np.float64),
            channel_names=self._config.channel_names,
            sampling_rate_hz=self._config.sampling_rate_hz,
            source="lsl",
            device_id=self._config.source_id,
            metadata={"timestamp_origin": "lsl_clock"},
        )
