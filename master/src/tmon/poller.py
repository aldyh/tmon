"""Poll loop for querying slave devices.

Sends POLL requests to each configured slave, decodes REPLY frames,
and stores raw int16 temperature readings in Storage.

Example:
    >>> from tmon.poller import Poller
    >>> poller = Poller(bus, storage, [1, 2])
    >>> readings = poller.poll_all()
    >>> readings[0]["addr"]
    1
"""

import logging

from tmon.protocol import (
    encode_request,
    decode_frame,
    parse_reply,
    PROTO_CMD_POLL,
    PROTO_CMD_REPLY,
    PROTO_REPLY_PAYLOAD_LEN,
)

log = logging.getLogger(__name__)


class Poller:
    """Polls slave devices and stores readings.

    Sends a POLL frame to each slave address, waits for a REPLY,
    unpacks the raw int16 temperatures from the payload, and
    inserts them into storage.

    Args:
        bus: Object with ``send(data)`` and ``receive()`` methods.
        storage: Object with ``insert(addr, temps)``.
        slaves: List of integer slave addresses to poll.

    Example:
        >>> poller = Poller(bus, storage, [1, 2])
        >>> results = poller.poll_all()
    """



    def __init__(self, bus, storage, slaves: list[int]):
        """Initialize the poller."""
        self._bus = bus
        self._storage = storage
        self._slaves = list(slaves)

    def poll(self, addr: int) -> dict | None:
        """Poll a single slave and return a reading dict or None.

        Sends a POLL frame, validates the REPLY, and unpacks raw int16
        temperatures.  Returns None on timeout or protocol error.

        Example:
            >>> reading = poller.poll(3)
            >>> reading["temp_0"]
            235
        """
        frame = encode_request(addr, PROTO_CMD_POLL, b"")
        self._bus.send(frame)
        raw = self._bus.receive()

        if not raw:
            log.debug("timeout polling slave %d", addr)
            return None

        try:
            reply = decode_frame(raw)
        except ValueError as exc:
            log.debug("bad frame from slave %d: %s", addr, exc)
            return None

        if reply["addr"] != addr:
            log.debug(
                "addr mismatch: expected %d, got %d", addr, reply["addr"]
            )
            return None

        if reply["cmd"] != PROTO_CMD_REPLY:
            log.debug(
                "unexpected cmd from slave %d: 0x%02X", addr, reply["cmd"]
            )
            return None

        payload = reply["payload"]
        if len(payload) != PROTO_REPLY_PAYLOAD_LEN:
            log.debug(
                "bad payload length from slave %d: %d",
                addr, len(payload),
            )
            return None

        parsed = parse_reply(payload)
        temps = []
        for t in parsed["temperatures"]:
            temps.append(int(t * 10) if t is not None else None)

        return {
            "addr": addr,
            "temp_0": temps[0],
            "temp_1": temps[1],
            "temp_2": temps[2],
            "temp_3": temps[3],
        }

    def poll_all(self) -> list[dict]:
        """Poll all slaves and store successful readings.

        Returns:
            list[dict]: Readings collected this cycle (``addr``,
                ``temp_0`` .. ``temp_3``).

        Example:
            >>> results = poller.poll_all()
            >>> len(results)
            2
        """
        results = []
        for addr in self._slaves:
            reading = self.poll(addr)
            if reading is not None:
                self._storage.insert(
                    reading["addr"],
                    [
                        reading["temp_0"],
                        reading["temp_1"],
                        reading["temp_2"],
                        reading["temp_3"],
                    ],
                )
                results.append(reading)
        return results
