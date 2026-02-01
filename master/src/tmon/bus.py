"""Serial bus abstraction for RS-485 communication.

Wraps pyserial to send and receive tmon protocol frames over a
half-duplex RS-485 link.

Example:
    >>> from tmon.bus import Bus
    >>> bus = Bus(port="/dev/ttyUSB0", baudrate=9600)
    >>> bus.send(frame_bytes)
    >>> response = bus.receive(timeout_ms=500)
"""


class Bus:
    """Half-duplex RS-485 serial bus.

    Args:
        port: Serial port device path.
        baudrate: Baud rate for the connection.
    """

    def __init__(self, port, baudrate):
        """Initialize the bus.

        Args:
            port: Serial port device path (e.g. "/dev/ttyUSB0").
            baudrate: Baud rate (e.g. 9600).
        """
        raise NotImplementedError

    def send(self, data):
        """Send raw bytes on the bus.

        Args:
            data: Bytes to transmit.
        """
        raise NotImplementedError

    def receive(self, timeout_ms):
        """Receive raw bytes from the bus.

        Args:
            timeout_ms: Read timeout in milliseconds.

        Returns:
            bytes: Data received, or empty bytes on timeout.
        """
        raise NotImplementedError
