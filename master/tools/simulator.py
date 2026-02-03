#!/usr/bin/env python3
"""Virtual slave simulator for tmon.

Listens on a serial port (typically a socat PTY) and responds to
POLL frames with REPLY frames containing synthetic temperatures.
All four channels produce valid readings by default; each channel
has a ~10% chance of being marked invalid on any given cycle.

The simulator always responds as address ADDR (3).

Usage:
    python simulator.py <port>

Args:
    port: Serial port path (e.g. /tmp/tmon-slave).

Example:
    python simulator.py /tmp/tmon-slave
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

ADDR = 3


def run(port: str) -> None:
    """Run the simulator loop.

    Opens *port* via Bus, reads incoming frames, and replies to POLL
    frames addressed to ADDR with synthetic temperature data.
    Each channel produces a random value between 50 and 900 (5.0 to
    90.0 C) with a ~10% chance of being PROTO_TEMP_INVALID.
    """
    bus = Bus(port, 9600)

    print("simulator: addr={} listening on {}".format(ADDR, port),
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

            if frame.addr != ADDR:
                continue

            if frame.cmd != PROTO_CMD_POLL:
                continue

            temps = []
            for _ in range(4):
                if random.random() < 0.1:
                    temps.append(PROTO_TEMP_INVALID)
                else:
                    temps.append(random.randint(50, 900))

            payload = struct.pack("<hhhh", temps[0], temps[1],
                                  temps[2], temps[3])
            reply = encode_request(ADDR, PROTO_CMD_REPLY, payload)
            bus.send(reply)
    except KeyboardInterrupt:
        pass
    finally:
        bus.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: simulator.py <port>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1])
