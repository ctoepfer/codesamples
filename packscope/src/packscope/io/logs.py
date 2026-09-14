# SPDX-License-Identifier: Apache-2.0
"""Documented raw log inputs for the offline CLI; no inferred channel locations."""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from packscope.errors import ConfigurationError
from packscope.io.serialization import from_dict
from packscope.models import EegFrame, GazeSample


def read_payload(path: Path) -> Any:
    """Read JSON with actionable errors."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ConfigurationError(f"Cannot read JSON log {path}: {error}") from error


def read_eeg_log(path: Path, *, sampling_rate_hz: float | None = None, window_s: float = 4.0) -> list[EegFrame]:
    """Read raw EegFrame dictionaries/envelopes or timestamp-plus-channel CSV.

    CSV requires an explicit sampling rate. JSON accepts one frame, a list, or
    {"frames": [...]}. Windows never cross input frame boundaries; tails are kept.
    """
    if not np.isfinite(window_s) or window_s <= 0:
        raise ConfigurationError("window_s must be positive and finite.")
    try:
        if path.suffix.lower() == ".csv":
            if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz <= 0:
                raise ConfigurationError("CSV requires --sampling-rate-hz with a positive finite value.")
            with path.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                names = reader.fieldnames or []
                if "timestamp_monotonic_s" not in names or len(names) < 2 or len(set(names)) != len(names):
                    raise ConfigurationError("CSV requires timestamp_monotonic_s and unique channel columns.")
                channels = tuple(n for n in names if n != "timestamp_monotonic_s")
                rows = list(reader)
            frames = [
                EegFrame(
                    np.array([[float(r[n]) for r in rows] for n in channels]),
                    np.array([float(r["timestamp_monotonic_s"]) for r in rows]),
                    channels,
                    sampling_rate_hz,
                    "csv",
                    path.stem,
                )
            ]
        else:
            payload = read_payload(path)
            items = payload.get("frames", [payload]) if isinstance(payload, dict) else payload
            frames = []
            for item in items:
                if "schema_version" in item:
                    frame = from_dict(item)
                    if not isinstance(frame, EegFrame):
                        raise ConfigurationError("Expected EegFrame data.")
                else:
                    item = dict(item)
                    item["channel_names"] = tuple(item["channel_names"])
                    item["quality_flags"] = tuple(item.get("quality_flags", ()))
                    frame = EegFrame(**item)
                frames.append(frame)
        windows = []
        for frame in frames:
            size = int(window_s * frame.sampling_rate_hz)
            if size < 1:
                raise ConfigurationError("Window must contain at least one sample.")
            for start in range(0, frame.samples.shape[1], size):
                windows.append(
                    replace(
                        frame,
                        samples=frame.samples[:, start : start + size],
                        timestamps_monotonic_s=frame.timestamps_monotonic_s[start : start + size],
                    )
                )
        return windows
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ConfigurationError(f"Invalid EEG log: {error}") from error


def read_gaze_log(path: Path) -> list[GazeSample]:
    """Read a JSON list of gaze dictionaries or serialization envelopes."""
    payload = read_payload(path)
    try:
        items = payload.get("samples", [payload]) if isinstance(payload, dict) else payload
        samples = []
        for item in items:
            sample = from_dict(item) if "schema_version" in item else GazeSample(**item)
            if not isinstance(sample, GazeSample) or type(sample.valid) is not bool:
                raise ConfigurationError("Expected GazeSample data with boolean validity.")
            samples.append(sample)
        return samples
    except (ValueError, TypeError, KeyError) as error:
        raise ConfigurationError(f"Invalid gaze log: {error}") from error
