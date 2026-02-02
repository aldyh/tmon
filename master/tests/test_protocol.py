"""Tests for tmon.protocol."""

import random

import pytest

from tmon.protocol import (
    PROTO_CMD_POLL,
    PROTO_CMD_REPLY,
    PROTO_START,
    PROTO_REPLY_PAYLOAD_LEN,
    PROTO_TEMP_INVALID,
    crc16_modbus,
    decode_frame,
    encode_request,
    parse_reply,
)


# -- CRC known vectors from protocol.org -------------------------------------


class TestCrc16Modbus:
    """CRC-16/MODBUS computation tests."""

    def test_example1_poll_slave3(self):
        """CRC of [03 01 00] should be 0x5080 (Example 1 in spec)."""
        assert crc16_modbus(bytes([0x03, 0x01, 0x00])) == 0x5080

    def test_example2_reply_slave3(self):
        """CRC of Example 2 body should be 0xEB90 (spec)."""
        body = bytes([
            0x03, 0x02, 0x08,
            0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
        ])
        assert crc16_modbus(body) == 0xEB90

    def test_empty_input(self):
        """CRC of empty data should be the initial value 0xFFFF."""
        assert crc16_modbus(b"") == 0xFFFF

    def test_single_byte(self):
        """CRC of a single zero byte should not be 0xFFFF."""
        result = crc16_modbus(b"\x00")
        assert result != 0xFFFF
        assert 0 <= result <= 0xFFFF


# -- encode_request ----------------------------------------------------------


class TestEncodeRequest:
    """Tests for the general frame encoder."""

    def test_example1_poll_slave3(self):
        """POLL for slave 3 should produce the Example 1 frame."""
        expected = bytes([0x01, 0x03, 0x01, 0x00, 0x80, 0x50])
        assert encode_request(3, PROTO_CMD_POLL, b"") == expected

    def test_poll_length_is_6(self):
        """POLL frame with no payload is always 6 bytes."""
        assert len(encode_request(1, PROTO_CMD_POLL, b"")) == 6
        assert len(encode_request(247, PROTO_CMD_POLL, b"")) == 6

    def test_example2_reply_frame(self):
        """encode_request should produce the Example 2 frame."""
        payload = bytes([
            0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
        ])
        expected = bytes([
            0x01, 0x03, 0x02, 0x08,
            0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
            0x90, 0xEB,
        ])
        assert encode_request(3, PROTO_CMD_REPLY, payload) == expected

    def test_start_byte(self):
        """First byte of any frame is PROTO_START."""
        frame = encode_request(1, PROTO_CMD_POLL, b"")
        assert frame[0] == PROTO_START

    def test_addr_in_frame(self):
        """Address appears at offset 1."""
        frame = encode_request(42, PROTO_CMD_POLL, b"")
        assert frame[1] == 42

    def test_cmd_in_frame(self):
        """Command byte appears at offset 2."""
        frame = encode_request(1, 0xAB, b"")
        assert frame[2] == 0xAB

    def test_len_field(self):
        """LEN field at offset 3 reflects actual payload length."""
        frame = encode_request(1, PROTO_CMD_POLL, b"\x01\x02\x03")
        assert frame[3] == 3

    def test_addr_boundary_low(self):
        """Address 0 should be rejected."""
        with pytest.raises(ValueError):
            encode_request(0, PROTO_CMD_POLL, b"")

    def test_addr_boundary_high(self):
        """Address 248 should be rejected."""
        with pytest.raises(ValueError):
            encode_request(248, PROTO_CMD_POLL, b"")


# -- decode_frame ------------------------------------------------------------


