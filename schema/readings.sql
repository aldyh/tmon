-- Schema for the readings table.
-- See docs/storage.org for documentation.

CREATE TABLE IF NOT EXISTS readings (
    id        INTEGER PRIMARY KEY,
    ts        TEXT    NOT NULL,  -- ISO-8601 UTC timestamp
    addr      INTEGER NOT NULL,  -- slave address (1-247)
    temp_0    INTEGER,           -- channel 0, tenths of deg C
    temp_1    INTEGER,           -- channel 1, tenths of deg C
    temp_2    INTEGER,           -- channel 2, tenths of deg C
    temp_3    INTEGER            -- channel 3, tenths of deg C
);
