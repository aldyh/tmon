"""Frame encoding and decoding for the tmon RS-485 protocol.

Handles the binary framing format described in docs/protocol.md:
START, ADDR, CMD, LEN, PAYLOAD, CRC_LO, CRC_HI.

Example:
    >>> from tmon.protocol import encode_request, decode_frame
    >>> raw = encode_request(addr=1, cmd=0x10)
    >>> frame = decode_frame(raw)
"""


def encode_request(addr, cmd):
    """Encode a poll request frame.

    Args:
        addr: Slave address (1-247).
        cmd: Command byte.

    Returns:
        bytes: The encoded frame.
    """
    raise NotImplementedError


def decode_frame(data):
    """Decode a raw frame from the bus.

    Args:
        data: Raw bytes received from the bus.

    Returns:
        dict: Parsed frame fields (addr, cmd, payload, etc.).
    """
    raise NotImplementedError
