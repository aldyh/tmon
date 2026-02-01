#!/usr/bin/env python3
"""Quick smoke test for the simulator.

Connects to the master PTY, sends a POLL frame, and verifies that
a valid REPLY comes back.  Exits 0 on success, 1 on failure.

This script is invoked by ``make check-simulator`` after socat and
the simulator are already running.

Usage:
    python check_simulator.py <master_pty> <addr>

Args:
    master_pty: Path to the master-side PTY (e.g. /tmp/tmon-master).
    addr: Slave address the simulator is responding as (int).

Example:
    python check_simulator.py /tmp/tmon-master 3
"""

import sys
import struct

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from tmon.bus import Bus
from tmon.protocol import (
    encode_request,
    decode_frame,
    PROTO_CMD_POLL,
    PROTO_CMD_REPLY,
    PROTO_REPLY_PAYLOAD_LEN,
)


def main(master_pty, addr):
    """Send a POLL and verify the REPLY.

    Args:
        master_pty: Path to the master-side PTY.
        addr: Expected slave address (int).

    Returns:
        int: 0 on success, 1 on failure.
    """
    bus = Bus(master_pty, 9600)

    poll = encode_request(addr, PROTO_CMD_POLL, b"")
    bus.send(poll)

    raw = bus.receive()
    if not raw:
        print("FAIL: no response (timeout)")
        bus.close()
        return 1

    try:
        frame = decode_frame(raw)
    except ValueError as exc:
        print("FAIL: bad frame: {}".format(exc))
        bus.close()
        return 1

    if frame["addr"] != addr:
        print("FAIL: wrong addr: expected {}, got {}".format(
            addr, frame["addr"]))
        bus.close()
        return 1

    if frame["cmd"] != PROTO_CMD_REPLY:
        print("FAIL: wrong cmd: expected 0x02, got 0x{:02X}".format(
            frame["cmd"]))
        bus.close()
        return 1

    if len(frame["payload"]) != PROTO_REPLY_PAYLOAD_LEN:
        print("FAIL: wrong payload length: {}".format(
            len(frame["payload"])))
        bus.close()
        return 1

    t0 = struct.unpack_from("<h", frame["payload"], 0)[0]
    print("OK: addr={} temp_0={}".format(addr, t0))
    bus.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: check_simulator.py <master_pty> <addr>",
              file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1], int(sys.argv[2])))
