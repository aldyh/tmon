#!/usr/bin/env python3
"""Virtual slave simulator for tmon.

Listens on a serial port (typically a socat PTY) and responds to
POLL frames with REPLY frames containing synthetic temperatures.
Channels 0 and 1 produce valid readings with slight variation
each cycle; channels 2 and 3 are invalid.

Usage:
    python simulator.py <port> <addr>

Args:
    port: Serial port path (e.g. /tmp/tmon-slave).
    addr: Slave address to respond as (int, 1-247).

Example:
    python simulator.py /tmp/tmon-slave 3
"""

import struct
import sys
import random

# Add parent src to path so we can import tmon
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from tmon.bus import Bus
from tmon.protocol import (
    encode_request,
    decode_frame,
    PROTO_CMD_POLL,
    PROTO_CMD_REPLY,
    PROTO_TEMP_INVALID,
)


def make_reply_payload(temps):
    """Build an 8-byte REPLY payload.

    Args:
        temps: List of four int16 temperature values.

    Returns:
        bytes: 8-byte payload.
    """
    return struct.pack("<hhhh", temps[0], temps[1],
                       temps[2], temps[3])


def run(port, addr):
    """Run the simulator loop.

    Opens *port* via Bus, reads incoming frames, and replies to POLL
    frames addressed to *addr* with synthetic temperature data.

    Args:
        port: Serial port device path.
        addr: Slave address to respond as (int).
    """
    bus = Bus(port, 9600)
    base_t0 = 235   # 23.5 C
    base_t1 = 198   # 19.8 C

    print("simulator: addr={} listening on {}".format(addr, port),
          flush=True)

    try:
        while True:
            raw = bus.receive()
            if not raw:
                continue

            try:
                frame = decode_frame(raw)
            except ValueError:
                continue

            if frame["addr"] != addr:
                continue

            if frame["cmd"] != PROTO_CMD_POLL:
                continue

            # Generate synthetic temps with slight variation
            t0 = base_t0 + random.randint(-5, 5)
            t1 = base_t1 + random.randint(-5, 5)
            payload = make_reply_payload(
                [t0, t1, PROTO_TEMP_INVALID, PROTO_TEMP_INVALID]
            )
            reply = encode_request(addr, PROTO_CMD_REPLY, payload)
            bus.send(reply)
    except KeyboardInterrupt:
        pass
    finally:
        bus.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: simulator.py <port> <addr>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1], int(sys.argv[2]))
