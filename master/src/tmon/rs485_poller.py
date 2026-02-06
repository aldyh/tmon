"""Poll loop for querying slave devices.

Sends POLL requests to each configured slave, decodes REPLY frames,
and stores raw int16 temperature readings in Storage.

Example:
    >>> from tmon.rs485_poller import Poller
    >>> poller = Poller(bus, storage, [1, 2])
    >>> readings = poller.poll_all()
    >>> readings[0].addr
    1
"""

import logging

from tmon.protocol import (
    encode_frame,
    decode_frame,
    parse_reply,
    PROTO_CMD_POLL,
    PROTO_CMD_REPLY,
    PROTO_REPLY_PAYLOAD_LEN,
)
from tmon.reading import Reading, fmt_temp

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

    def poll(self, addr: int) -> Reading | None:
        """Poll a single slave and return a Reading or None.

        Sends a POLL frame, validates the REPLY, and unpacks raw int16
        temperatures.  Returns None on timeout or protocol error.

        Example:
            >>> reading = poller.poll(3)
            >>> reading.temp_0
            235
        """
        frame = encode_frame(addr, PROTO_CMD_POLL, b"")
        self._bus.send(frame)
        raw = self._bus.receive()

        # All error conditions return None; details go to the log.
        if not raw:
            log.debug("timeout polling slave %d", addr)
            return None

        try:
            reply = decode_frame(raw)
        except ValueError as exc:
            log.debug("bad frame from slave %d: %s", addr, exc)
            return None

        if reply.addr != addr:
            log.debug(
                "addr mismatch: expected %d, got %d", addr, reply.addr
            )
            return None

        if reply.cmd != PROTO_CMD_REPLY:
            log.debug(
                "unexpected cmd from slave %d: 0x%02X", addr, reply.cmd
            )
            return None

        payload = reply.payload
        if len(payload) != PROTO_REPLY_PAYLOAD_LEN:
            log.debug(
                "bad payload length from slave %d: %d",
                addr, len(payload),
            )
            return None

        temps = parse_reply(payload)

        log.info(
            "slave %d: temps=[%s, %s, %s, %s]",
            addr,
            fmt_temp(temps[0]), fmt_temp(temps[1]),
            fmt_temp(temps[2]), fmt_temp(temps[3]),
        )

        return Reading(
            addr=addr,
            temp_0=temps[0],
            temp_1=temps[1],
            temp_2=temps[2],
            temp_3=temps[3],
        )

    def poll_all(self) -> list[Reading]:
        """Poll all slaves and store successful readings.

        Returns:
            list[Reading]: Readings collected this cycle.

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
                    reading.addr,
                    [
                        reading.temp_0,
                        reading.temp_1,
                        reading.temp_2,
                        reading.temp_3,
                    ],
                )
                results.append(reading)
        self._storage.commit()
        return results
