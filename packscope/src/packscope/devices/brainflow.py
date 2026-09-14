# SPDX-License-Identifier: Apache-2.0
"""Optional BrainFlow adapter for OpenBCI and other BrainFlow-supported boards."""

from __future__ import annotations

import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from packscope.devices.base import DeviceCapabilities
from packscope.errors import ConfigurationError, OptionalDependencyError
from packscope.models import EegFrame


@dataclass(frozen=True, slots=True)
class BrainFlowConfig:
    """Connection settings passed to BrainFlow without importing it at package import time."""

    board_id: str
    serial_port: str | None = None
    mac_address: str | None = None
    ip_address: str | None = None
    ip_port: int | None = None
    timeout_s: int = 15
    channel_labels: dict[int, str] = field(default_factory=dict)
    device_id: str = "brainflow-device"


class BrainFlowEegSource:
    """Acquire raw EEG blocks and normalized metadata from a BrainFlow board.

    The caller must supply physical channel labels for location-dependent analyses.
    No channel index is ever silently treated as F3 or F4.
    """

    def __init__(self, config: BrainFlowConfig) -> None:
        self._config = config
        self._board: Any | None = None
        self._board_id: int | None = None
        self._clock_offset_s: float | None = None
        self._sampling_rate_hz: float | None = None

    @property
    def capabilities(self) -> DeviceCapabilities:
        labels = {name.upper() for name in self._config.channel_labels.values()}
        return DeviceCapabilities(
            source_name="brainflow",
            raw_eeg=True,
            frontal_asymmetry_possible={"F3", "F4"}.issubset(labels),
            has_signal_quality=False,
            sample_rate_hz=self._sampling_rate_hz,
            notes=("Channel locations must be explicitly mapped in BrainFlowConfig.",),
        )

    def start(self) -> None:
        """Connect to the board and begin buffered acquisition."""
        if self._board is not None:
            raise ConfigurationError("The BrainFlow source is already running.")
        try:
            from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
        except ImportError as error:
            raise OptionalDependencyError("brainflow", "brainflow") from error

        try:
            board_identifier = getattr(BoardIds, self._config.board_id)
            board_id = int(board_identifier.value)
        except AttributeError as error:
            raise ConfigurationError(
                f"Unknown BrainFlow board_id '{self._config.board_id}'. "
                "Use a BoardIds enum member such as 'CYTON_BOARD'."
            ) from error

        parameters = BrainFlowInputParams()
        for name in ("serial_port", "mac_address", "ip_address", "ip_port", "timeout"):
            configured_name = "timeout_s" if name == "timeout" else name
            value = getattr(self._config, configured_name)
            if value is not None:
                setattr(parameters, name, value)

        board = BoardShim(board_id, parameters)
        try:
            board.prepare_session()
            board.start_stream()
        except Exception:
            with suppress(Exception):
                board.release_session()
            raise

        self._board = board
        self._board_id = board_id
        self._sampling_rate_hz = float(BoardShim.get_sampling_rate(board_id))
        # BrainFlow timestamps are wall-clock seconds. Anchor them to the local
        # monotonic domain once so downstream windows share a non-adjusting clock.
        self._clock_offset_s = time.monotonic() - time.time()

    def stop(self) -> None:
        """Stop acquisition and release the native board session."""
        if self._board is None:
            return
        try:
            self._board.stop_stream()
        finally:
            self._board.release_session()
            self._board = None
            self._board_id = None
            self._sampling_rate_hz = None
            self._clock_offset_s = None

    def read_frame(self, max_samples: int) -> EegFrame | None:
        """Return up to max_samples currently buffered by BrainFlow."""
        if self._board is None or self._board_id is None or self._sampling_rate_hz is None:
            raise ConfigurationError("Call start() before reading from BrainFlow.")
        if max_samples <= 0:
            raise ConfigurationError("max_samples must be positive.")

        from brainflow.board_shim import BoardShim

        available = self._board.get_board_data_count()
        if available <= 0:
            return None
        data = self._board.get_board_data(min(max_samples, available))
        eeg_channels = BoardShim.get_eeg_channels(self._board_id)
        timestamp_channel = BoardShim.get_timestamp_channel(self._board_id)
        if not eeg_channels:
            raise ConfigurationError("The configured BrainFlow board has no EEG channels.")

        samples = np.asarray(data[eeg_channels, :], dtype=np.float64)
        wall_timestamps = np.asarray(data[timestamp_channel, :], dtype=np.float64)
        if np.any(wall_timestamps <= 0.0):
            # Some boards may not populate a timestamp row. Retain ordering and
            # clearly expose that host timing rather than manufacturing device time.
            now = time.monotonic()
            timestamps = now - np.arange(samples.shape[1] - 1, -1, -1) / self._sampling_rate_hz
            timestamp_origin = "host_estimate"
        else:
            timestamps = wall_timestamps + float(self._clock_offset_s)
            timestamp_origin = "brainflow_wallclock_mapped_to_monotonic"

        channel_names = tuple(self._config.channel_labels.get(index, f"EEG_{index}") for index in eeg_channels)
        return EegFrame(
            samples=samples,
            timestamps_monotonic_s=timestamps,
            channel_names=channel_names,
            sampling_rate_hz=self._sampling_rate_hz,
            source="brainflow",
            device_id=self._config.device_id,
            metadata={"timestamp_origin": timestamp_origin, "board_id": self._config.board_id},
        )
