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
import time

from tmon.bus import Bus
from tmon.config import load_config
from tmon.listener import Listener
from tmon.poller import Poller
from tmon.storage import Storage
from tmon.udp_receiver import UDPReceiver

log = logging.getLogger(__name__)

# Module-level shutdown flag set by signal handler.  This is the classic
# Unix daemon pattern -- simple and correct for a single-threaded poll loop.
_shutdown = False


def _on_signal(signum: int, frame) -> None:
    """Signal handler that sets the shutdown flag."""
    global _shutdown
    _shutdown = True


def run_poll(cfg: dict, bus, storage) -> int:
    """Run the poll loop until shutdown is requested.

    Polls all slaves, sleeps for ``cfg["interval"]`` seconds, and
    repeats.  Returns the number of completed cycles when the
    module-level ``_shutdown`` flag is set.

    Example:
        >>> run_poll({"slaves": [3], "interval": 30}, bus, storage)
        5
    """
    poller = Poller(bus, storage, cfg["slaves"])
    cycles = 0

    while not _shutdown:
        results = poller.poll_all()
        cycles += 1
        log.info(
            "cycle %d: %d/%d slaves responded",
            cycles, len(results), len(cfg["slaves"]),
        )
        # Sleep in short increments so we notice shutdown quickly.
        deadline = time.monotonic() + cfg["interval"]
        while not _shutdown and time.monotonic() < deadline:
            time.sleep(0.25)

    return cycles


def run_push(bus, storage) -> int:
    """Run the push receiver loop until shutdown is requested.

    Receives readings pushed by slaves via UDP and stores them.
    Returns the number of readings received when shutdown is signaled.

    Example:
        >>> run_push(bus, storage)
        42
    """
    listener = Listener(bus, storage)
    count = 0

    while not _shutdown:
        # Use timeout so we check shutdown flag periodically
        reading = listener.receive_one(0.5)
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
    global _shutdown
    _shutdown = False

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
            run_push(receiver, storage)
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
        bus = Bus(cfg["port"], cfg["baudrate"])
        try:
            run_poll(cfg, bus, storage)
        finally:
            bus.close()
            storage.close()
            log.info("shutting down")


if __name__ == "__main__":
    main()
