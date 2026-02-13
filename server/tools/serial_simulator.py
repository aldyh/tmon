#!/usr/bin/env python3
"""Virtual serial sensor simulator for tmon.

Listens on a serial port (typically a socat PTY) and responds to
POLL frames with REPLY frames containing synthetic temperatures.
All four channels produce valid readings by default; each channel
has a ~10% chance of being marked invalid on any given cycle.

The simulator responds to any address (promiscuous mode), echoing
the address from the incoming frame in the reply.

Usage:
    python serial_simulator.py <port> <baudrate>

Args:
    port: Serial port path (e.g. /tmp/tmon-sensor).
    baudrate: Baud rate (e.g. 9600).
"""

import random
import struct
import sys

# Add parent src to path so we can import tmon
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from tmon.serial_bus import SerialBus
from tmon.protocol import (
    encode_frame,
    decode_frame,
    PROTO_CMD_POLL,
    PROTO_CMD_REPLY,
    PROTO_TEMP_INVALID,
)


def run(port: str, baudrate: int) -> None:
    """Run the simulator loop.

    Opens *port* via Bus at *baudrate*, reads incoming frames, and
    replies to POLL frames with synthetic temperature data.  Responds
    to any address.  Each channel produces a random value between 50
    and 900 (5.0 to 90.0 C) with a ~10% chance of being PROTO_TEMP_INVALID.
    """
    bus = SerialBus(port, baudrate)

    print("serial_simulator: listening on {}".format(port), flush=True)

    try:
        while True:
            raw = bus.receive()
            if not raw:
                continue

            try:
                frame = decode_frame(raw)
            except ValueError:
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
            reply = encode_frame(frame.addr, PROTO_CMD_REPLY, payload)
            bus.send(reply)
    except KeyboardInterrupt:
        pass
    finally:
        bus.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: serial_simulator.py <port> <baudrate>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1], int(sys.argv[2]))
