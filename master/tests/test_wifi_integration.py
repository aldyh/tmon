"""Integration tests for WiFi transport.

Tests the full poll cycle over localhost TCP:
- WifiBus server running on localhost
- Simulated slave connecting and responding
- Poller sends POLL and receives REPLY
"""

import socket
import threading
import time

import pytest

from tmon.poller import Poller
from tmon.protocol import (
    PROTO_CMD_POLL,
    PROTO_START,
    decode_frame,
    encode_request,
)
from tmon.storage import Storage
from tmon.wifi_bus import WifiBus

from conftest import make_reply


def _find_free_port() -> int:
    """Find an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SimulatedSlave:
    """TCP client that responds to POLL with REPLY."""

    def __init__(self, port: int, addr: int, temps: list[int]):
        """Connect to server and start response thread."""
        self._addr = addr
        self._temps = temps
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect(("127.0.0.1", port))
        self._sock.sendall(bytes([addr]))
        self._thread = threading.Thread(target=self._respond_loop, daemon=True)
        self._thread.start()

    def _respond_loop(self) -> None:
        """Read POLL frames and send REPLY."""
        while self._running:
            try:
                self._sock.settimeout(0.1)
                data = self._sock.recv(64)
                if not data:
                    break
                # Parse frame
                if len(data) >= 6 and data[0] == PROTO_START:
                    frame = decode_frame(data)
                    if frame.cmd == PROTO_CMD_POLL and frame.addr == self._addr:
                        reply = make_reply(self._addr, *self._temps)
                        self._sock.sendall(reply)
            except socket.timeout:
                pass
            except OSError:
                break

    def close(self) -> None:
        """Stop the response thread and close socket."""
        self._running = False
        self._thread.join(timeout=1.0)
        try:
            self._sock.close()
        except OSError:
            pass


@pytest.mark.integration
class TestWifiIntegration:
    """Integration tests for WiFi transport."""

    def test_poll_single_slave(self) -> None:
        """Poll a single slave over TCP."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=500)
        storage = Storage(":memory:")
        try:
            slave = SimulatedSlave(port, 1, [250, 255, 0, -100])
            time.sleep(0.2)  # Let slave connect

            poller = Poller(bus, storage, [1])
            reading = poller.poll(1)

            assert reading is not None
            assert reading.addr == 1
            assert reading.temp_0 == 250
            assert reading.temp_1 == 255
            assert reading.temp_2 == 0
            assert reading.temp_3 == -100

            slave.close()
        finally:
            bus.close()
            storage.close()

    def test_poll_multiple_slaves(self) -> None:
        """Poll multiple slaves over TCP."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=500)
        storage = Storage(":memory:")
        try:
            slave1 = SimulatedSlave(port, 1, [100, 0, 0, 0])
            slave2 = SimulatedSlave(port, 2, [200, 0, 0, 0])
            slave3 = SimulatedSlave(port, 3, [300, 0, 0, 0])
            time.sleep(0.3)  # Let slaves connect

            poller = Poller(bus, storage, [1, 2, 3])
            results = poller.poll_all()

            assert len(results) == 3
            temps = {r.addr: r.temp_0 for r in results}
            assert temps[1] == 100
            assert temps[2] == 200
            assert temps[3] == 300

            slave1.close()
            slave2.close()
            slave3.close()
        finally:
            bus.close()
            storage.close()

    def test_poll_offline_slave_returns_none(self) -> None:
        """Polling a non-connected slave returns None."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=100)
        storage = Storage(":memory:")
        try:
            # No slaves connected
            poller = Poller(bus, storage, [99])
            reading = poller.poll(99)

            assert reading is None
        finally:
            bus.close()
            storage.close()

    def test_poll_all_stores_to_db(self) -> None:
        """poll_all stores readings in the database."""
        port = _find_free_port()
        bus = WifiBus("127.0.0.1", port, timeout_ms=500)
        storage = Storage(":memory:")
        try:
            slave = SimulatedSlave(port, 5, [123, 456, 789, 0])
            time.sleep(0.2)

            poller = Poller(bus, storage, [5])
            poller.poll_all()

            rows = storage.fetch(10)
            assert len(rows) == 1
            assert rows[0]["addr"] == 5
            assert rows[0]["temp_0"] == 123

            slave.close()
        finally:
            bus.close()
            storage.close()
