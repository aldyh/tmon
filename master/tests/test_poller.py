"""Tests for tmon.poller."""

import struct

from conftest import FakeBus
from tmon.poller import Poller
from tmon.storage import Storage
from tmon.protocol import (
    encode_request,
    crc16_modbus,
    PROTO_CMD_REPLY,
    PROTO_TEMP_INVALID,
)


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


class TestPollSlave:
    """Tests for Poller.poll."""

    def test_success(self):
        """Successful poll returns a reading dict with raw int16 temps."""
        reply = _make_reply(3, 235, 198, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID)
        bus = FakeBus([reply])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [3])

        reading = poller.poll(3)

        assert reading is not None
        assert reading["addr"] == 3
        assert reading["temp_0"] == 235
        assert reading["temp_1"] == 198
        assert reading["temp_2"] is None
        assert reading["temp_3"] is None
        storage.close()

    def test_timeout(self):
        """Timeout returns None."""
        bus = FakeBus([b""])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [1])

        reading = poller.poll(1)
        assert reading is None
        storage.close()

    def test_bad_crc(self):
        """Corrupted CRC returns None."""
        reply = _make_reply(3, 235, 198, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID)
        # Flip last byte to corrupt CRC
        corrupted = reply[:-1] + bytes([reply[-1] ^ 0xFF])
        bus = FakeBus([corrupted])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [3])

        reading = poller.poll(3)
        assert reading is None
        storage.close()

    def test_wrong_addr(self):
        """Reply from wrong address returns None."""
        reply = _make_reply(5, 100, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeBus([reply])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [3])

        reading = poller.poll(3)
        assert reading is None
        storage.close()

    def test_all_channels_valid(self):
        """All four channels valid returns four raw int16 temps."""
        reply = _make_reply(1, 100, 200, 300, 400)
        bus = FakeBus([reply])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [1])

        reading = poller.poll(1)
        assert reading["temp_0"] == 100
        assert reading["temp_1"] == 200
        assert reading["temp_2"] == 300
        assert reading["temp_3"] == 400
        storage.close()

    def test_negative_temps(self):
        """Negative temperatures are unpacked correctly."""
        reply = _make_reply(1, -100, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeBus([reply])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [1])

        reading = poller.poll(1)
        assert reading["temp_0"] == -100
        storage.close()

    def test_sends_poll_frame(self):
        """poll sends a correctly encoded POLL frame."""
        reply = _make_reply(3, 100, PROTO_TEMP_INVALID,
                            PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeBus([reply])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [3])

        poller.poll(3)

        assert len(bus.sent) == 1
        sent = bus.sent[0]
        # POLL frame for addr 3: 01 03 01 00 <crc_lo> <crc_hi>
        assert sent[0] == 0x01  # START
        assert sent[1] == 3     # ADDR
        assert sent[2] == 0x01  # CMD = POLL
        assert sent[3] == 0     # LEN = 0
        storage.close()


class TestRunOnce:
    """Tests for Poller.poll_all."""

    def test_polls_all_slaves(self):
        """poll_all polls each slave and returns readings."""
        reply1 = _make_reply(1, 100, PROTO_TEMP_INVALID,
                             PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        reply2 = _make_reply(2, 200, PROTO_TEMP_INVALID,
                             PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        bus = FakeBus([reply1, reply2])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [1, 2])

        results = poller.poll_all()

        assert len(results) == 2
        assert results[0]["addr"] == 1
        assert results[1]["addr"] == 2

        # Verify storage got both readings
        rows = storage.fetch(10)
        assert len(rows) == 2
        storage.close()

    def test_partial_failure(self):
        """poll_all skips failed slaves and stores successful ones."""
        reply1 = _make_reply(1, 100, PROTO_TEMP_INVALID,
                             PROTO_TEMP_INVALID, PROTO_TEMP_INVALID)
        # Slave 2 times out
        bus = FakeBus([reply1, b""])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [1, 2])

        results = poller.poll_all()

        assert len(results) == 1
        assert results[0]["addr"] == 1

        rows = storage.fetch(10)
        assert len(rows) == 1
        storage.close()

    def test_all_timeout(self):
        """poll_all returns empty list when all slaves time out."""
        bus = FakeBus([b"", b""])
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [1, 2])

        results = poller.poll_all()

        assert results == []
        rows = storage.fetch(10)
        assert len(rows) == 0
        storage.close()
