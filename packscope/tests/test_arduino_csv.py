# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest

from packscope.devices.arduino_csv import ArduinoBrainCsvDecoder
from packscope.errors import DeviceProtocolError


def test_arduino_brain_csv_preserves_signal_quality_and_bands() -> None:
    decoder = ArduinoBrainCsvDecoder("bench-mindflex")

    snapshot = decoder.decode_line("0,51,40,1,2,3,4,5,6,7,8\n", received_at_monotonic_s=3.5)

    assert snapshot.device_id == "bench-mindflex"
    assert snapshot.signal_quality == 0
    assert snapshot.attention == 51
    assert snapshot.bands["high_beta"] == 6.0
    assert snapshot.quality_flags == ()


def test_arduino_brain_csv_rejects_wrong_column_count() -> None:
    with pytest.raises(DeviceProtocolError, match="Expected 11"):
        ArduinoBrainCsvDecoder().decode_line("0,1,2")
