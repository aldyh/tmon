"""Tests for PushCollector UDP receiver."""

import time

from tmon.collector_poll import Reading
from tmon.collector_push import PushCollector
from tmon.protocol import encode_request, PROTO_CMD_REPLY, PROTO_TEMP_INVALID
from tmon.storage import Storage

from conftest import make_reply


class FakeUdpBus:
    """Fake UDP bus that returns pre-configured frames."""

    def __init__(self, frames: list[bytes]):
        self._frames = list(frames)
        self._index = 0

    def recv(self) -> bytes:
        """Return next frame or empty bytes."""
        if self._index < len(self._frames):
            frame = self._frames[self._index]
            self._index += 1
            return frame
        return b""

    def recv_timeout(self, timeout_s: float) -> bytes:
        """Same as recv for testing."""
        return self.recv()


class TestReceiveOne:
    """Tests for receive_one."""

    def test_receives_and_stores(self) -> None:
        """receive_one decodes frame and stores reading."""
        frame = make_reply(3, 235, 198, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeUdpBus([frame])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        reading = collector.receive_one()

        assert reading is not None
        assert reading.addr == 3
        assert reading.temp_0 == 235
        assert reading.temp_1 == 198
        assert reading.temp_2 is None
        assert reading.temp_3 is None

        # Verify stored
        rows = storage.fetch(10)
        assert len(rows) == 1
        assert rows[0]["addr"] == 3
        assert rows[0]["temp_0"] == 235

        storage.close()

    def test_bad_crc_returns_none(self) -> None:
        """Corrupted frame returns None."""
        frame = make_reply(3, 235, 198, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        corrupted = frame[:-1] + bytes([frame[-1] ^ 0xFF])
        bus = FakeUdpBus([corrupted])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        reading = collector.receive_one()

        assert reading is None
        assert len(storage.fetch(10)) == 0
        storage.close()

    def test_empty_recv_returns_none(self) -> None:
        """Empty recv (timeout) returns None."""
        bus = FakeUdpBus([b""])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        reading = collector.receive_one()

        assert reading is None
        storage.close()

    def test_multiple_readings(self) -> None:
        """Multiple readings from different slaves."""
        frame1 = make_reply(1, 100, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        frame2 = make_reply(2, 200, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeUdpBus([frame1, frame2])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        r1 = collector.receive_one()
        r2 = collector.receive_one()

        assert r1.addr == 1
        assert r1.temp_0 == 100
        assert r2.addr == 2
        assert r2.temp_0 == 200

        rows = storage.fetch(10)
        assert len(rows) == 2

        storage.close()

    def test_negative_temps(self) -> None:
        """Negative temperatures are decoded correctly."""
        frame = make_reply(1, -100, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeUdpBus([frame])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        reading = collector.receive_one()

        assert reading.temp_0 == -100
        storage.close()


class TestLastSeen:
    """Tests for last_seen tracking."""

    def test_updates_on_receive(self) -> None:
        """last_seen is updated when reading is received."""
        frame = make_reply(5, 100, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeUdpBus([frame])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        assert collector.last_seen(5) is None

        collector.receive_one()

        ts = collector.last_seen(5)
        assert ts is not None
        assert ts <= time.monotonic()

        storage.close()

    def test_stale_slaves_empty_initially(self) -> None:
        """stale_slaves returns empty list when no readings yet."""
        bus = FakeUdpBus([])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        assert collector.stale_slaves(60.0) == []
        storage.close()

    def test_stale_slaves_detects_old(self) -> None:
        """stale_slaves detects slaves not seen recently."""
        frame = make_reply(3, 100, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeUdpBus([frame])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        collector.receive_one()

        # Immediately after, not stale
        assert collector.stale_slaves(60.0) == []

        # With 0 max_age, everything is stale
        stale = collector.stale_slaves(0.0)
        assert 3 in stale

        storage.close()


class TestReceiveOneTimeout:
    """Tests for receive_one_timeout."""

    def test_returns_reading_if_available(self) -> None:
        """receive_one_timeout returns reading if frame arrives."""
        frame = make_reply(4, 150, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeUdpBus([frame])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        reading = collector.receive_one_timeout(1.0)

        assert reading is not None
        assert reading.addr == 4
        storage.close()

    def test_returns_none_on_timeout(self) -> None:
        """receive_one_timeout returns None when no frame."""
        bus = FakeUdpBus([b""])
        storage = Storage(":memory:")
        collector = PushCollector(bus, storage)

        reading = collector.receive_one_timeout(0.1)

        assert reading is None
        storage.close()
