"""Shared pytest fixtures for tmon tests."""

import struct

from tmon.protocol import encode_request, PROTO_CMD_REPLY


def make_reply(addr: int, t0: int, t1: int, t2: int, t3: int) -> bytes:
    """Build a valid REPLY frame for testing."""
    payload = struct.pack("<hhhh", t0, t1, t2, t3)
    return encode_request(addr, PROTO_CMD_REPLY, payload)


class FakeBus:
    """Test double for Bus: canned responses, records sent data."""

    def __init__(self, responses: list[bytes]):
        """Initialize with canned responses."""
        self._responses = list(responses)
        self.sent = []

    def send(self, data: bytes) -> None:
        """Record *data* for later inspection."""
        self.sent.append(data)

    def receive(self) -> bytes:
        """Return the next canned response, or empty bytes if exhausted."""
        if self._responses:
            return self._responses.pop(0)
        return b""
