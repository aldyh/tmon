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

### Master

```bash
cd master
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
deactivate
```

### ESP32 slave

Requires [PlatformIO](https://platformio.org/).

```bash
cd slave
pio run
```

### Testing without hardware

All master unit tests run on x86 Linux without any ESP32 hardware:

```bash
cd master
. .venv/bin/activate
pytest
deactivate
```

## Documentation

- [Protocol Specification](docs/protocol.md)
- [Wiring Reference](docs/wiring.md)
- [Storage Specification](docs/storage.md)
