"""Tests for tmon.storage."""

import re
import time

import pytest

from tmon.storage import Storage


class TestStorage:
    """Tests for the Storage class."""

    def test_create_table(self):
        """Opening Storage creates the readings table."""
        store = Storage(":memory:")
        cursor = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert "readings" in tables
        store.close()

    def test_insert_and_fetch(self):
        """insert + commit + fetch round-trips data."""
        store = Storage(":memory:")
        store.insert(1, [235, 198, None, None])
        store.commit()
        rows = store.fetch(10)
        assert len(rows) == 1
        row = rows[0]
        assert row["addr"] == 1
        assert row["temp_0"] == 235
        assert row["temp_1"] == 198
        assert row["temp_2"] is None
        assert row["temp_3"] is None
        store.close()

    def test_null_temps(self):
        """All four temps can be None."""
        store = Storage(":memory:")
        store.insert(5, [None, None, None, None])
        store.commit()
        rows = store.fetch(1)
        assert rows[0]["temp_0"] is None
        assert rows[0]["temp_1"] is None
        assert rows[0]["temp_2"] is None
        assert rows[0]["temp_3"] is None
        store.close()

    def test_all_temps_present(self):
        """All four temps can be non-None."""
        store = Storage(":memory:")
        store.insert(2, [100, 200, 300, 400])
        store.commit()
        rows = store.fetch(1)
        row = rows[0]
        assert row["temp_0"] == 100
        assert row["temp_1"] == 200
        assert row["temp_2"] == 300
        assert row["temp_3"] == 400
        store.close()

    def test_ordering_newest_first(self):
        """fetch returns newest rows first."""
        store = Storage(":memory:")
        store.insert(1, [100, None, None, None])
        store.insert(1, [200, None, None, None])
        store.insert(1, [300, None, None, None])
        store.commit()
        rows = store.fetch(10)
        assert [r["temp_0"] for r in rows] == [300, 200, 100]
        store.close()

    def test_fetch_limit(self):
        """fetch honours the count limit."""
        store = Storage(":memory:")
        for i in range(5):
            store.insert(1, [i * 10, None, None, None])
        store.commit()
        rows = store.fetch(2)
        assert len(rows) == 2
        store.close()

    def test_timestamp_format(self):
        """Timestamp is a Unix epoch integer."""
        store = Storage(":memory:")
        store.insert(1, [100, None, None, None])
        store.commit()
        rows = store.fetch(1)
        ts = rows[0]["ts"]
        assert isinstance(ts, int)
        assert ts > 0
        store.close()

    def test_negative_temps(self):
        """Negative temperatures are stored correctly."""
        store = Storage(":memory:")
        store.insert(1, [-100, None, None, None])
        store.commit()
        rows = store.fetch(1)
        assert rows[0]["temp_0"] == -100
        store.close()

    def test_multiple_sensors(self):
        """Readings from different sensors coexist."""
        store = Storage(":memory:")
        store.insert(1, [100, None, None, None])
        store.insert(2, [200, None, None, None])
        store.commit()
        rows = store.fetch(10)
        addrs = {r["addr"] for r in rows}
        assert addrs == {1, 2}
        store.close()

    def test_wrong_temps_length(self):
        """insert rejects temps with wrong length."""
        store = Storage(":memory:")
        with pytest.raises(ValueError):
            store.insert(1, [100, 200])
        with pytest.raises(ValueError):
            store.insert(1, [100, 200, 300, 400, 500])
        store.close()


class TestStorageContextManager:
    """Tests for Storage context manager protocol."""

    def test_with_block_closes_connection(self):
        """Exiting a with block closes the database connection."""
        with Storage(":memory:") as store:
            store.insert(1, [100, 200, 300, 400])
            store.commit()
            rows = store.fetch(1)
            assert rows[0]["addr"] == 1
        # Connection is closed after the with block
        with pytest.raises(Exception):
            store.fetch(1)

    def test_enter_returns_self(self):
        """__enter__ returns the Storage instance."""
        store = Storage(":memory:")
        assert store.__enter__() is store
        store.close()


class TestPurge:
    """Tests for Storage.purge."""

    def _insert_at(self, store, ts: int, addr: int) -> None:
        """Insert a reading with a specific timestamp."""
        store._conn.execute(
            "INSERT INTO readings (ts, addr, temp_0) VALUES (?, ?, ?)",
            (ts, addr, 200),
        )
        store._conn.commit()

    def test_purge_deletes_old_rows(self):
        """purge removes rows older than the given number of days."""
        store = Storage(":memory:")
        now = int(time.time())
        self._insert_at(store, now - 400 * 86400, 1)  # 400 days ago
        self._insert_at(store, now - 10 * 86400, 1)   # 10 days ago
        deleted = store.purge(365)
        assert deleted == 1
        rows = store.fetch(10)
        assert len(rows) == 1
        store.close()

    def test_purge_keeps_recent_rows(self):
        """purge does not delete rows within the retention period."""
        store = Storage(":memory:")
        now = int(time.time())
        self._insert_at(store, now - 100 * 86400, 1)
        self._insert_at(store, now - 200 * 86400, 2)
        deleted = store.purge(365)
        assert deleted == 0
        rows = store.fetch(10)
        assert len(rows) == 2
        store.close()

    def test_purge_returns_zero_on_empty_db(self):
        """purge on an empty database returns 0."""
        store = Storage(":memory:")
        deleted = store.purge(365)
        assert deleted == 0
        store.close()

    def test_purge_deletes_all_old(self):
        """purge removes multiple old rows at once."""
        store = Storage(":memory:")
        now = int(time.time())
        for i in range(5):
            self._insert_at(store, now - (400 + i) * 86400, 1)
        self._insert_at(store, now, 1)  # recent
        deleted = store.purge(365)
        assert deleted == 5
        rows = store.fetch(10)
        assert len(rows) == 1
        store.close()
