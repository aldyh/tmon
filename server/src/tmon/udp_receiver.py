"""UDP receiver for pushed readings.

Sensors push REPLY frames via UDP; server just listens and stores.
No connection state, no polling -- sensors control timing.
"""

import socket


class UDPReceiver:
    """UDP socket for receiving sensor readings.

    Binds to a UDP port and receives frames pushed by sensors.
    Each frame is a complete protocol REPLY (START, ADDR, CMD, LEN,
    payload, CRC).

    Args:
        port: UDP port to listen on.
    """

    _MAX_FRAME = 64

    def __init__(self, port: int):
        """Bind to the UDP port and start listening."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", port))

    def recv(self, timeout_s: float) -> bytes:
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

    def __enter__(self) -> "UDPReceiver":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the socket."""
        try:
            self._sock.close()
        except OSError:
            pass
