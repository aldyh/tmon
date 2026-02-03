"""Master daemon -- polls slaves on a schedule and stores readings.

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
from tmon.poller import Poller
from tmon.storage import Storage

log = logging.getLogger(__name__)

# Module-level flag; set by the signal handler.
_shutdown = False


def _on_signal(signum: int, frame) -> None:
    """Signal handler that sets the shutdown flag."""
    global _shutdown
    _shutdown = True


def run(cfg: dict, bus, storage) -> int:
    """Run the poll loop until shutdown is requested.

    Polls all slaves, sleeps for ``cfg["interval"]`` seconds, and
    repeats.  Returns the number of completed cycles when the
    module-level ``_shutdown`` flag is set.

    Example:
        >>> run({"slaves": [3], "interval": 30}, bus, storage)
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
    log.info(
        "starting: port=%s baudrate=%d slaves=%s db=%s interval=%ds",
        cfg["port"], cfg["baudrate"], cfg["slaves"], cfg["db"], cfg["interval"],
    )

    bus = Bus(cfg["port"], cfg["baudrate"])
    storage = Storage(cfg["db"])

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    try:
        run(cfg, bus, storage)
    finally:
        bus.close()
        storage.close()
        log.info("shutting down")


if __name__ == "__main__":
    main()
