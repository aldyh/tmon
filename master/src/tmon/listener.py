"""Push-based reading listener for receiving slave readings via UDP.

Slaves push REPLY frames periodically; this listener receives them,
decodes temperatures, and stores to the database. No polling needed.

Example:
    >>> from tmon.listener import Listener
    >>> from tmon.udp_receiver import UDPReceiver
    >>> listener = Listener(UDPReceiver(5555), storage)
    >>> listener.receive(1.0)  # Wait up to 1 second
"""

import logging
import time

from tmon.poller import Reading
from tmon.protocol import (
    decode_frame,
    parse_reply,
    PROTO_CMD_REPLY,
    PROTO_REPLY_PAYLOAD_LEN,
)

log = logging.getLogger(__name__)


class Listener:
    """Receives pushed readings from slaves via UDP.

    Listens for REPLY frames pushed by slaves, decodes temperatures,
    and stores them. Tracks last-seen timestamps for offline detection.

    Args:
        receiver: Object with ``recv(timeout_s)`` method.
        storage: Object with ``insert(addr, temps)`` and ``commit()``.

    Example:
        >>> listener = Listener(receiver, storage)
        >>> reading = listener.receive(1.0)
        >>> reading.addr
        3
    """

    def __init__(self, receiver, storage):
        """Initialize the listener."""
        self._receiver = receiver
        self._storage = storage
        self._last_seen: dict[int, float] = {}

    def receive(self, timeout_s: float) -> Reading | None:
        """Receive and process one pushed frame.

        Args:
            timeout_s: Maximum seconds to wait.

        Returns:
            Reading on success, None on timeout or error.

        Example:
            >>> reading = listener.receive(1.0)
            >>> reading.temp_0
            235
        """
        raw = self._receiver.recv(timeout_s)
        if not raw:
            return None

        return self._process_frame(raw)

    def _process_frame(self, raw: bytes) -> Reading | None:
        """Decode frame, store reading, update last-seen."""
        try:
            frame = decode_frame(raw)
        except ValueError as exc:
            log.debug("bad frame: %s", exc)
            return None

        if frame.cmd != PROTO_CMD_REPLY:
            log.debug("unexpected cmd: 0x%02X", frame.cmd)
            return None

        if len(frame.payload) != PROTO_REPLY_PAYLOAD_LEN:
            log.debug("bad payload length: %d", len(frame.payload))
            return None

        temps = parse_reply(frame.payload)
        addr = frame.addr

        def _fmt(t):
            return f"{t / 10:.1f}" if t is not None else "--.-"

        log.info(
            "slave %d: temps=[%s, %s, %s, %s]",
            addr,
            _fmt(temps[0]), _fmt(temps[1]), _fmt(temps[2]), _fmt(temps[3]),
        )

        reading = Reading(
            addr=addr,
            temp_0=temps[0],
            temp_1=temps[1],
            temp_2=temps[2],
            temp_3=temps[3],
        )

        self._storage.insert(addr, temps)
        self._storage.commit()
        self._last_seen[addr] = time.monotonic()

        return reading

    def last_seen(self, addr: int) -> float | None:
        """Return monotonic timestamp of last reading from addr, or None."""
        return self._last_seen.get(addr)

    def stale_slaves(self, max_age_s: float) -> list[int]:
        """Return list of slave addresses not seen within max_age_s seconds."""
        now = time.monotonic()
        return [
            addr for addr, ts in self._last_seen.items()
            if now - ts > max_age_s
        ]
