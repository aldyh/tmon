"""Server daemon -- collects readings from clients and stores them.

Supports two modes:
- Poll mode (RS-485): actively polls clients on a schedule
- Push mode (WiFi): passively receives readings pushed by clients

Foreground loop driven by a TOML config file.  Shuts down cleanly
on SIGINT or SIGTERM.
"""

import argparse
import logging
import signal
import threading

from tmon.config import load_config
from tmon.paths import resolve_config, resolve_db
from tmon.serial_bus import SerialBus
from tmon.serial_poller import Poller
from tmon.storage import Storage
from tmon.udp_listener import UDPListener
from tmon.udp_receiver import UDPReceiver

_RETENTION_DAYS = 365

log = logging.getLogger(__name__)

_shutdown = threading.Event()


def _on_signal(signum: int, frame) -> None:
    """Set the module-level shutdown event on SIGINT/SIGTERM."""
    _shutdown.set()


def run_poller(cfg: dict, bus, storage, shutdown: threading.Event) -> int:
    """Run the poll loop until *shutdown* is set.

    Polls all clients, sleeps for ``cfg["interval"]`` seconds, and
    repeats.  Returns the number of completed cycles.
    """
    poller = Poller(bus, storage, cfg["clients"])
    cycles = 0

    while not shutdown.is_set():
        results = poller.poll_all()
        cycles += 1
        log.info(
            "cycle %d: %d/%d clients responded",
            cycles, len(results), len(cfg["clients"]),
        )
        remaining = cfg["interval"]
        if remaining > 0:
            shutdown.wait(remaining)

    return cycles


def run_listener(receiver, storage, shutdown: threading.Event) -> int:
    """Run the push receiver loop until *shutdown* is set.

    Receives readings pushed by clients via UDP and stores them.
    Returns the number of readings received.
    """
    listener = UDPListener(receiver, storage)
    count = 0

    while not shutdown.is_set():
        # Use timeout so we check shutdown flag periodically
        reading = listener.receive(0.5)
        if reading is not None:
            count += 1

    return count


def main() -> None:
    """CLI entry point -- parse args, load config, run the daemon."""
    _shutdown.clear()

    parser = argparse.ArgumentParser(description="tmon temperature monitor")
    parser.add_argument("config", help="path to TOML config file")
    parser.add_argument(
        "--transport", required=True, choices=("rs485", "wifi"),
        help="transport mode",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable debug logging",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=level,
    )

    config_path = resolve_config(args.config)
    cfg = load_config(config_path, args.transport)
    cfg["db"] = resolve_db(config_path, cfg["db"])
    transport = cfg["transport"]

    storage = Storage(cfg["db"])
    storage.purge(_RETENTION_DAYS)
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    if transport == "wifi":
        log.info(
            "starting: transport=wifi port=%d db=%s",
            cfg["wifi_port"], cfg["db"],
        )
        receiver = UDPReceiver(cfg["wifi_port"])
        try:
            run_listener(receiver, storage, _shutdown)
        finally:
            receiver.close()
            storage.close()
            log.info("shutting down")
    else:
        # RS-485 poll transport
        log.info(
            "starting: transport=rs485 port=%s baudrate=%d clients=%s db=%s "
            "interval=%ds",
            cfg["port"], cfg["baudrate"], cfg["clients"], cfg["db"],
            cfg["interval"],
        )
        bus = SerialBus(cfg["port"], cfg["baudrate"])
        try:
            run_poller(cfg, bus, storage, _shutdown)
        finally:
            bus.close()
            storage.close()
            log.info("shutting down")


if __name__ == "__main__":
    main()
