"""Generate mock temperature data for the demo dashboard.

Creates tmon_mock.db with the readings table schema from tmon.storage.
Populates it with 1 year of readings for 3 clients at 30-second intervals.

Temperature profiles use sinusoidal daily and seasonal cycles plus
Gaussian noise to look realistic.  One channel on client 3 has
occasional NULL readings to exercise null handling.
"""

import argparse
import math
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from tmon.storage import SCHEMA

# (addr, num_channels, base_temp_tenths, amplitude_tenths)
_SENSORS = [
    (1, 4, 220, 50),   # indoor sensor: ~22C +/- 5C
    (2, 3, 180, 80),   # outdoor sensor: ~18C +/- 8C
    (3, 2, 350, 30),   # hot-water pipe: ~35C +/- 3C
]

_SECONDS_PER_DAY = 86400
_INTERVAL = 30  # seconds between readings


def _temperature(base: int, amplitude: int, day_frac: float,
                 year_frac: float, noise_std: int) -> int:
    """Compute a synthetic temperature value in tenths of deg C."""
    daily = amplitude * math.sin(2 * math.pi * (day_frac - 0.25))
    seasonal = (amplitude * 0.6) * math.sin(
        2 * math.pi * (year_frac - 0.25)
    )
    noise = random.gauss(0, noise_std)
    return int(base + daily + seasonal + noise)


def generate(db_path: str, days: int, seed: int) -> int:
    """Populate *db_path* with mock readings.

    Returns the total number of rows inserted.

    Args:
        db_path: Path to the SQLite database file.
        days: Number of days of data to generate.
        seed: Random seed for reproducibility.
    """
    random.seed(seed)

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.executescript(SCHEMA)

    total_seconds = days * _SECONDS_PER_DAY
    total_steps = total_seconds // _INTERVAL

    # End at the current time so the mock data feels recent.
    now_epoch = int(time.time())
    now = datetime.fromtimestamp(now_epoch, tz=timezone.utc)
    start = now - timedelta(days=days)

    rows = []
    batch_size = 10000
    count = 0

    start_epoch = int(start.timestamp())

    for step in range(total_steps):
        ts_epoch = start_epoch + step * _INTERVAL
        ts = start + timedelta(seconds=step * _INTERVAL)
        day_frac = (ts.hour * 3600 + ts.minute * 60 + ts.second) / _SECONDS_PER_DAY
        year_frac = ts.timetuple().tm_yday / 365.0

        for addr, num_channels, base, amplitude in _SENSORS:
            temps = []
            for ch in range(4):
                if ch >= num_channels:
                    temps.append(None)
                elif addr == 3 and ch == 1 and random.random() < 0.05:
                    # 5% null rate on client 3, channel 1
                    temps.append(None)
                else:
                    # Each channel gets a slight offset
                    ch_offset = ch * 15
                    t = _temperature(base + ch_offset, amplitude,
                                     day_frac, year_frac, 5)
                    temps.append(t)
            rows.append((ts_epoch, addr, temps[0], temps[1],
                         temps[2], temps[3]))
            count += 1

            if len(rows) >= batch_size:
                conn.executemany(
                    "INSERT INTO readings (ts, addr, temp_0, temp_1,"
                    " temp_2, temp_3) VALUES (?, ?, ?, ?, ?, ?)",
                    rows,
                )
                rows.clear()

    if rows:
        conn.executemany(
            "INSERT INTO readings (ts, addr, temp_0, temp_1,"
            " temp_2, temp_3) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )

    conn.commit()
    conn.close()
    return count


def main() -> None:
    """Entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Generate mock temperature data"
    )
    parser.add_argument("--db", default="tmon_mock.db",
                        help="output database path")
    parser.add_argument("--days", type=int, default=365,
                        help="days of data to generate")
    parser.add_argument("--seed", type=int, default=42,
                        help="random seed")
    args = parser.parse_args()

    print("Generating %d days of mock data..." % args.days)
    n = generate(args.db, args.days, args.seed)
    print("Wrote %d rows to %s" % (n, args.db))


if __name__ == "__main__":
    main()
