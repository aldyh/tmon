"""Tests for tmon.daemon."""

import threading

import tmon.daemon as daemon_mod
from conftest import FakeBus, make_reply
from tmon.daemon import run_poller, run_listener, _on_signal
from tmon.protocol import PROTO_TEMP_INVALID
from tmon.storage import Storage


class CountingBus:
    """Test double: counts sends, triggers shutdown after max_polls."""

    def __init__(self, reply: bytes, max_polls: int, shutdown: threading.Event):
        """Initialize with canned reply, send limit, and shutdown event."""
        self._reply = reply
        self._max_polls = max_polls
        self._shutdown = shutdown
        self.send_count = 0

    def send(self, data: bytes) -> None:
        """Record send; trigger shutdown when limit reached."""
        self.send_count += 1
        if self.send_count >= self._max_polls:
            self._shutdown.set()

    def receive(self) -> bytes:
        """Return the canned reply."""
        return self._reply

    def close(self) -> None:
        """No-op for test compatibility."""
        pass


class CountingReceiver:
    """Test double: returns canned frames via recv(), triggers shutdown at limit."""

    def __init__(self, frame: bytes, max_recvs: int, shutdown: threading.Event):
        """Initialize with canned frame, receive limit, and shutdown event."""
        self._frame = frame
        self._max_recvs = max_recvs
        self._shutdown = shutdown
        self.recv_count = 0

    def recv(self, timeout_s: float) -> bytes:
        """Return the canned frame; trigger shutdown when limit reached."""
        self.recv_count += 1
        if self.recv_count >= self._max_recvs:
            self._shutdown.set()
        return self._frame


class TestRunPoller:
    """Tests for the daemon run_poller() function."""

    def test_polls_and_stores(self):
        """run_poller() calls poll_all and stores readings before shutdown."""
        shutdown = threading.Event()
        reply = make_reply(3, 250, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = CountingBus(reply, 2, shutdown)
        storage = Storage(":memory:")
        cfg = {"sensors": [3], "interval": 0}

        cycles = run_poller(cfg, bus, storage, shutdown)

        assert cycles >= 1
        rows = storage.fetch(10)
        assert len(rows) >= 1
        assert rows[0]["addr"] == 3
        storage.close()

    def test_shutdown_flag_stops_loop(self):
        """Setting shutdown before run_poller() causes immediate return."""
        shutdown = threading.Event()
        shutdown.set()
        reply = make_reply(1, 100, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeBus([reply])
        storage = Storage(":memory:")
        cfg = {"sensors": [1], "interval": 0}

        cycles = run_poller(cfg, bus, storage, shutdown)

        assert cycles == 0
        storage.close()

    def test_on_signal_sets_shutdown(self):
        """_on_signal sets the module-level shutdown event."""
        daemon_mod._shutdown.clear()
        _on_signal(2, None)
        assert daemon_mod._shutdown.is_set()

    def test_multiple_sensors(self):
        """run_poller() polls all configured sensors each cycle."""
        shutdown = threading.Event()
        reply1 = make_reply(1, 100, PROTO_TEMP_INVALID,
                             PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        reply2 = make_reply(2, 200, PROTO_TEMP_INVALID,
                             PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)

        class MultiBus:
            """Test double: cycles through replies, shuts down at limit."""

            def __init__(self, replies: list[bytes], max_sends: int,
                         shutdown_ev: threading.Event):
                """Initialize with reply list, send limit, and shutdown event."""
                self._replies = replies
                self._idx = 0
                self._max = max_sends
                self._sends = 0
                self._shutdown = shutdown_ev

            def send(self, data: bytes) -> None:
                """Record send; trigger shutdown at limit."""
                self._sends += 1
                if self._sends >= self._max:
                    self._shutdown.set()

            def receive(self) -> bytes:
                """Return next reply in rotation."""
                r = self._replies[self._idx % len(self._replies)]
                self._idx += 1
                return r

            def close(self) -> None:
                """No-op for test compatibility."""
                pass

        bus = MultiBus([reply1, reply2], 4, shutdown)
        storage = Storage(":memory:")
        cfg = {"sensors": [1, 2], "interval": 0}

        cycles = run_poller(cfg, bus, storage, shutdown)

        assert cycles >= 1
        rows = storage.fetch(10)
        assert len(rows) >= 2
        storage.close()


class TestRunListener:
    """Tests for the daemon run_listener() function."""

    def test_receives_and_stores(self):
        """run_listener() receives frames and stores readings."""
        shutdown = threading.Event()
        frame = make_reply(3, 250, PROTO_TEMP_INVALID,
                           PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        receiver = CountingReceiver(frame, 2, shutdown)
        storage = Storage(":memory:")

        count = run_listener(receiver, storage, shutdown)

        assert count >= 1
        rows = storage.fetch(10)
        assert len(rows) >= 1
        assert rows[0]["addr"] == 3
        storage.close()

    def test_shutdown_flag_stops_listener(self):
        """Setting shutdown before run_listener() causes immediate return."""
        shutdown = threading.Event()
        shutdown.set()
        frame = make_reply(1, 100, PROTO_TEMP_INVALID,
                           PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        receiver = CountingReceiver(frame, 1, shutdown)
        storage = Storage(":memory:")

        count = run_listener(receiver, storage, shutdown)

        assert count == 0
        storage.close()
