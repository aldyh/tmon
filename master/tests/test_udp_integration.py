"""Integration tests for UDP push transport.

Tests the full push cycle over localhost UDP:
- UdpReceiver listening on localhost
- Simulated slave pushing REPLY frames
- Listener receives and stores readings
"""

import socket
import threading
import time

import pytest

from tmon.listener import Listener
from tmon.storage import Storage
from tmon.udp_receiver import UdpReceiver

from conftest import make_reply


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


@pytest.mark.integration
class TestUdpIntegration:
    """Integration tests for UDP push transport."""

    def test_receive_single_reading(self) -> None:
        """Receive a single pushed reading via UDP."""
        port = _find_free_port()
        receiver = UdpReceiver(port)
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        try:
            # Push a REPLY frame
            frame = make_reply(1, 250, 255, 0, -100)

            def push_later():
                time.sleep(0.05)
                _send_udp(port, frame)

            t = threading.Thread(target=push_later)
            t.start()

            reading = collector.receive_one(1.0)
            t.join()

            assert reading is not None
            assert reading.addr == 1
            assert reading.temp_0 == 250
            assert reading.temp_1 == 255
            assert reading.temp_2 == 0
            assert reading.temp_3 == -100

            # Verify stored
            rows = storage.fetch(10)
            assert len(rows) == 1
            assert rows[0]["addr"] == 1
        finally:
            receiver.close()
            storage.close()

    def test_receive_multiple_slaves(self) -> None:
        """Receive pushed readings from multiple slaves."""
        port = _find_free_port()
        receiver = UdpReceiver(port)
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        try:
            frame1 = make_reply(1, 100, 0, 0, 0)
            frame2 = make_reply(2, 200, 0, 0, 0)
            frame3 = make_reply(3, 300, 0, 0, 0)

            def push_later():
                time.sleep(0.05)
                _send_udp(port, frame1)
                time.sleep(0.02)
                _send_udp(port, frame2)
                time.sleep(0.02)
                _send_udp(port, frame3)

            t = threading.Thread(target=push_later)
            t.start()

            r1 = collector.receive_one(1.0)
            r2 = collector.receive_one(1.0)
            r3 = collector.receive_one(1.0)
            t.join()

            temps = {r.addr: r.temp_0 for r in [r1, r2, r3]}
            assert temps[1] == 100
            assert temps[2] == 200
            assert temps[3] == 300

            rows = storage.fetch(10)
            assert len(rows) == 3
        finally:
            receiver.close()
            storage.close()

    def test_receive_timeout_no_data(self) -> None:
        """receive_one returns None when no data arrives."""
        port = _find_free_port()
        receiver = UdpReceiver(port)
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        try:
            start = time.time()
            reading = collector.receive_one(0.1)
            elapsed = time.time() - start

            assert reading is None
            assert elapsed < 0.3
        finally:
            receiver.close()
            storage.close()

    def test_last_seen_updated(self) -> None:
        """last_seen is updated when reading is received."""
        port = _find_free_port()
        receiver = UdpReceiver(port)
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        try:
            frame = make_reply(5, 123, 0, 0, 0)

            def push_later():
                time.sleep(0.05)
                _send_udp(port, frame)

            t = threading.Thread(target=push_later)
            t.start()

            assert collector.last_seen(5) is None
            collector.receive_one(1.0)
            t.join()

            ts = collector.last_seen(5)
            assert ts is not None
        finally:
            receiver.close()
            storage.close()

    def test_corrupted_frame_ignored(self) -> None:
        """Corrupted frames are ignored, good frames are processed."""
        port = _find_free_port()
        receiver = UdpReceiver(port)
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        try:
            good_frame = make_reply(1, 100, 0, 0, 0)
            # Corrupt the CRC
            bad_frame = good_frame[:-1] + bytes([good_frame[-1] ^ 0xFF])

            def push_later():
                time.sleep(0.05)
                _send_udp(port, bad_frame)  # Should be ignored
                time.sleep(0.02)
                _send_udp(port, good_frame)  # Should be processed

            t = threading.Thread(target=push_later)
            t.start()

            # First receive gets the bad frame (returns None)
            r1 = collector.receive_one(1.0)
            # Second receive gets the good frame
            r2 = collector.receive_one(1.0)
            t.join()

            assert r1 is None
            assert r2 is not None
            assert r2.addr == 1

            rows = storage.fetch(10)
            assert len(rows) == 1
        finally:
            receiver.close()
            storage.close()
