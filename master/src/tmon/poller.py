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

import struct
import logging

from tmon.protocol import (
    encode_request,
    decode_frame,
    PROTO_CMD_POLL,
    PROTO_CMD_REPLY,
    PROTO_REPLY_PAYLOAD_LEN,
    PROTO_TEMP_INVALID,
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



    def __init__(self, bus, storage, slaves):
        """Initialize the poller.

        Args:
            bus: Bus-like object for sending/receiving frames.
            storage: Storage-like object for persisting readings.
            slaves: List of integer slave addresses (1-247).
        """
        self._bus = bus
        self._storage = storage
        self._slaves = list(slaves)

    def poll(self, addr):
        """Poll a single slave and return a reading dict or None.

        Encodes a POLL frame, sends it, waits for a REPLY, validates
        the response (address, command, payload length), and unpacks
        the raw int16 temperatures.  Invalid channels (status bit
        cleared) are stored as None.

        Args:
            addr: Slave address to poll (int, 1-247).

        Returns:
            dict: Reading with keys ``addr``, ``status``,
                ``temp_0`` .. ``temp_3`` (raw int16 or None), or
                None on timeout/error.

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

        status = payload[0]
        temps = []
        for i in range(4):
            raw_val = struct.unpack_from("<h", payload, 1 + i * 2)[0]
            if status & (1 << i) and raw_val != PROTO_TEMP_INVALID:
                temps.append(raw_val)
            else:
                temps.append(None)

        return {
            "addr": addr,
            "status": status,
            "temp_0": temps[0],
            "temp_1": temps[1],
            "temp_2": temps[2],
            "temp_3": temps[3],
        }

    def poll_all(self):
        """Execute a single poll cycle across all slaves.

        Polls each slave in order.  Successful readings are inserted
        into storage.  Returns a list of reading dicts (only the
        successful ones).

        Returns:
            list[dict]: Readings collected this cycle.  Each dict has
                keys ``addr``, ``status``, ``temp_0`` .. ``temp_3``.

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
