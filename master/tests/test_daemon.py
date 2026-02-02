"""Tests for tmon.daemon."""

import struct
import threading

from conftest import FakeBus
from tmon.daemon import run, _on_signal
from tmon.protocol import encode_request, PROTO_CMD_REPLY, PROTO_TEMP_INVALID
from tmon.storage import Storage
import tmon.daemon as daemon_mod


def _make_reply(addr, t0, t1, t2, t3):
    """Build a valid REPLY frame for testing.

    Args:
        addr: Slave address (int).
        t0: Channel 0 raw int16 temperature.
        t1: Channel 1 raw int16 temperature.
        t2: Channel 2 raw int16 temperature.
        t3: Channel 3 raw int16 temperature.

    Returns:
        bytes: Complete REPLY frame.
    """
    payload = struct.pack("<hhhh", t0, t1, t2, t3)
    return encode_request(addr, PROTO_CMD_REPLY, payload)


class CountingBus:
    """Bus that counts send calls and signals shutdown after N polls.

    Args:
        reply: Canned reply frame to return from receive().
        max_polls: Number of poll cycles before triggering shutdown.

    Example:
        >>> bus = CountingBus(_make_reply(1, 100, 0, 0, 0), 2)
        >>> bus.receive()
        b'...'
    """

    def __init__(self, reply, max_polls):
        """Initialize the counting bus.

        Args:
            reply: Bytes to return from receive().
            max_polls: Trigger shutdown after this many send() calls.
        """
        self._reply = reply
        self._max_polls = max_polls
        self.send_count = 0

    def send(self, data):
        """Record a send and trigger shutdown when limit is reached.

        Args:
            data: Bytes that would be sent on a real bus.
        """
        self.send_count += 1
        if self.send_count >= self._max_polls:
            daemon_mod._shutdown = True

    def receive(self):
        """Return the canned reply.

        Returns:
            bytes: The pre-configured reply frame.
        """
        return self._reply

    def close(self):
        """No-op close for test compatibility."""
        pass


class TestRun:
    """Tests for the daemon run() function."""

    def test_polls_and_stores(self):
        """run() calls poll_all and stores readings before shutdown."""
        daemon_mod._shutdown = False
        reply = _make_reply(3, 250, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = CountingBus(reply, 2)
        storage = Storage(":memory:")
        cfg = {"slaves": [3], "interval": 0}

        cycles = run(cfg, bus, storage)

        assert cycles >= 1
        rows = storage.fetch(10)
        assert len(rows) >= 1
        assert rows[0]["addr"] == 3
        storage.close()

    def test_shutdown_flag_stops_loop(self):
        """Setting _shutdown before run() causes immediate return."""
        daemon_mod._shutdown = True
        reply = _make_reply(1, 100, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeBus([reply])
        storage = Storage(":memory:")
        cfg = {"slaves": [1], "interval": 0}

        cycles = run(cfg, bus, storage)

        assert cycles == 0
        storage.close()

    def test_on_signal_sets_shutdown(self):
        """_on_signal sets the _shutdown flag."""
        daemon_mod._shutdown = False
        _on_signal(2, None)
        assert daemon_mod._shutdown is True

    def test_multiple_slaves(self):
        """run() polls all configured slaves each cycle."""
        daemon_mod._shutdown = False
        reply1 = _make_reply(1, 100, PROTO_TEMP_INVALID,
                             PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        reply2 = _make_reply(2, 200, PROTO_TEMP_INVALID,
                             PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)

        class MultiBus:
            """Bus returning alternating replies for two slaves.

            Args:
                replies: List of reply frames to cycle through.
                max_sends: Trigger shutdown after this many sends.
            """

            def __init__(self, replies, max_sends):
                """Initialize with reply list and send limit.

                Args:
                    replies: List of bytes replies.
                    max_sends: Shutdown trigger count.
                """
                self._replies = replies
                self._idx = 0
                self._max = max_sends
                self._sends = 0

            def send(self, data):
                """Record send and trigger shutdown at limit.

                Args:
                    data: Bytes that would be sent.
                """
                self._sends += 1
                if self._sends >= self._max:
                    daemon_mod._shutdown = True

            def receive(self):
                """Return next reply in rotation.

                Returns:
                    bytes: Next canned reply.
                """
                r = self._replies[self._idx % len(self._replies)]
                self._idx += 1
                return r

            def close(self):
                """No-op close."""
                pass

        bus = MultiBus([reply1, reply2], 4)
        storage = Storage(":memory:")
        cfg = {"slaves": [1, 2], "interval": 0}

        cycles = run(cfg, bus, storage)

        assert cycles >= 1
        rows = storage.fetch(10)
        assert len(rows) >= 2
        storage.close()
