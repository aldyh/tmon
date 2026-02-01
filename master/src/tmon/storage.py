"""SQLite storage for temperature readings.

Persists poll data according to the schema in docs/storage.md.

Example:
    >>> from tmon.storage import Storage
    >>> store = Storage(db_path="readings.db")
    >>> store.insert_reading(slave_addr=1, sensor=0, temp_c=23.5)
"""


class Storage:
    """SQLite-backed storage for temperature readings.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path):
        """Initialize storage and ensure schema exists.

        Args:
            db_path: Filesystem path to the SQLite database.
        """
        raise NotImplementedError

    def insert_reading(self, slave_addr, sensor, temp_c):
        """Store a single temperature reading.

        Args:
            slave_addr: Slave address that produced the reading.
            sensor: Sensor index on the slave (0-3).
            temp_c: Temperature in degrees Celsius.
        """
        raise NotImplementedError
