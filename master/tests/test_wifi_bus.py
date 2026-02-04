"""Tests for WifiBus TCP server."""

import socket
import time

import pytest

from tmon.wifi_bus import WifiBus


def _connect_slave(port: int, addr: int) -> socket.socket:
    """Connect to WifiBus server and send address byte."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", port))
    sock.sendall(bytes([addr]))
    return sock


def _find_free_port() -> int:
    """Find an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestWifiBusConnect:
    """Test connection handling."""

    def test_accept_slave_connection(self) -> None:
        """Server accepts slave and registers its address."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=200)
        try:
            slave = _connect_slave(port, 5)
            time.sleep(0.1)  # Let accept thread process

            # Verify slave is registered by sending a frame to it
            # Frame: START=0x01, ADDR=5, CMD=1, LEN=0, CRC=xx xx
            frame = b"\x01\x05\x01\x00\x80\x04"
            bus.send(frame)

            slave.settimeout(1.0)
            received = slave.recv(10)
            assert received == frame
            slave.close()
        finally:
            bus.close()

    def test_slave_reconnect_replaces_old(self) -> None:
        """New connection from same address replaces old socket."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=200)
        try:
            slave1 = _connect_slave(port, 3)
            time.sleep(0.1)

            slave2 = _connect_slave(port, 3)
            time.sleep(0.1)

            # Old socket should be closed
            slave1.settimeout(0.5)
            try:
                data = slave1.recv(1)
                assert data == b""  # EOF means closed
            except (OSError, ConnectionResetError):
                pass  # Also acceptable

            # New socket should work
            frame = b"\x01\x03\x01\x00\x41\xc4"
            bus.send(frame)
            slave2.settimeout(1.0)
            assert slave2.recv(10) == frame

            slave1.close()
            slave2.close()
        finally:
            bus.close()


class TestWifiBusSendReceive:
    """Test send and receive."""

    def test_send_routes_to_correct_slave(self) -> None:
        """Send routes frame based on ADDR byte."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=200)
        try:
            slave1 = _connect_slave(port, 1)
            slave2 = _connect_slave(port, 2)
            time.sleep(0.1)

            # Send to slave 2
            frame2 = b"\x01\x02\x01\x00\x01\xc4"
            bus.send(frame2)

            slave1.settimeout(0.2)
            slave2.settimeout(0.2)

            # Slave 1 should not receive
            try:
                data1 = slave1.recv(10)
                assert data1 == b""
            except socket.timeout:
                pass

            # Slave 2 should receive
            data2 = slave2.recv(10)
            assert data2 == frame2

            slave1.close()
            slave2.close()
        finally:
            bus.close()

    def test_receive_complete_frame(self) -> None:
        """Receive assembles complete frame from header + payload."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=500)
        try:
            slave = _connect_slave(port, 4)
            time.sleep(0.1)

            # Send poll to slave
            poll = b"\x01\x04\x01\x00\xc0\x05"
            bus.send(poll)

            # Slave sends reply: 8-byte payload (4 temps)
            # START=0x01, ADDR=4, CMD=0x02, LEN=8, payload, CRC
            reply = b"\x01\x04\x02\x08\xe8\x03\xf4\x01\x00\x00\xff\x7f\xdb\x5a"
            slave.sendall(reply)

            received = bus.receive()
            assert received == reply
            slave.close()
        finally:
            bus.close()

    def test_receive_timeout_returns_empty(self) -> None:
        """Receive returns empty bytes on timeout."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=100)
        try:
            slave = _connect_slave(port, 1)
            time.sleep(0.1)

            bus.send(b"\x01\x01\x01\x00\x40\x04")
            # Slave doesn't respond

            start = time.time()
            result = bus.receive()
            elapsed = time.time() - start

            assert result == b""
            assert elapsed < 0.5  # Should timeout quickly
            slave.close()
        finally:
            bus.close()

    def test_receive_partial_frame_returns_empty(self) -> None:
        """Receive returns empty if slave sends incomplete frame."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=100)
        try:
            slave = _connect_slave(port, 1)
            time.sleep(0.1)

            bus.send(b"\x01\x01\x01\x00\x40\x04")
            slave.sendall(b"\x01\x01")  # Incomplete header

            result = bus.receive()
            assert result == b""
            slave.close()
        finally:
            bus.close()

    def test_send_to_disconnected_slave(self) -> None:
        """Send to non-existent slave is a no-op."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=100)
        try:
            # No slaves connected, send should not raise
            bus.send(b"\x01\x99\x01\x00\x00\x00")
            # Receive should return empty
            result = bus.receive()
            assert result == b""
        finally:
            bus.close()


class TestWifiBusClose:
    """Test shutdown."""

    def test_close_stops_accept_thread(self) -> None:
        """Close shuts down cleanly."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=100)
        slave = _connect_slave(port, 1)
        time.sleep(0.1)

        bus.close()

        # Server should no longer accept
        with pytest.raises(OSError):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect(("127.0.0.1", port))
            sock.close()

        slave.close()
