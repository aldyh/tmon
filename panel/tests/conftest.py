"""Shared fixtures for panel tests."""

import os
import sqlite3
import tempfile

import pytest


_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS readings (
    id        INTEGER PRIMARY KEY,
    ts        TEXT    NOT NULL,
    addr      INTEGER NOT NULL,
    temp_0    INTEGER,
    temp_1    INTEGER,
    temp_2    INTEGER,
    temp_3    INTEGER
)"""


@pytest.fixture()
def empty_db():
    """Yield a path to a temporary empty database with the readings table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute(_CREATE_TABLE)
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
    conn.execute(_CREATE_TABLE)
    rows = [
        ("2024-06-01T12:00:00Z", 1, 220, 230, 240, None),
        ("2024-06-01T12:00:30Z", 1, 221, 231, 241, None),
        ("2024-06-01T12:00:00Z", 2, 180, 190, None, None),
        ("2024-06-01T12:00:30Z", 2, 181, 191, None, None),
        ("2024-06-01T12:01:00Z", 1, 222, 232, 242, None),
        ("2024-06-01T12:01:00Z", 2, 182, 192, None, None),
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
