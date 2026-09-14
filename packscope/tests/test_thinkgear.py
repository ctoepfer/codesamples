from __future__ import annotations

from packscope.devices.thinkgear import ThinkGearParser


def _packet(payload: bytes) -> bytes:
    return bytes((0xAA, 0xAA, len(payload))) + payload + bytes(((~sum(payload)) & 0xFF,))


def test_parser_recovers_fragmented_packet_and_decodes_asic_bands() -> None:
    bands = b"".join(value.to_bytes(3, "big") for value in range(1, 9))
    payload = bytes((0x02, 0, 0x04, 42, 0x05, 61, 0x83, 24)) + bands
    encoded = _packet(payload)
    parser = ThinkGearParser()

    assert parser.feed(encoded[:5], received_at_monotonic_s=10.0) == []
    packets = parser.feed(encoded[5:], received_at_monotonic_s=10.1)

    assert len(packets) == 1
    decoded = packets[0]
    assert decoded.poor_signal == 0
    assert decoded.attention == 42
    assert decoded.meditation == 61
    assert decoded.band_powers["delta"] == 1.0
    assert decoded.band_powers["mid_gamma"] == 8.0
    assert parser.valid_packets == 1


def test_parser_rejects_bad_checksum_and_resynchronizes() -> None:
    parser = ThinkGearParser()
    corrupt = b"\xaa\xaa\x02\x04\x44\x00"
    valid = _packet(bytes((0x04, 99)))

    packets = parser.feed(corrupt + valid, received_at_monotonic_s=1.0)

    assert parser.invalid_checksums == 1
    assert len(packets) == 1
    assert packets[0].attention == 99
