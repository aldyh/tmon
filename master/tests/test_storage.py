"""Tests for tmon.storage."""

import re

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
        """insert + fetch round-trips data."""
        store = Storage(":memory:")
        store.insert(1, [235, 198, None, None])
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
        rows = store.fetch(10)
        assert [r["temp_0"] for r in rows] == [300, 200, 100]
        store.close()

    def test_fetch_limit(self):
        """fetch honours the count limit."""
        store = Storage(":memory:")
        for i in range(5):
            store.insert(1, [i * 10, None, None, None])
        rows = store.fetch(2)
        assert len(rows) == 2
        store.close()

    def test_timestamp_format(self):
        """Timestamp is ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)."""
        store = Storage(":memory:")
        store.insert(1, [100, None, None, None])
        rows = store.fetch(1)
        ts = rows[0]["ts"]
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", ts)
        store.close()

    def test_negative_temps(self):
        """Negative temperatures are stored correctly."""
        store = Storage(":memory:")
        store.insert(1, [-100, None, None, None])
        rows = store.fetch(1)
        assert rows[0]["temp_0"] == -100
        store.close()

    def test_multiple_slaves(self):
        """Readings from different slaves coexist."""
        store = Storage(":memory:")
        store.insert(1, [100, None, None, None])
        store.insert(2, [200, None, None, None])
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
