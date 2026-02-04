"""Shared fixtures for panel tests."""

import os
import sqlite3
import tempfile

import pytest

from tmon.storage import SCHEMA


@pytest.fixture()
def empty_db():
    """Yield a path to a temporary empty database with the readings table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


@pytest.fixture()
def sample_db():
    """Yield a path to a database with a handful of test rows."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    # Unix timestamps for 2024-06-01 12:00:00Z, 12:00:30Z, 12:01:00Z
    ts_base = 1717243200  # 2024-06-01T12:00:00Z
    rows = [
        (ts_base, 1, 220, 230, 240, None),
        (ts_base + 30, 1, 221, 231, 241, None),
        (ts_base, 2, 180, 190, None, None),
        (ts_base + 30, 2, 181, 191, None, None),
        (ts_base + 60, 1, 222, 232, 242, None),
        (ts_base + 60, 2, 182, 192, None, None),
    ]
    conn.executemany(
        "INSERT INTO readings (ts, addr, temp_0, temp_1, temp_2, temp_3)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)
