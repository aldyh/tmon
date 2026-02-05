"""Tests for UDPReceiver."""

import socket
import threading
import time

from tmon.udp_receiver import UDPReceiver


def _find_free_port() -> int:
    """Find an available UDP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _send_udp(port: int, data: bytes) -> None:
    """Send a UDP datagram to localhost:port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data, ("127.0.0.1", port))
    sock.close()


class TestUDPReceiverRecvTimeout:
    """Tests for recv."""

    def test_timeout_returns_empty(self) -> None:
        """recv returns empty bytes on timeout."""
        port = _find_free_port()
        bus = UDPReceiver(port)
        try:
            start = time.time()
            result = bus.recv(0.1)
            elapsed = time.time() - start

            assert result == b""
            assert elapsed < 0.3
        finally:
            bus.close()

    def test_recv_within_timeout(self) -> None:
        """recv returns frame if it arrives in time."""
        port = _find_free_port()
        bus = UDPReceiver(port)
        try:
            frame = b"\x01\x03\x02\x08\xe8\x03\xf4\x01\x00\x00\xff\x7f\xdb\x5a"

            def send_later():
                time.sleep(0.05)
                _send_udp(port, frame)

            t = threading.Thread(target=send_later)
            t.start()

            result = bus.recv(1.0)
            t.join()

            assert result == frame
        finally:
            bus.close()


class TestUDPReceiverClose:
    """Tests for close."""

    def test_close_releases_port(self) -> None:
        """After close, port can be reused."""
        port = _find_free_port()
        bus1 = UDPReceiver(port)
        bus1.close()

        # Should be able to bind again
        bus2 = UDPReceiver(port)
        bus2.close()
