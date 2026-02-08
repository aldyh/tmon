"""Master daemon -- collects readings from slaves and stores them.

Supports two modes:
- Poll mode (RS-485): actively polls slaves on a schedule
- Push mode (UDP): passively receives readings pushed by slaves

Foreground loop driven by a TOML config file.  Shuts down cleanly
on SIGINT or SIGTERM.

Example:
    Run from the command line::

        tmon master/config.toml -v
"""

import argparse
import logging
import signal
import threading

from tmon.config import load_config
from tmon.serial_bus import SerialBus
from tmon.serial_poller import Poller
from tmon.storage import Storage
from tmon.udp_listener import UDPListener
from tmon.udp_receiver import UDPReceiver

log = logging.getLogger(__name__)

_shutdown = threading.Event()


def _on_signal(signum: int, frame) -> None:
    """Set the module-level shutdown event on SIGINT/SIGTERM."""
    _shutdown.set()


def run_poller(cfg: dict, bus, storage, shutdown: threading.Event) -> int:
    """Run the poll loop until *shutdown* is set.

    Polls all slaves, sleeps for ``cfg["interval"]`` seconds, and
    repeats.  Returns the number of completed cycles.

    Example:
        >>> run_poller({"slaves": [3], "interval": 30}, bus, storage, ev)
        5
    """
    poller = Poller(bus, storage, cfg["slaves"])
    cycles = 0

    while not shutdown.is_set():
        results = poller.poll_all()
        cycles += 1
        log.info(
            "cycle %d: %d/%d slaves responded",
            cycles, len(results), len(cfg["slaves"]),
        )
        remaining = cfg["interval"]
        if remaining > 0:
            shutdown.wait(remaining)

    return cycles


def run_listener(receiver, storage, shutdown: threading.Event) -> int:
    """Run the push receiver loop until *shutdown* is set.

    Receives readings pushed by slaves via UDP and stores them.
    Returns the number of readings received.

    Example:
        >>> run_listener(receiver, storage, ev)
        42
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
    """CLI entry point -- parse args, load config, run the daemon.

    Example:
        From the shell::

            tmon config.toml
            tmon config.toml -v
    """
    _shutdown.clear()

    parser = argparse.ArgumentParser(description="tmon temperature monitor")
    parser.add_argument("config", help="path to TOML config file")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable debug logging",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=level,
    )

    cfg = load_config(args.config)
    transport = cfg["transport"]

    storage = Storage(cfg["db"])
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    if transport == "udp":
        log.info(
            "starting: transport=udp port=%d db=%s",
            cfg["udp_port"], cfg["db"],
        )
        receiver = UDPReceiver(cfg["udp_port"])
        try:
            run_listener(receiver, storage, _shutdown)
        finally:
            receiver.close()
            storage.close()
            log.info("shutting down")
    else:
        # RS-485 poll transport
        log.info(
            "starting: transport=rs485 port=%s baudrate=%d slaves=%s db=%s "
            "interval=%ds",
            cfg["port"], cfg["baudrate"], cfg["slaves"], cfg["db"],
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
