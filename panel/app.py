"""Flask application for the tmon mock visualization panel.

Serves a single-page dashboard and a JSON API for temperature data.
Time windows are computed relative to the newest row in the database,
so mock data always feels "live" regardless of when it was generated.

Example:
    $ flask --app app run
    # Then open http://localhost:5000 in a browser.
"""

import csv
import io
import os
import sqlite3

from flask import Flask, Response, g, jsonify, render_template, request

_DB_PATH = os.environ.get("TMON_DB", "tmon_mock.db")


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
        """Return the latest reading per slave.

        Response JSON:
            [{"addr": 1, "ts": "...", "temp_0": 220, ...}, ...]
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
        return jsonify([dict(r) for r in rows]), 200

    @app.route("/api/history")
    def api_history() -> tuple:
        """Return historical readings for one slave, downsampled.

        Query parameters:
            addr: Slave address (required, integer).
            hours: Time window in hours (default 24).
            points: Maximum points to return (default 500).

        Response JSON:
            [{"ts": "...", "temp_0": 220, ...}, ...]
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

        from datetime import datetime, timedelta, timezone
        end = datetime.strptime(max_ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        start = end - timedelta(hours=hours)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")

        rows = db.execute(
            "SELECT ts, temp_0, temp_1, temp_2, temp_3"
            " FROM readings"
            " WHERE addr = ? AND ts >= ? AND ts <= ?"
            " ORDER BY ts",
            (addr, start_str, max_ts),
        ).fetchall()

        # Downsample by stepping through evenly
        result = _downsample(rows, points)
        return jsonify([dict(r) for r in result]), 200

    @app.route("/api/slaves")
    def api_slaves() -> tuple:
        """Return a list of distinct slave addresses.

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
        """Export readings for one node and date range as CSV.

        Query parameters:
            addr: Node address (required, integer).
            start: Start timestamp, ISO-8601 (required).
            end: End timestamp, ISO-8601 (required).

        Returns a CSV download with columns ts, temp_0 .. temp_3.

        Example:
            GET /api/export?addr=1&start=2024-06-01T12:00:00Z&end=2024-06-01T13:00:00Z
        """
        addr = request.args.get("addr", type=int)
        if addr is None:
            return jsonify({"error": "addr parameter required"}), 400
        start = request.args.get("start", type=str)
        if start is None:
            return jsonify({"error": "start parameter required"}), 400
        end = request.args.get("end", type=str)
        if end is None:
            return jsonify({"error": "end parameter required"}), 400

        db = _get_db()
        rows = db.execute(
            "SELECT ts, temp_0, temp_1, temp_2, temp_3"
            " FROM readings"
            " WHERE addr = ? AND ts >= ? AND ts <= ?"
            " ORDER BY ts",
            (addr, start, end),
        ).fetchall()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ts", "temp_0", "temp_1", "temp_2", "temp_3"])
        for row in rows:
            writer.writerow([
                row["ts"],
                row["temp_0"] if row["temp_0"] is not None else "",
                row["temp_1"] if row["temp_1"] is not None else "",
                row["temp_2"] if row["temp_2"] is not None else "",
                row["temp_3"] if row["temp_3"] is not None else "",
            ])

        safe_start = start.replace(":", "-")
        safe_end = end.replace(":", "-")
        filename = "tmon_node{}_{}_{}.csv".format(addr, safe_start, safe_end)
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
        return jsonify({"min": row["min_ts"], "max": row["max_ts"]}), 200

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
