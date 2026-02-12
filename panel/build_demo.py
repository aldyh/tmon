"""Build a static demo of the tmon dashboard.

Reads tmon_mock.db directly (no Flask dependency) and generates a
self-contained directory of HTML, CSS, JS, JSON, and CSV files that
can be served by any static HTTP server.

The output mirrors the Flask API structure with pre-rendered JSON
and CSV responses for every node/range combination.

Example:
    $ python build_demo.py --db tmon_mock.db --output demo
    $ cd demo && python -m http.server 8000
"""

import argparse
import csv
import io
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone


# Range options matching the <select> in index.html
_RANGE_HOURS = [1, 6, 24, 168, 720, 8760]


def _ts_to_iso(ts: int) -> str:
    """Convert Unix timestamp to ISO-8601 UTC string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

_MAX_POINTS = 500


def _downsample(rows: list, max_points: int) -> list:
    """Return at most *max_points* evenly spaced items from *rows*."""
    n = len(rows)
    if n <= max_points:
        return rows
    step = n / max_points
    result = []
    pos = 0.0
    while len(result) < max_points and int(pos) < n:
        result.append(rows[int(pos)])
        pos += step
    return result


def _query_sensors(conn: sqlite3.Connection) -> list:
    """Return sorted list of distinct sensor addresses."""
    rows = conn.execute(
        "SELECT DISTINCT addr FROM readings ORDER BY addr"
    ).fetchall()
    return [r[0] for r in rows]


def _query_current(conn: sqlite3.Connection) -> list:
    """Return the latest reading per sensor as a list of dicts."""
    rows = conn.execute(
        "SELECT addr, ts, temp_0, temp_1, temp_2, temp_3"
        " FROM readings WHERE ts = ("
        "   SELECT MAX(ts) FROM readings AS r2"
        "   WHERE r2.addr = readings.addr"
        " ) GROUP BY addr ORDER BY addr"
    ).fetchall()
    return [
        {
            "addr": r[0], "ts": _ts_to_iso(r[1]),
            "temp_0": r[2], "temp_1": r[3],
            "temp_2": r[4], "temp_3": r[5],
        }
        for r in rows
    ]


def _query_range(conn: sqlite3.Connection) -> dict:
    """Return min and max timestamps in the database."""
    row = conn.execute(
        "SELECT MIN(ts) AS min_ts, MAX(ts) AS max_ts FROM readings"
    ).fetchone()
    if row[0] is None:
        return {"min": None, "max": None}
    return {"min": _ts_to_iso(row[0]), "max": _ts_to_iso(row[1])}


def _query_history(conn: sqlite3.Connection, addr: int,
                   hours: float) -> list:
    """Return downsampled history for one node over a trailing window."""
    max_ts = conn.execute(
        "SELECT MAX(ts) FROM readings WHERE addr = ?", (addr,)
    ).fetchone()[0]
    if max_ts is None:
        return []

    start_ts = max_ts - int(hours * 3600)

    rows = conn.execute(
        "SELECT ts, temp_0, temp_1, temp_2, temp_3"
        " FROM readings"
        " WHERE addr = ? AND ts >= ? AND ts <= ?"
        " ORDER BY ts",
        (addr, start_ts, max_ts),
    ).fetchall()

    downsampled = _downsample(rows, _MAX_POINTS)
    return [
        {
            "ts": _ts_to_iso(r[0]), "temp_0": r[1], "temp_1": r[2],
            "temp_2": r[3], "temp_3": r[4],
        }
        for r in downsampled
    ]


def _query_export(conn: sqlite3.Connection, addr: int,
                  hours: float) -> str:
    """Return CSV text for one node over a trailing window."""
    max_ts = conn.execute(
        "SELECT MAX(ts) FROM readings WHERE addr = ?", (addr,)
    ).fetchone()[0]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ts", "temp_0", "temp_1", "temp_2", "temp_3"])

    if max_ts is None:
        return buf.getvalue()

    start_ts = max_ts - int(hours * 3600)

    rows = conn.execute(
        "SELECT ts, temp_0, temp_1, temp_2, temp_3"
        " FROM readings"
        " WHERE addr = ? AND ts >= ? AND ts <= ?"
        " ORDER BY ts",
        (addr, start_ts, max_ts),
    ).fetchall()

    for row in rows:
        writer.writerow([
            _ts_to_iso(row[0]),
            row[1] if row[1] is not None else "",
            row[2] if row[2] is not None else "",
            row[3] if row[3] is not None else "",
            row[4] if row[4] is not None else "",
        ])
    return buf.getvalue()


def _transform_html(html: str, sensors: list) -> str:
    """Rewrite index.html for static file serving.

    - Rewrites asset paths to be relative.
    - Rewrites API fetch URLs to point at static JSON/CSV files.
    - Removes the setInterval polling call.

    Args:
        html: Original index.html content.
        sensors: List of sensor address integers.

    Returns:
        Transformed HTML string.
    """
    # Static asset paths
    html = html.replace('href="/static/style.css"', 'href="style.css"')
    html = html.replace('src="/static/vendor/chart.umd.min.js"',
                        'src="vendor/chart.umd.min.js"')

    # API: /api/current -> api/current.json
    html = html.replace('fetch("/api/current")',
                        'fetch("api/current.json")')

    # API: /api/sensors -> api/sensors.json
    html = html.replace('fetch("/api/sensors")',
                        'fetch("api/sensors.json")')

    # API: /api/history?addr=...&hours=...&points=500 ->
    #       api/history/<addr>_<hours>.json
    html = html.replace(
        'fetch("/api/history?addr=" + addr + "&hours=" + hours + "&points=500")',
        'fetch("api/history/" + addr + "_" + hours + ".json")'
    )

    # API: /api/export?addr=...&hours=... ->
    #       api/export/<addr>_<hours>.csv
    html = html.replace(
        'window.open("/api/export?addr=" + addr + "&hours=" + hours)',
        'window.open("api/export/" + addr + "_" + hours + ".csv")'
    )

    # Remove setInterval polling line
    html = re.sub(
        r'\n\s*setInterval\(refreshCurrent,\s*REFRESH_MS\);\n',
        '\n',
        html,
    )

    return html


def build(db_path: str, output_dir: str) -> None:
    """Generate the static demo site.

    Args:
        db_path: Path to the SQLite database.
        output_dir: Directory to write output files into.

    Example:
        >>> import tempfile, os, sqlite3
        >>> db = os.path.join(tempfile.mkdtemp(), "t.db")
        >>> conn = sqlite3.connect(db)
        >>> _ = conn.execute(
        ...     "CREATE TABLE readings (id INTEGER PRIMARY KEY,"
        ...     " ts INTEGER, addr INTEGER,"
        ...     " temp_0 INTEGER, temp_1 INTEGER,"
        ...     " temp_2 INTEGER, temp_3 INTEGER)")
        >>> conn.commit(); conn.close()
        >>> out = os.path.join(tempfile.mkdtemp(), "demo")
        >>> build(db, out)
        >>> os.path.isfile(os.path.join(out, "index.html"))
        True
    """
    conn = sqlite3.connect(db_path)

    sensors = _query_sensors(conn)
    current = _query_current(conn)
    ts_range = _query_range(conn)

    # Create output directories
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    os.makedirs(os.path.join(output_dir, "vendor"))
    os.makedirs(os.path.join(output_dir, "api", "history"))
    os.makedirs(os.path.join(output_dir, "api", "export"))

    # Write JSON endpoints
    _write_json(os.path.join(output_dir, "api", "sensors.json"), sensors)
    _write_json(os.path.join(output_dir, "api", "current.json"), current)
    _write_json(os.path.join(output_dir, "api", "range.json"), ts_range)

    # Write history JSON and export CSV for each node x range
    for addr in sensors:
        for hours in _RANGE_HOURS:
            history = _query_history(conn, addr, hours)
            name = "{}_{}.json".format(addr, hours)
            _write_json(
                os.path.join(output_dir, "api", "history", name),
                history,
            )

            export_csv = _query_export(conn, addr, hours)
            csv_name = "{}_{}.csv".format(addr, hours)
            _write_text(
                os.path.join(output_dir, "api", "export", csv_name),
                export_csv,
            )

    conn.close()

    # Copy static assets
    panel_dir = os.path.dirname(os.path.abspath(__file__))
    shutil.copy2(
        os.path.join(panel_dir, "static", "style.css"),
        os.path.join(output_dir, "style.css"),
    )
    shutil.copy2(
        os.path.join(panel_dir, "static", "vendor", "chart.umd.min.js"),
        os.path.join(output_dir, "vendor", "chart.umd.min.js"),
    )

    # Transform and write index.html
    with open(os.path.join(panel_dir, "templates", "index.html")) as f:
        html = f.read()
    html = _transform_html(html, sensors)
    _write_text(os.path.join(output_dir, "index.html"), html)


def _write_json(path: str, data: object) -> None:
    """Write *data* as JSON to *path*."""
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))


def _write_text(path: str, text: str) -> None:
    """Write *text* to *path*."""
    with open(path, "w") as f:
        f.write(text)


def main() -> None:
    """Entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Build a static demo of the tmon dashboard"
    )
    parser.add_argument(
        "--db", required=True,
        help="path to the SQLite database"
    )
    parser.add_argument(
        "--output", required=True,
        help="output directory for the static site"
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        parser.error("database not found: {}".format(args.db))

    build(args.db, args.output)
    print("Static demo written to {}".format(args.output))


if __name__ == "__main__":
    main()
