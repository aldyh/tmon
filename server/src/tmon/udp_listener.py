"""Push-based reading listener for receiving slave readings via UDP.

Slaves push REPLY frames periodically; this listener receives them,
decodes temperatures, and stores to the database. No polling needed.

Example:
    >>> from tmon.udp_listener import UDPListener
    >>> from tmon.udp_receiver import UDPReceiver
    >>> listener = UDPListener(UDPReceiver(5555), storage)
    >>> listener.receive(1.0)  # Wait up to 1 second
"""

import logging

from tmon.reading import Reading, fmt_temp
from tmon.protocol import (
    decode_frame,
    parse_reply,
    PROTO_CMD_REPLY,
    PROTO_REPLY_PAYLOAD_LEN,
)

log = logging.getLogger(__name__)


class UDPListener:
    """Receives pushed readings from slaves via UDP.

    Listens for REPLY frames pushed by slaves, decodes temperatures,
    and stores them.

    Args:
        receiver: Object with ``recv(timeout_s)`` method.
        storage: Object with ``insert(addr, temps)`` and ``commit()``.

    Example:
        >>> listener = UDPListener(receiver, storage)
        >>> reading = listener.receive(1.0)
        >>> reading.addr
        3
    """

    def __init__(self, receiver, storage):
        """Initialize the listener."""
        self._receiver = receiver
        self._storage = storage

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

        log.info(
            "slave %d: temps=[%s, %s, %s, %s]",
            addr,
            fmt_temp(temps[0]), fmt_temp(temps[1]),
            fmt_temp(temps[2]), fmt_temp(temps[3]),
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

        return reading