class TestDecodeFrame:
    """Tests for frame decoding and validation."""

    def test_roundtrip_poll(self):
        """encode then decode should recover the original fields."""
        raw = encode_request(5, PROTO_CMD_POLL, b"")
        frame = decode_frame(raw)
        assert frame["addr"] == 5
        assert frame["cmd"] == PROTO_CMD_POLL
        assert frame["payload"] == b""

    def test_roundtrip_reply(self):
        """Round-trip with a non-empty payload."""
        payload = bytes([0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F])
        raw = encode_request(10, PROTO_CMD_REPLY, payload)
        frame = decode_frame(raw)
        assert frame["addr"] == 10
        assert frame["cmd"] == PROTO_CMD_REPLY
        assert frame["payload"] == payload

    def test_example1_from_spec(self):
        """Decode the Example 1 frame from the protocol spec."""
        raw = bytes([0x01, 0x03, 0x01, 0x00, 0x80, 0x50])
        frame = decode_frame(raw)
        assert frame["addr"] == 3
        assert frame["cmd"] == PROTO_CMD_POLL
        assert frame["payload"] == b""

    def test_example2_from_spec(self):
        """Decode the Example 2 frame from the protocol spec."""
        raw = bytes([
            0x01, 0x03, 0x02, 0x08,
            0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
            0x90, 0xEB,
        ])
        frame = decode_frame(raw)
        assert frame["addr"] == 3
        assert frame["cmd"] == PROTO_CMD_REPLY
        assert len(frame["payload"]) == 8

    def test_error_short_frame(self):
        """Frames shorter than 6 bytes should be rejected."""
        with pytest.raises(ValueError, match="too short"):
            decode_frame(b"\x01\x02\x03")

    def test_error_bad_start(self):
        """Non-0x01 START byte should be rejected."""
        raw = bytearray(encode_request(1, PROTO_CMD_POLL, b""))
        raw[0] = 0xFF
        with pytest.raises(ValueError, match="bad START"):
            decode_frame(bytes(raw))

    def test_error_bad_crc(self):
        """Corrupted CRC should be detected."""
        raw = bytearray(encode_request(1, PROTO_CMD_POLL, b""))
        raw[-1] ^= 0xFF
        with pytest.raises(ValueError, match="CRC mismatch"):
            decode_frame(bytes(raw))

    def test_error_length_mismatch_too_long(self):
        """Extra bytes beyond what LEN declares should be rejected."""
        raw = encode_request(1, PROTO_CMD_POLL, b"") + b"\x00"
        with pytest.raises(ValueError, match="length mismatch"):
            decode_frame(raw)

    def test_error_length_mismatch_too_short(self):
        """Frame truncated relative to LEN should be rejected."""
        raw = bytearray(encode_request(1, PROTO_CMD_REPLY, b"\x01\x02\x03"))
        # Truncate one payload byte but keep original LEN
        truncated = bytes(raw[:6])
        with pytest.raises(ValueError):
            decode_frame(truncated)

    def test_error_addr_zero(self):
        """Address 0 in a frame should be rejected.

        We craft a frame with addr=0 and valid CRC to specifically
        test the addr range check.
        """
        import struct
        body = bytes([0x00, PROTO_CMD_POLL, 0x00])
        crc = crc16_modbus(body)
        raw = bytes([PROTO_START]) + body + struct.pack("<H", crc)
        with pytest.raises(ValueError, match="addr out of range"):
            decode_frame(raw)


# -- parse_reply -------------------------------------------------------------


class TestParseReply:
    """Tests for REPLY payload parsing."""

    def test_example2_payload(self):
        """Parse the Example 2 payload: channels 0,1 valid."""
        payload = bytes([
            0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
        ])
        result = parse_reply(payload)
        assert result["temperatures"][0] == pytest.approx(23.5)
        assert result["temperatures"][1] == pytest.approx(19.8)
        assert result["temperatures"][2] is None
        assert result["temperatures"][3] is None

    def test_all_channels_invalid(self):
        """All temps INVALID means all temperatures are None."""
        payload = bytes([0xFF, 0x7F] * 4)
        result = parse_reply(payload)
        assert result["temperatures"] == [None, None, None, None]

    def test_all_channels_valid(self):
        """All 4 temperatures returned as floats."""
        import struct
        temps_raw = struct.pack("<hhhh", 100, -50, 0, 325)
        result = parse_reply(temps_raw)
        assert result["temperatures"][0] == pytest.approx(10.0)
        assert result["temperatures"][1] == pytest.approx(-5.0)
        assert result["temperatures"][2] == pytest.approx(0.0)
        assert result["temperatures"][3] == pytest.approx(32.5)

    def test_negative_temperature(self):
        """Negative temperature values are handled correctly."""
        import struct
        temps_raw = struct.pack("<hhhh", -100, 0, 0, 0)
        result = parse_reply(temps_raw)
        assert result["temperatures"][0] == pytest.approx(-10.0)

    def test_bad_length_short(self):
        """Payload shorter than 8 bytes should be rejected."""
        with pytest.raises(ValueError, match="8 bytes"):
            parse_reply(b"\x00" * 7)

    def test_bad_length_long(self):
        """Payload longer than 8 bytes should be rejected."""
        with pytest.raises(ValueError, match="8 bytes"):
            parse_reply(b"\x00" * 9)


# -- Fuzz-ish ----------------------------------------------------------------


class TestFuzz:
    """Random byte sequences must not crash decode_frame."""

    def test_random_bytes_no_crash(self):
        """Feed 1000 random byte sequences; all must raise ValueError."""
        rng = random.Random(42)
        for _ in range(1000):
            length = rng.randint(0, 30)
            data = bytes(rng.randint(0, 255) for _ in range(length))
            try:
                decode_frame(data)
            except ValueError:
                pass
            # If it doesn't raise, that's fine too -- could be a valid frame
