# tmon: A temperature monitoring system

A small, home-use **Raspberry Pi + ESP32** setup for monitoring temperatures over **RS-485**.

## What it is

- **Master (Raspberry Pi):** Python daemon that polls ESP32 slaves over RS-485 (USB adapter) and stores readings in SQLite.
- **Slaves (ESP32):** Each reads up to **4 NTC thermistors** and replies when polled.
- **Protocol:** Simple custom binary frames with **CRC-16/MODBUS**.
- **Scale:** 1–4 slaves; designed to stay small and stable.

## Directory layout

- `master/` — Python 3.11+ polling daemon
  - `src/tmon/` — protocol, bus, poller, storage, config
  - `tests/` — pytest unit tests (no hardware)
  - `tools/` — x86 simulator + `socat` harness (integration tests)
- `slave/` — ESP32 firmware (PlatformIO, Arduino framework)
- `docs/` — documentation (see links below)

## Quick start

### Prerequisites

- Python 3.11+
- [PlatformIO](https://platformio.org/) -- install via
  [pipx](https://pipx.pypa.io/) (`apt` package is outdated on recent
  Ubuntu):

      sudo apt install pipx
      pipx install platformio
      pipx ensurepath          # if ~/.local/bin is not already on PATH

### Build

    make                  # create master venv + deps, build slave firmware

Individual targets:

    make build-master     # Python venv + pip install -e ".[test]"
    make build-slave      # PlatformIO firmware compile

### Test

    make check            # run all tests (no hardware needed)

Individual targets:

    make check-master     # Python unit tests only
    make check-slave      # C/Unity protocol tests only

## Documentation

- [Protocol Specification](docs/protocol.md)
- [Wiring Reference](docs/wiring.md)
- [Storage Specification](docs/storage.md)
