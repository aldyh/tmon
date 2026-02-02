"""SQLite storage for temperature readings.

Persists poll data according to the schema in docs/storage.org.
One row per successful REPLY frame, storing raw int16 temperatures
(tenths of a degree Celsius).

Example:
    >>> from tmon.storage import Storage
    >>> store = Storage(":memory:")
    >>> store.insert(1, [235, 198, None, None])
    >>> rows = store.fetch(1)
    >>> rows[0]["addr"]
    1
    >>> store.close()
"""

import sqlite3
from datetime import datetime, timezone


_NUM_CHANNELS = 4

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
        >>> store = Storage(":memory:")
        >>> store.insert(2, [100, 200, 300, 400])
        >>> store.fetch(1)[0]["addr"]
        2
        >>> store.close()
    """

    def __init__(self, db_path):
        """Open the database and ensure the schema exists.

        Args:
            db_path: Filesystem path to the SQLite database, or
                ``":memory:"`` for an in-memory database.
        """
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def insert(self, addr, temps):
        """Insert one reading row: *addr* + 4-element *temps* list.

        Args:
            addr: Slave address (int, 1-247).
            temps: List of 4 int temperatures (tenths of deg C), or
                None for invalid channels.

        Raises:
            ValueError: If *temps* does not contain exactly 4 elements.

        Example:
            >>> store = Storage(":memory:")
            >>> store.insert(1, [235, 198, None, None])
        """
        if len(temps) != _NUM_CHANNELS:
            raise ValueError(
                "temps must have %d elements, got %d"
                % (_NUM_CHANNELS, len(temps))
            )
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._conn.execute(_INSERT, (ts, addr) + tuple(temps))
        self._conn.commit()

    def fetch(self, count):
        """Return the newest *count* readings, newest first.

        Args:
            count: Maximum number of rows to return (int).

        Returns:
            list[dict]: Each dict has keys ``id``, ``ts``, ``addr``,
                ``temp_0`` ... ``temp_3``.

        Example:
            >>> store = Storage(":memory:")
            >>> store.insert(1, [200, None, None, None])
            >>> rows = store.fetch(10)
            >>> len(rows)
            1
        """
        cursor = self._conn.execute(_FETCH_RECENT, (count,))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close the database connection."""
        self._conn.close()
