# Storage specification

SQLite database for persisting temperature readings collected by the
master poller.

- **Database file:** `tmon.db` (configurable in `config.toml`).
- **Engine:** SQLite 3
- **Write pattern:** one INSERT per successful poll reply.
- **No deletes or updates** during normal operation.

## Schema

### `readings` table

Stores one row per successful REPLY frame received from a slave.

```sql
CREATE TABLE readings (
    id        INTEGER PRIMARY KEY,
    ts        TEXT    NOT NULL,  -- ISO-8601 UTC timestamp
    addr      INTEGER NOT NULL,  -- slave address (1-247)
    status    INTEGER NOT NULL,  -- channel validity bitmask
    temp_0    INTEGER,           -- channel 0, tenths of deg C
    temp_1    INTEGER,           -- channel 1, tenths of deg C
    temp_2    INTEGER,           -- channel 2, tenths of deg C
    temp_3    INTEGER            -- channel 3, tenths of deg C
);
```

### Column details

| Column | Type    | Description                                                                         |
|--------|---------|-------------------------------------------------------------------------------------|
| id     | INTEGER | Auto-incrementing primary key.                                                      |
| ts     | TEXT    | UTC timestamp in ISO-8601 format (`YYYY-MM-DDTHH:MM:SSZ`).                          |
| addr   | INTEGER | Slave address from the REPLY frame (1-247).                                         |
| status | INTEGER | Bitmask from the REPLY payload. Bit N set = channel N valid.                        |
| temp_0 | INTEGER | Channel 0 reading in tenths of a degree Celsius, or NULL if the channel is invalid. |
| temp_1 | INTEGER | Channel 1 reading, same encoding as temp_0.                                         |
| temp_2 | INTEGER | Channel 2 reading, same encoding as temp_0.                                         |
| temp_3 | INTEGER | Channel 3 reading, same encoding as temp_0.                                         |
