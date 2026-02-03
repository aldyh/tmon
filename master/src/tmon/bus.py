"""Serial bus abstraction for RS-485 communication.

Wraps pyserial to send and receive tmon protocol frames over a
half-duplex RS-485 link.  The receive method is frame-aware: it
reads the 4-byte header (START, ADDR, CMD, LEN) to learn the
payload length, then reads the remaining payload + CRC bytes.

Example:
    >>> from tmon.bus import Bus
    >>> bus = Bus("/dev/ttyUSB0", 9600, timeout_ms=200)
    >>> bus.send(frame_bytes)
    >>> response = bus.receive()
"""

import serial


class Bus:
    """Half-duplex RS-485 serial bus.

    Wraps ``serial.Serial`` with frame-aware send/receive.
    Duck-typed -- tests can substitute any object with matching
    ``send(data)`` and ``receive()`` methods.

    Args:
        port: Serial port device path (e.g. ``"/dev/ttyUSB0"``).
        baudrate: Baud rate for the connection (e.g. ``9600``).
        timeout_ms: Receive timeout in milliseconds (e.g. ``200``).

    Example:
        >>> bus = Bus("/dev/ttyUSB0", 9600, timeout_ms=200)
        >>> bus.send(b"\\x01\\x03\\x01\\x00\\x80\\x50")
        >>> reply = bus.receive()
    """

    # Header is START + ADDR + CMD + LEN (4 bytes).
    _HEADER_LEN = 4
    # CRC is 2 bytes appended after the payload.
    _CRC_LEN = 2

    def __init__(self, port: str, baudrate: int, timeout_ms: int):
        """Open the serial port."""
        self._ser = serial.Serial(port, baudrate, timeout=0)
        self._timeout_ms = timeout_ms

    def send(self, data: bytes) -> None:
        """Send raw bytes on the bus, flushing any stale input first."""
        self._ser.reset_input_buffer()
        self._ser.write(data)
        self._ser.flush()

    def receive(self) -> bytes:
        """Receive a complete protocol frame, or b"" on timeout."""
        self._ser.timeout = self._timeout_ms / 1000.0
        header = self._ser.read(self._HEADER_LEN)
        if len(header) < self._HEADER_LEN:
            return b""

        payload_len = header[3]
        remaining = payload_len + self._CRC_LEN
        tail = self._ser.read(remaining)
        if len(tail) < remaining:
            return b""

        return header + tail

    def close(self) -> None:
        """Close the underlying serial port."""
        self._ser.close()
