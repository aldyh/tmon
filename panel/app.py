"""Flask application for the tmon demo dashboard.

Serves a single-page dashboard and a JSON API for temperature data.
Time windows are computed relative to the newest row in the database,
so data always feels "live" regardless of when it was generated.

Internally, timestamps are stored as Unix epoch integers.  The API
converts them to ISO-8601 strings for JSON responses and CSV export.

Example:
    $ flask --app app run
    # Then open http://localhost:5000 in a browser.
"""

import csv
import io
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, g, jsonify, render_template, request
from tmon.paths import find_db


def _ts_to_iso(ts: int) -> str:
    """Convert Unix timestamp to ISO-8601 UTC string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

_DB_PATH = os.environ.get("TMON_DB") or find_db("tmon.db")


def create_app(db_path: str) -> Flask:
    """Create and configure the Flask application.

    Args:
        db_path: Path to the SQLite database file.

    Example:
        >>> app = create_app(":memory:")
        >>> app.name
        'app'
    """
    app = Flask(__name__)
    app.config["TMON_DB"] = db_path

    def _get_db() -> sqlite3.Connection:
        """Return a per-request database connection."""
        if "db" not in g:
            g.db = sqlite3.connect(app.config["TMON_DB"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def _close_db(exc: BaseException | None) -> None:
        """Close the database connection at end of request."""
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def index() -> str:
        """Serve the dashboard HTML page."""
        return render_template("index.html")

    @app.route("/api/current")
    def api_current() -> tuple:
        """Return the latest reading per sensor.

        Response JSON:
            [{"addr": 1, "ts": "2024-01-01T00:00:00Z", "temp_0": 220, ...}, ...]
        """
        db = _get_db()
        max_ts = db.execute(
            "SELECT MAX(ts) FROM readings"
        ).fetchone()[0]
        if max_ts is None:
            return jsonify([]), 200
        rows = db.execute(
            "SELECT addr, ts, temp_0, temp_1, temp_2, temp_3"
            " FROM readings WHERE ts = ("
            "   SELECT MAX(ts) FROM readings AS r2"
            "   WHERE r2.addr = readings.addr"
            " ) GROUP BY addr ORDER BY addr"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["ts"] = _ts_to_iso(d["ts"])
            result.append(d)
        return jsonify(result), 200

    @app.route("/api/history")
    def api_history() -> tuple:
        """Return historical readings for one sensor, downsampled.

        Query parameters:
            addr: Sensor address (required, integer).
            hours: Time window in hours (default 24).
            points: Maximum points to return (default 500).

        Response JSON:
            [{"ts": "2024-01-01T00:00:00Z", "temp_0": 220, ...}, ...]
        """
        addr = request.args.get("addr", type=int)
        if addr is None:
            return jsonify({"error": "addr parameter required"}), 400
        hours = request.args.get("hours", type=float)
        if hours is None:
            return jsonify({"error": "hours parameter required"}), 400
        if hours <= 0:
            return jsonify({"error": "hours must be positive"}), 400
        points = request.args.get("points", 500, type=int)
        if points <= 0:
            return jsonify({"error": "points must be positive"}), 400

        db = _get_db()

        # Compute the time window relative to the newest row
        max_ts = db.execute(
            "SELECT MAX(ts) FROM readings WHERE addr = ?", (addr,)
        ).fetchone()[0]
        if max_ts is None:
            return jsonify([]), 200

        start_ts = max_ts - int(hours * 3600)

        rows = db.execute(
            "SELECT ts, temp_0, temp_1, temp_2, temp_3"
            " FROM readings"
            " WHERE addr = ? AND ts >= ? AND ts <= ?"
            " ORDER BY ts",
            (addr, start_ts, max_ts),
        ).fetchall()

        # Downsample by stepping through evenly
        sampled = _downsample(rows, points)
        result = []
        for r in sampled:
            d = dict(r)
            d["ts"] = _ts_to_iso(d["ts"])
            result.append(d)
        return jsonify(result), 200

    @app.route("/api/sensors")
    def api_sensors() -> tuple:
        """Return a list of distinct sensor addresses.

        Response JSON:
            [1, 2, 3]
        """
        db = _get_db()
        rows = db.execute(
            "SELECT DISTINCT addr FROM readings ORDER BY addr"
        ).fetchall()
        return jsonify([r["addr"] for r in rows]), 200

    @app.route("/api/export")
    def api_export() -> Response:
        """Export readings for one node as CSV over a trailing time window.

        The window is computed relative to the newest reading for the
        given node, exactly like ``/api/history``.

        Query parameters:
            addr: Node address (required, integer).
            hours: Time window in hours (required, positive float).

        Returns a CSV download with columns ts, temp_0 .. temp_3.
        Timestamps are exported as ISO-8601 strings.

        Example:
            GET /api/export?addr=1&hours=24
        """
        addr = request.args.get("addr", type=int)
        if addr is None:
            return jsonify({"error": "addr parameter required"}), 400
        hours = request.args.get("hours", type=float)
        if hours is None:
            return jsonify({"error": "hours parameter required"}), 400
        if hours <= 0:
            return jsonify({"error": "hours must be positive"}), 400

        db = _get_db()

        max_ts = db.execute(
            "SELECT MAX(ts) FROM readings WHERE addr = ?", (addr,)
        ).fetchone()[0]
        if max_ts is None:
            buf = io.StringIO()
            csv.writer(buf).writerow(
                ["ts", "temp_0", "temp_1", "temp_2", "temp_3"]
            )
            return Response(buf.getvalue(), mimetype="text/csv")

        start_ts = max_ts - int(hours * 3600)

        rows = db.execute(
            "SELECT ts, temp_0, temp_1, temp_2, temp_3"
            " FROM readings"
            " WHERE addr = ? AND ts >= ? AND ts <= ?"
            " ORDER BY ts",
            (addr, start_ts, max_ts),
        ).fetchall()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ts", "temp_0", "temp_1", "temp_2", "temp_3"])
        for row in rows:
            writer.writerow([
                _ts_to_iso(row["ts"]),
                row["temp_0"] if row["temp_0"] is not None else "",
                row["temp_1"] if row["temp_1"] is not None else "",
                row["temp_2"] if row["temp_2"] is not None else "",
                row["temp_3"] if row["temp_3"] is not None else "",
            ])

        start_iso = _ts_to_iso(start_ts).replace(":", "-")
        end_iso = _ts_to_iso(max_ts).replace(":", "-")
        filename = "tmon_node{}_{}_{}.csv".format(addr, start_iso, end_iso)
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="{}"'.format(
                    filename
                )
            },
        )

    @app.route("/api/range")
    def api_range() -> tuple:
        """Return the min and max timestamps in the database.

        Response JSON:
            {"min": "2024-01-01T00:00:00Z", "max": "2024-12-31T23:59:30Z"}
        """
        db = _get_db()
        row = db.execute(
            "SELECT MIN(ts) as min_ts, MAX(ts) as max_ts FROM readings"
        ).fetchone()
        if row["min_ts"] is None:
            return jsonify({"min": None, "max": None}), 200
        return jsonify({
            "min": _ts_to_iso(row["min_ts"]),
            "max": _ts_to_iso(row["max_ts"]),
        }), 200

    return app


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


# Default app instance for `flask --app app run`
app = create_app(_DB_PATH)
