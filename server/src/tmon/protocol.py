"""Frame encoding and decoding for the tmon RS-485 protocol.

Handles the binary framing format described in docs/protocol.org:
START, ADDR, CMD, LEN, PAYLOAD, CRC_LO, CRC_HI.
"""

import struct
from dataclasses import dataclass

# -- Protocol constants ------------------------------------------------------

PROTO_START = 0x01
PROTO_CMD_POLL = 0x01
PROTO_CMD_REPLY = 0x02
PROTO_REPLY_PAYLOAD_LEN = 8
PROTO_TEMP_INVALID = 0x7FFF

# Valid address range per MODBUS: 1-247.
PROTO_ADDR_MIN = 1
PROTO_ADDR_MAX = 247


def is_valid_address(addr: int) -> bool:
    """Check whether *addr* is in the valid range (1-247)."""
    return PROTO_ADDR_MIN <= addr <= PROTO_ADDR_MAX


@dataclass
class Frame:
    """Decoded protocol frame."""

    addr: int
    cmd: int
    payload: bytes

# -- CRC-16/MODBUS -----------------------------------------------------------


def crc16_modbus(data: bytes) -> int:
    """Compute CRC-16/MODBUS over a byte sequence.

    Uses polynomial 0x8005 with initial value 0xFFFF and reflected
    input/output (standard MODBUS CRC).  Bitwise implementation --
    simple and sufficient for our short frames.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


# -- Encoding ----------------------------------------------------------------


def encode_frame(addr: int, cmd: int, payload: bytes) -> bytes:
    """Build a complete protocol frame.

    Constructs the frame: START + ADDR + CMD + LEN + PAYLOAD + CRC_LO + CRC_HI.
    The CRC is computed over ADDR + CMD + LEN + PAYLOAD.

    Raises:
        ValueError: If addr is outside the valid range 1-247.
    """
    if not is_valid_address(addr):
        raise ValueError(
            "addr must be in range {}-{}, got {}".format(
                PROTO_ADDR_MIN, PROTO_ADDR_MAX, addr
            )
        )
    body = bytes([addr, cmd, len(payload)]) + payload
    crc = crc16_modbus(body)
    return bytes([PROTO_START]) + body + struct.pack("<H", crc)


# -- Decoding ----------------------------------------------------------------


def decode_frame(data: bytes) -> Frame:
    """Parse raw bytes into a Frame.

    Validates the frame structure, length field, address range, and CRC.

    Raises:
        ValueError: On any validation failure (short frame, bad START byte,
            length mismatch, CRC mismatch, or address out of range).
    """
    if len(data) < 6:
        raise ValueError(
            "frame too short: {} bytes, minimum is 6".format(len(data))
        )

    if data[0] != PROTO_START:
        raise ValueError(
            "bad START byte: expected 0x{:02X}, got 0x{:02X}".format(
                PROTO_START, data[0]
            )
        )

    addr = data[1]
    cmd = data[2]
    payload_len = data[3]

    if len(data) != 4 + payload_len + 2:
        raise ValueError(
            "length mismatch: LEN field says {} payload bytes, "
            "but frame is {} bytes (expected {})".format(
                payload_len, len(data), 4 + payload_len + 2
            )
        )

    payload = data[4 : 4 + payload_len]
    crc_received = struct.unpack_from("<H", data, 4 + payload_len)[0]
    body = data[1 : 4 + payload_len]
    crc_computed = crc16_modbus(body)

    if crc_received != crc_computed:
        raise ValueError(
            "CRC mismatch: received 0x{:04X}, computed 0x{:04X}".format(
                crc_received, crc_computed
            )
        )

    if not is_valid_address(addr):
        raise ValueError(
            "addr out of range: {} (must be {}-{})".format(
                addr, PROTO_ADDR_MIN, PROTO_ADDR_MAX
            )
        )

    return Frame(addr, cmd, payload)


def parse_reply(payload: bytes) -> list[int | None]:
    """Parse the 8-byte REPLY payload into raw int16 temperatures.

    The payload layout is four int16-LE temperature values in tenths
    of a degree Celsius.  Channels with value PROTO_TEMP_INVALID are
    returned as None.

    Returns:
        list: Four raw int16 values (tenths of degree C), or None for invalid.

    Raises:
        ValueError: If payload is not exactly 8 bytes.
    """
    if len(payload) != PROTO_REPLY_PAYLOAD_LEN:
        raise ValueError(
            "REPLY payload must be {} bytes, got {}".format(
                PROTO_REPLY_PAYLOAD_LEN, len(payload)
            )
        )

    temperatures = []
    for i in range(4):
        raw = struct.unpack_from("<h", payload, i * 2)[0]
        if raw != PROTO_TEMP_INVALID:
            temperatures.append(raw)
        else:
            temperatures.append(None)

    return temperatures
