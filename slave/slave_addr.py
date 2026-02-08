"""PlatformIO extra script to set SLAVE_ADDR from environment variable."""
Import("env")
import os

ADDR_MIN = 1
ADDR_MAX = 247

raw = os.environ.get("SLAVE_ADDR", "1")

try:
    addr = int(raw)
except ValueError:
    print(f"SLAVE_ADDR={raw!r}: not a valid integer")
    env.Exit(1)

if addr < ADDR_MIN or addr > ADDR_MAX:
    print(f"SLAVE_ADDR={addr}: out of range ({ADDR_MIN}-{ADDR_MAX})")
    env.Exit(1)

env.Append(BUILD_FLAGS=[f"-DSLAVE_ADDR={addr}"])
