"""Tests for generate_data.py."""

import os
import sqlite3
import tempfile
from unittest.mock import patch

from generate_data import generate


class TestGenerate:
    """Verify mock data generation produces valid, realistic data."""

    def test_row_count(self):
        """One day = 2880 intervals * 3 slaves = 8640 rows."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            n = generate(path, 1, 42)
            assert n == 2880 * 3
        finally:
            os.unlink(path)

    def test_temperature_ranges(self):
        """All non-null temperatures fall within a plausible range."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            generate(path, 7, 42)
            conn = sqlite3.connect(path)
            for col in ("temp_0", "temp_1", "temp_2", "temp_3"):
                row = conn.execute(
                    "SELECT MIN(%s), MAX(%s) FROM readings"
                    " WHERE %s IS NOT NULL" % (col, col, col)
                ).fetchone()
                if row[0] is not None:
                    # -20C to 60C in tenths
                    assert row[0] >= -200, "%s min too low: %d" % (col, row[0])
                    assert row[1] <= 600, "%s max too high: %d" % (col, row[1])
            conn.close()
        finally:
            os.unlink(path)

    def test_timestamps_ordered(self):
        """Timestamps within each slave are strictly non-decreasing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            generate(path, 3, 42)
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            for addr in (1, 2, 3):
                rows = conn.execute(
                    "SELECT ts FROM readings WHERE addr = ?"
                    " ORDER BY id", (addr,)
                ).fetchall()
                for i in range(1, len(rows)):
                    assert rows[i]["ts"] >= rows[i - 1]["ts"]
            conn.close()
        finally:
            os.unlink(path)

    def test_null_presence(self):
        """Slave 3 channel 1 has some NULL values."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            generate(path, 30, 42)
            conn = sqlite3.connect(path)
            null_count = conn.execute(
                "SELECT COUNT(*) FROM readings"
                " WHERE addr = 3 AND temp_1 IS NULL"
            ).fetchone()[0]
            total = conn.execute(
                "SELECT COUNT(*) FROM readings WHERE addr = 3"
            ).fetchone()[0]
            conn.close()
            # Expect roughly 5% nulls; check at least some exist
            assert null_count > 0
            assert null_count < total
        finally:
            os.unlink(path)

    def test_unused_channels_are_null(self):
        """Channels beyond a slave's count are always NULL."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            generate(path, 1, 42)
            conn = sqlite3.connect(path)
            # Slave 2 has 3 channels: temp_3 should always be NULL
            non_null = conn.execute(
                "SELECT COUNT(*) FROM readings"
                " WHERE addr = 2 AND temp_3 IS NOT NULL"
            ).fetchone()[0]
            assert non_null == 0
            # Slave 3 has 2 channels: temp_2 and temp_3 always NULL
            non_null = conn.execute(
                "SELECT COUNT(*) FROM readings"
                " WHERE addr = 3 AND temp_2 IS NOT NULL"
            ).fetchone()[0]
            assert non_null == 0
            conn.close()
        finally:
            os.unlink(path)

    def test_reproducible_with_seed(self):
        """Same seed produces identical data."""
        # Freeze time so both generate() calls use the same "now",
        # avoiding timestamp drift on slow machines (e.g. the Pi).
        frozen_epoch = 1750000000
        paths = []
        try:
            for _ in range(2):
                fd, path = tempfile.mkstemp(suffix=".db")
                os.close(fd)
                with patch("generate_data.time.time", return_value=float(frozen_epoch)):
                    generate(path, 1, 99)
                paths.append(path)
            conn1 = sqlite3.connect(paths[0])
            conn2 = sqlite3.connect(paths[1])
            rows1 = conn1.execute(
                "SELECT ts, addr, temp_0, temp_1, temp_2, temp_3"
                " FROM readings ORDER BY id"
            ).fetchall()
            rows2 = conn2.execute(
                "SELECT ts, addr, temp_0, temp_1, temp_2, temp_3"
                " FROM readings ORDER BY id"
            ).fetchall()
            assert rows1 == rows2
            conn1.close()
            conn2.close()
        finally:
            for p in paths:
                os.unlink(p)
