"""Tests for Listener UDP receiver."""

from tmon.poller import Reading
from tmon.listener import Listener
from tmon.protocol import encode_request, PROTO_CMD_REPLY, PROTO_TEMP_INVALID
from tmon.storage import Storage

from conftest import make_reply


class FakeReceiver:
    """Fake receiver that returns pre-configured frames."""

    def __init__(self, frames: list[bytes]):
        self._frames = list(frames)
        self._index = 0

    def recv(self, timeout_s: float) -> bytes:
        """Return next frame or empty bytes."""
        if self._index < len(self._frames):
            frame = self._frames[self._index]
            self._index += 1
            return frame
        return b""


class TestReceiveOne:
    """Tests for receive."""

    def test_receives_and_stores(self) -> None:
        """receive decodes frame and stores reading."""
        frame = make_reply(3, 235, 198, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        receiver = FakeReceiver([frame])
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        reading = collector.receive(1.0)

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
        receiver = FakeReceiver([corrupted])
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        reading = collector.receive(1.0)

        assert reading is None
        assert len(storage.fetch(10)) == 0
        storage.close()

    def test_empty_recv_returns_none(self) -> None:
        """Empty recv (timeout) returns None."""
        receiver = FakeReceiver([b""])
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        reading = collector.receive(1.0)

        assert reading is None
        storage.close()

    def test_multiple_readings(self) -> None:
        """Multiple readings from different slaves."""
        frame1 = make_reply(1, 100, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        frame2 = make_reply(2, 200, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        receiver = FakeReceiver([frame1, frame2])
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        r1 = collector.receive(1.0)
        r2 = collector.receive(1.0)

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
        receiver = FakeReceiver([frame])
        storage = Storage(":memory:")
        collector = Listener(receiver, storage)

        reading = collector.receive(1.0)

        assert reading.temp_0 == -100
        storage.close()
