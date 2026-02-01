# Project plan

Goal: a small, robust temperature monitoring system where a Raspberry Pi polls a few ESP32 nodes over RS-485, stores readings locally, and is easy to test without hardware.

## Assumptions

- 1–4 ESP32 slaves, each with up to 4 NTC thermistors.
- A USB <-> RS-485 adapter on the Pi.
- SQLite is sufficient
- Protocol is custom binary as defined in `docs/protocol.md` and uses **CRC-16/MODBUS**.

## Conventions

- **Python (master):** Python 3.11+, minimal deps (prefer stdlib; `pyserial` is expected).
- **Config:** `config.toml` (stdlib `tomllib` in Python 3.11).
- **Testing:**
  - Unit tests: `pytest` with fakes/mocks (no hardware).
  - Integration tests: `socat` + simulator (`master/tools`).
- **Firmware (slave):** PlatformIO + Arduino framework; keep firmware straightforward.

## Milestones

Use this as the canonical checklist. Keep it up to date as work is completed.

### Setup coding guidelines
- [x] Coding guidlines are GNU for C/C++.  Look up what that means, especially space after function
names.  Braces on lone line, but are indented one more level.  typedef/struct have braces
on next line, but on column 0.  Look it up.
- [x] For python document each method/class with docstrings.
- [x] Document each argument and retval.
- [x] For main API methods, and toplevel externally visible functions include usage/code examples.
- [x] Update CLAUDE.md to include coding guidelines accordingly described above.

### Flesh out docs/wiring.md

- [x] Document the wiring for the esp32.

### Flesh out docs/protocol.md

- [ ] Design protocol.  Remember this is not meant to grow in complexity,
so something simple.
- [ ] Write out docs/protocol.md.
- [ ] Favor clean, elegant, to the point.
- [ ] Provide examples.
- [ ] Explain that it's crc-16/modbus.
- [ ] Remove modbus reference from plan.md.

### Flesh out docs/storage.md

- [ ] document schema and how poll data will be stored in sqlite in docs/storage.md
- [ ] update README.md to link to docs/storage.md

### Setup skeleton test

- [ ] Setup bare stubs for entire project (no API, just stubs)
- [ ] Add stub tests so that we can "run" tests for slave, master, etc, even if just placeholders.
- [ ] We can build the entire system and tests pass.
- [ ] Flesh out "Quick Start" section in README.md.

### Protocol layer (Python)

- [ ] Implement frame encode/decode per `docs/protocol.md`
- [ ] Implement CRC-16/MODBUS
- [ ] Validate length/fields; reject malformed frames cleanly
- [ ] Unit tests: round-trip encode/decode, CRC pass/fail, fuzz-ish malformed inputs
- [ ] Public API: minimal and stable (e.g., `encode_request(...)`, `decode_frame(...)`)

### Protocol layer (ESP32)

- [ ] Implement the same framing + CRC in firmware
- [ ] Unit-test-ish coverage where feasible (host-side tests or embedded tests if lightweight)
- [ ] Ensure consistent endianness/field sizes with Python implementation
- [ ] Use unity for testing protocol while hardware becomes available.
- [ ] Unity tests pass on x86 linux box.

### Simulator (x86)

- [ ] Implement a simple “virtual slave” that speaks the protocol over a pseudo-serial port
- [ ] Provide `run_simulator.sh` (socat wiring) and a minimal README comment in `master/tools/`
- [ ] Integration test: master talks to simulator and receives stable readings
- [ ] Master can poll simulator end-to-end without hardware

### Master poller loop

- [ ] Implement serial bus abstraction
- [ ] Poll loop
- [ ] Unit tests around poll scheduling and timeout behavior using fake bus
- [ ] Poller can run against simulator

### Storage (SQLite)

- [ ] Define schema
- [ ] Write path: insert readings efficiently
- [ ] Basic query helpers
- [ ] Integration test: poller -> storage using simulator
- [ ] SQLite DB gets populated correctly during simulator run

### ESP32 firmware: sensors + RS-485

- [ ] Read NTC thermistors
- [ ] RS-485 transceiver enable/disable control (DE/RE) with correct timing
- [ ] Respond to requests; populate payload with readings + status
- [ ] Real device responds reliably on a physical RS-485 bus

### Integration + polish

- [ ] Real bus smoke test with 1 slave -> then scale to all slaves
- [ ] Document how to add a new slave (address + wiring + config)
- [ ] Confirm error handling (CRC errors, timeouts, missing devices) is reasonable
- [ ] Final pass: remove unused code, ensure docs match behavior
