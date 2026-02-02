"""Frame encoding and decoding for the tmon RS-485 protocol.

Handles the binary framing format described in docs/protocol.org:
START, ADDR, CMD, LEN, PAYLOAD, CRC_LO, CRC_HI.

Example:
    >>> from tmon.protocol import encode_request, decode_frame, PROTO_CMD_POLL
    >>> raw = encode_request(3, PROTO_CMD_POLL, b"")
    >>> raw.hex(' ')
    '01 03 01 00 80 50'
    >>> frame = decode_frame(raw)
    >>> frame['addr']
    3
    >>> frame['cmd']
    1
"""

import struct

# -- Protocol constants ------------------------------------------------------

PROTO_START = 0x01
PROTO_CMD_POLL = 0x01
PROTO_CMD_REPLY = 0x02
PROTO_REPLY_PAYLOAD_LEN = 8
PROTO_TEMP_INVALID = 0x7FFF

# -- CRC-16/MODBUS -----------------------------------------------------------


def crc16_modbus(data):
    """Compute CRC-16/MODBUS over a byte sequence.

    Uses polynomial 0x8005 with initial value 0xFFFF and reflected
    input/output (standard MODBUS CRC).  Bitwise implementation --
    simple and sufficient for our short frames.

    Args:
        data: Bytes-like object to compute the CRC over.

    Returns:
        int: 16-bit CRC value.

    Example:
        >>> crc16_modbus(bytes([0x03, 0x01, 0x00]))
        0x5080
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


def encode_request(addr, cmd, payload):
    """Build a complete protocol frame.

    Constructs the frame: START + ADDR + CMD + LEN + PAYLOAD + CRC_LO + CRC_HI.
    The CRC is computed over ADDR + CMD + LEN + PAYLOAD.

    Args:
        addr: Slave address (int, 1-247).
        cmd: Command byte (int).
        payload: Payload bytes (bytes, may be empty).

    Returns:
        bytes: The complete encoded frame.

    Raises:
        ValueError: If addr is outside the valid range 1-247.

    Example:
        >>> encode_request(3, PROTO_CMD_POLL, b"").hex(' ')
        '01 03 01 00 80 50'
        >>> import struct
        >>> payload = struct.pack("<hhhh", 235, 198, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        >>> encode_request(3, PROTO_CMD_REPLY, payload).hex(' ')
        '01 03 02 08 eb 00 c6 00 ff 7f ff 7f 90 eb'
    """
    if not (1 <= addr <= 247):
        raise ValueError(
            "addr must be in range 1-247, got {}".format(addr)
        )
    body = bytes([addr, cmd, len(payload)]) + payload
    crc = crc16_modbus(body)
    return bytes([PROTO_START]) + body + struct.pack("<H", crc)


# -- Decoding ----------------------------------------------------------------


def decode_frame(data):
    """Parse raw bytes into a protocol frame dict.

    Validates the frame structure, length field, address range, and CRC.

    Args:
        data: Raw bytes received from the bus (bytes).

    Returns:
        dict: Parsed frame with keys:
            - ``addr`` (int): Slave address.
            - ``cmd`` (int): Command byte.
            - ``payload`` (bytes): Payload bytes (may be empty).

    Raises:
        ValueError: On any validation failure (short frame, bad START byte,
            length mismatch, CRC mismatch, or address out of range).

    Example:
        >>> frame = decode_frame(bytes.fromhex('01 03 01 00 80 50'))
        >>> frame['addr'], frame['cmd'], frame['payload']
        (3, 1, b'')
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

    if not (1 <= addr <= 247):
        raise ValueError(
            "addr out of range: {} (must be 1-247)".format(addr)
        )

    return {"addr": addr, "cmd": cmd, "payload": payload}


def parse_reply_payload(payload):
    """Parse the 8-byte REPLY payload into temperatures.

    The payload layout is four int16-LE temperature values in tenths
    of a degree Celsius.  Channels with value PROTO_TEMP_INVALID are
    returned as None.

    Args:
        payload: Exactly 8 bytes of REPLY payload (bytes).

    Returns:
        dict: Parsed reply with keys:
            - ``temperatures`` (list): Four floats (degrees Celsius) or
              None for invalid channels.

    Raises:
        ValueError: If payload is not exactly 8 bytes.

    Example:
        >>> result = parse_reply_payload(
        ...     bytes([0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F])
        ... )
        >>> result['temperatures']
        [23.5, 19.8, None, None]
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
            temperatures.append(raw / 10.0)
        else:
            temperatures.append(None)

    return {"temperatures": temperatures}
