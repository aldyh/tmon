"""SQLite storage for temperature readings.

Persists poll data according to the readings schema (embedded below).
One row per successful REPLY frame, storing raw int16 temperatures
(tenths of a degree Celsius).  Timestamps are stored as Unix epoch
integers (seconds since 1970-01-01 00:00:00 UTC).

Example:
    >>> from tmon.storage import Storage
    >>> with Storage(":memory:") as store:
    ...     store.insert(1, [235, 198, None, None])
    ...     rows = store.fetch(1)
    ...     rows[0]["addr"]
    1
"""

import sqlite3
import time
from pathlib import Path


_NUM_CHANNELS = 4

SCHEMA = """\
CREATE TABLE IF NOT EXISTS readings (
    id        INTEGER PRIMARY KEY,
    ts        INTEGER NOT NULL,  -- Unix timestamp (seconds since epoch, UTC)
    addr      INTEGER NOT NULL,  -- slave address (1-247)
    temp_0    INTEGER,           -- channel 0, tenths of deg C
    temp_1    INTEGER,           -- channel 1, tenths of deg C
    temp_2    INTEGER,           -- channel 2, tenths of deg C
    temp_3    INTEGER            -- channel 3, tenths of deg C
);
CREATE INDEX IF NOT EXISTS idx_readings_addr_ts ON readings (addr, ts);
"""

_INSERT = """\
INSERT INTO readings (ts, addr, temp_0, temp_1, temp_2, temp_3)
VALUES (?, ?, ?, ?, ?, ?)"""

_FETCH_RECENT = """\
SELECT id, ts, addr, temp_0, temp_1, temp_2, temp_3
FROM readings ORDER BY id DESC LIMIT ?"""


class Storage:
    """SQLite-backed storage for temperature readings.

    Opens (or creates) the database at *db_path*, creates the
    ``readings`` table if absent, and enables WAL journaling for
    concurrent-read safety.

    Args:
        db_path: Path to the SQLite database file, or ``":memory:"``.

    Example:
        >>> with Storage(":memory:") as store:
        ...     store.insert(2, [100, 200, 300, 400])
        ...     store.fetch(1)[0]["addr"]
        2
    """

    def __init__(self, db_path: str):
        """Open the database and ensure the schema exists."""
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def insert(self, addr: int, temps: list[int | None]) -> None:
        """Insert one reading row: *addr* + 4-element *temps* list.

        Does not commit; call ``commit()`` after a batch of inserts.

        Raises:
            ValueError: If *temps* does not contain exactly 4 elements.

        Example:
            >>> store = Storage(":memory:")
            >>> store.insert(1, [235, 198, None, None])
            >>> store.commit()
        """
        if len(temps) != _NUM_CHANNELS:
            raise ValueError(
                "temps must have %d elements, got %d"
                % (_NUM_CHANNELS, len(temps))
            )
        ts = int(time.time())
        self._conn.execute(_INSERT, (ts, addr) + tuple(temps))

    def fetch(self, count: int) -> list[dict]:
        """Return the newest *count* readings, newest first.

        Example:
            >>> store = Storage(":memory:")
            >>> store.insert(1, [200, None, None, None])
            >>> store.commit()
            >>> rows = store.fetch(10)
            >>> len(rows)
            1
        """
        cursor = self._conn.execute(_FETCH_RECENT, (count,))
        return [dict(row) for row in cursor.fetchall()]

    def commit(self) -> None:
        """Commit the current transaction."""
        self._conn.commit()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
