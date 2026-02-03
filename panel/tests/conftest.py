"""Shared fixtures for panel tests."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "readings.sql"


def _load_schema() -> str:
    """Read the CREATE TABLE statement from schema/readings.sql."""
    return _SCHEMA_PATH.read_text()


@pytest.fixture()
def empty_db():
    """Yield a path to a temporary empty database with the readings table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(_load_schema())
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
    conn.executescript(_load_schema())
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
