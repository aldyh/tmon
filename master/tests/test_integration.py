"""Integration tests: poller + simulator over socat PTY pair.

These tests require socat to be installed and are excluded from
the default ``make check-master`` run (marker: ``integration``).

Run with::

    make check-integration
"""

import os
import signal
import shutil
import subprocess
import sys
import time

import pytest

from tmon.bus import Bus
from tmon.poller import Poller
from tmon.storage import Storage

pytestmark = pytest.mark.integration

MASTER_PTY = "/tmp/tmon-test-master"
SLAVE_PTY = "/tmp/tmon-test-slave"
SIM_ADDR = 3
TOOLS_DIR = os.path.join(os.path.dirname(__file__), "..", "tools")


def _socat_available():
    """Check whether socat is on PATH.

    Returns:
        bool: True if socat is available.
    """
    return shutil.which("socat") is not None


@pytest.fixture
def pty_pair():
    """Create a socat PTY pair and start the simulator.

    Yields the master PTY path.  Tears down socat and the
    simulator on exit.

    Yields:
        str: Path to the master-side PTY.
    """
    socat = subprocess.Popen(
        [
            "socat", "-d", "-d",
            "PTY,raw,echo=0,link={}".format(MASTER_PTY),
            "PTY,raw,echo=0,link={}".format(SLAVE_PTY),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for PTYs to appear
    for _ in range(40):
        if os.path.exists(MASTER_PTY) and os.path.exists(SLAVE_PTY):
            break
        time.sleep(0.05)

    sim = subprocess.Popen(
        [sys.executable, os.path.join(TOOLS_DIR, "simulator.py"),
         SLAVE_PTY, "9600"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Give the simulator a moment to open the port
    time.sleep(0.3)

    yield MASTER_PTY

    sim.terminate()
    sim.wait()
    socat.terminate()
    socat.wait()
    for p in (MASTER_PTY, SLAVE_PTY):
        if os.path.exists(p):
            os.unlink(p)


@pytest.mark.skipif(not _socat_available(), reason="socat not installed")
class TestIntegration:
    """Integration tests using socat + simulator."""

    def test_poll_single_slave(self, pty_pair):
        """Poller.poll_all polls the simulator and gets a reading."""
        bus = Bus(pty_pair, 9600, timeout_ms=200)
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [SIM_ADDR])

        results = poller.poll_all()

        assert len(results) == 1
        r = results[0]
        assert r.addr == SIM_ADDR
        # All four channels should be present (valid int16 or None)
        for val in (r.temp_0, r.temp_1, r.temp_2, r.temp_3):
            if val is not None:
                assert 50 <= val <= 900

        # Verify storage was populated
        rows = storage.fetch(10)
        assert len(rows) == 1

        bus.close()
        storage.close()

    def test_multiple_polls(self, pty_pair):
        """Multiple poll_all calls accumulate readings in storage."""
        bus = Bus(pty_pair, 9600, timeout_ms=200)
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [SIM_ADDR])

        for _ in range(3):
            results = poller.poll_all()
            assert len(results) == 1

        rows = storage.fetch(10)
        assert len(rows) == 3

        bus.close()
        storage.close()

    def test_temp_values_in_range(self, pty_pair):
        """Simulator produces temperatures in the 50-900 range."""
        bus = Bus(pty_pair, 9600, timeout_ms=200)
        storage = Storage(":memory:")
        poller = Poller(bus, storage, [SIM_ADDR])

        results = poller.poll_all()
        r = results[0]
        for val in (r.temp_0, r.temp_1, r.temp_2, r.temp_3):
            if val is not None:
                assert 50 <= val <= 900

        bus.close()
        storage.close()

    def test_daemon_subprocess(self, pty_pair, tmp_path):
        """Daemon starts, polls simulator, stores readings, shuts down."""
        db_path = os.path.join(str(tmp_path), "test.db")
        config_path = os.path.join(str(tmp_path), "test.toml")

        with open(config_path, "w") as f:
            f.write('port = "%s"\n' % pty_pair)
            f.write("baudrate = 9600\n")
            f.write("slaves = [%d]\n" % SIM_ADDR)
            f.write('db = "%s"\n' % db_path)
            f.write("interval = 1\n")
            f.write("timeout = 200\n")

        proc = subprocess.Popen(
            [sys.executable, "-m", "tmon.daemon", config_path, "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Let it run a few poll cycles
        time.sleep(4)

        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

        # SIGTERM is handled gracefully; exit code 0.
        # If the signal fires during sleep before the handler runs,
        # Python may exit with -SIGTERM; accept either.
        assert proc.returncode in (0, -signal.SIGTERM)

        # Verify readings were stored
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM readings")
        count = cursor.fetchone()[0]
        conn.close()

        assert count >= 2
