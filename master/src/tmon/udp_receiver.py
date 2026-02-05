"""UDP receiver for pushed readings.

Slaves push REPLY frames via UDP; master just listens and stores.
No connection state, no polling -- slaves control timing.

Example:
    >>> from tmon.udp_receiver import UdpReceiver
    >>> receiver = UdpReceiver(5555)
    >>> frame = receiver.recv()  # Blocks until a frame arrives
    >>> receiver.close()
"""

import socket


class UdpReceiver:
    """UDP socket for receiving slave readings.

    Binds to a UDP port and receives frames pushed by slaves.
    Each frame is a complete protocol REPLY (START, ADDR, CMD, LEN,
    payload, CRC).

    Args:
        port: UDP port to listen on.

    Example:
        >>> receiver = UdpReceiver(5555)
        >>> frame = receiver.recv()  # Blocks until frame arrives
        >>> frame[1]  # ADDR byte
        3
        >>> receiver.close()
    """

    _MAX_FRAME = 64

    def __init__(self, port: int):
        """Bind to the UDP port and start listening."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", port))

    def recv(self) -> bytes:
        """Receive a single UDP datagram (blocks).

        Returns:
            The raw frame bytes, or empty bytes on error.
        """
        try:
            data, _ = self._sock.recvfrom(self._MAX_FRAME)
            return data
        except OSError:
            return b""

    def recv_timeout(self, timeout_s: float) -> bytes:
        """Receive with timeout.

        Args:
            timeout_s: Timeout in seconds.

        Returns:
            The raw frame bytes, or empty bytes on timeout/error.
        """
        self._sock.settimeout(timeout_s)
        try:
            data, _ = self._sock.recvfrom(self._MAX_FRAME)
            return data
        except socket.timeout:
            return b""
        except OSError:
            return b""
        finally:
            self._sock.settimeout(None)

    def close(self) -> None:
        """Close the socket."""
        try:
            self._sock.close()
        except OSError:
            pass
