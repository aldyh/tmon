"""Tests for UdpReceiver."""

import socket
import threading
import time

from tmon.udp_receiver import UdpReceiver


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


class TestUdpReceiverRecv:
    """Tests for recv."""

    def test_recv_single_frame(self) -> None:
        """recv returns a complete frame."""
        port = _find_free_port()
        bus = UdpReceiver(port)
        try:
            # Send a REPLY frame: START=0x01, ADDR=3, CMD=0x02, LEN=8, payload, CRC
            frame = b"\x01\x03\x02\x08\xe8\x03\xf4\x01\x00\x00\xff\x7f\xdb\x5a"

            def send_later():
                time.sleep(0.05)
                _send_udp(port, frame)

            t = threading.Thread(target=send_later)
            t.start()

            received = bus.recv()
            t.join()

            assert received == frame
        finally:
            bus.close()

    def test_recv_extracts_addr(self) -> None:
        """Frame ADDR byte is at index 1."""
        port = _find_free_port()
        bus = UdpReceiver(port)
        try:
            # Frame with ADDR=5
            frame = b"\x01\x05\x02\x08\xe8\x03\xf4\x01\x00\x00\xff\x7f\x5a\x5b"

            def send_later():
                time.sleep(0.05)
                _send_udp(port, frame)

            t = threading.Thread(target=send_later)
            t.start()

            received = bus.recv()
            t.join()

            assert received[1] == 5
        finally:
            bus.close()

    def test_recv_multiple_frames(self) -> None:
        """recv returns frames one at a time."""
        port = _find_free_port()
        bus = UdpReceiver(port)
        try:
            frame1 = b"\x01\x01\x02\x08\x64\x00\x00\x00\x00\x00\xff\x7f\xaa\xbb"
            frame2 = b"\x01\x02\x02\x08\xc8\x00\x00\x00\x00\x00\xff\x7f\xcc\xdd"

            def send_later():
                time.sleep(0.05)
                _send_udp(port, frame1)
                time.sleep(0.05)
                _send_udp(port, frame2)

            t = threading.Thread(target=send_later)
            t.start()

            r1 = bus.recv()
            r2 = bus.recv()
            t.join()

            assert r1 == frame1
            assert r2 == frame2
        finally:
            bus.close()


class TestUdpReceiverRecvTimeout:
    """Tests for recv_timeout."""

    def test_timeout_returns_empty(self) -> None:
        """recv_timeout returns empty bytes on timeout."""
        port = _find_free_port()
        bus = UdpReceiver(port)
        try:
            start = time.time()
            result = bus.recv_timeout(0.1)
            elapsed = time.time() - start

            assert result == b""
            assert elapsed < 0.3
        finally:
            bus.close()

    def test_recv_within_timeout(self) -> None:
        """recv_timeout returns frame if it arrives in time."""
        port = _find_free_port()
        bus = UdpReceiver(port)
        try:
            frame = b"\x01\x03\x02\x08\xe8\x03\xf4\x01\x00\x00\xff\x7f\xdb\x5a"

            def send_later():
                time.sleep(0.05)
                _send_udp(port, frame)

            t = threading.Thread(target=send_later)
            t.start()

            result = bus.recv_timeout(1.0)
            t.join()

            assert result == frame
        finally:
            bus.close()


class TestUdpReceiverClose:
    """Tests for close."""

    def test_close_releases_port(self) -> None:
        """After close, port can be reused."""
        port = _find_free_port()
        bus1 = UdpReceiver(port)
        bus1.close()

        # Should be able to bind again
        bus2 = UdpReceiver(port)
        bus2.close()
