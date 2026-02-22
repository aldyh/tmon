"""Tests for the static demo builder."""

import csv
import io
import json
import os
import sqlite3
import tempfile

import pytest

from build_demo import _transform_html, build


@pytest.fixture()
def demo_dir(sample_db):
    """Build a demo from sample_db and yield the output directory."""
    out = tempfile.mkdtemp()
    demo = os.path.join(out, "demo")
    build(sample_db, demo)
    yield demo


@pytest.fixture()
def empty_demo_dir(empty_db):
    """Build a demo from an empty database and yield the output directory."""
    out = tempfile.mkdtemp()
    demo = os.path.join(out, "demo")
    build(empty_db, demo)
    yield demo


class TestExpectedFiles:
    """All expected output files must exist."""

    def test_index_html(self, demo_dir):
        """index.html exists."""
        assert os.path.isfile(os.path.join(demo_dir, "index.html"))

    def test_style_css(self, demo_dir):
        """style.css exists."""
        assert os.path.isfile(os.path.join(demo_dir, "style.css"))

    def test_chart_js(self, demo_dir):
        """vendor/chart.umd.min.js exists."""
        assert os.path.isfile(
            os.path.join(demo_dir, "vendor", "chart.umd.min.js")
        )

    def test_api_json_files(self, demo_dir):
        """Top-level API JSON files exist."""
        for name in ("current.json", "sensors.json", "range.json"):
            path = os.path.join(demo_dir, "api", name)
            assert os.path.isfile(path), "{} missing".format(name)

    def test_history_json_files(self, demo_dir):
        """History JSON files exist for each node x range."""
        hours = [1, 6, 24, 168, 720, 8760]
        for addr in (1, 2):
            for h in hours:
                name = "{}_{}.json".format(addr, h)
                path = os.path.join(demo_dir, "api", "history", name)
                assert os.path.isfile(path), "{} missing".format(name)

    def test_export_csv_files(self, demo_dir):
        """Export CSV files exist for each node x range."""
        hours = [1, 6, 24, 168, 720, 8760]
        for addr in (1, 2):
            for h in hours:
                name = "{}_{}.csv".format(addr, h)
                path = os.path.join(demo_dir, "api", "export", name)
                assert os.path.isfile(path), "{} missing".format(name)


class TestJsonOutput:
    """JSON output matches the Flask endpoint responses."""

    def test_sensors(self, demo_dir):
        """sensors.json contains the correct addresses."""
        with open(os.path.join(demo_dir, "api", "sensors.json")) as f:
            data = json.load(f)
        assert data == [1, 2]

    def test_current(self, demo_dir):
        """current.json contains latest reading per client."""
        with open(os.path.join(demo_dir, "api", "current.json")) as f:
            data = json.load(f)
        addrs = sorted(r["addr"] for r in data)
        assert addrs == [1, 2]
        s1 = [r for r in data if r["addr"] == 1][0]
        assert s1["temp_0"] == 222

    def test_range(self, demo_dir):
        """range.json contains min and max timestamps."""
        with open(os.path.join(demo_dir, "api", "range.json")) as f:
            data = json.load(f)
        assert data["min"] == "2024-06-01T12:00:00Z"
        assert data["max"] == "2024-06-01T12:01:00Z"

    def test_history(self, demo_dir):
        """History JSON contains expected rows for node 1, 1 hour."""
        path = os.path.join(demo_dir, "api", "history", "1_1.json")
        with open(path) as f:
            data = json.load(f)
        assert len(data) == 3
        assert all("ts" in r for r in data)
        assert all("temp_0" in r for r in data)

    def test_history_null_handling(self, demo_dir):
        """Null temperature values are preserved as null in JSON."""
        path = os.path.join(demo_dir, "api", "history", "1_1.json")
        with open(path) as f:
            data = json.load(f)
        assert all(r["temp_3"] is None for r in data)


class TestCsvOutput:
    """CSV output matches the Flask export endpoint responses."""

    def test_export_header(self, demo_dir):
        """CSV files have the correct header row."""
        path = os.path.join(demo_dir, "api", "export", "1_1.csv")
        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["ts", "temp_0", "temp_1", "temp_2", "temp_3"]

    def test_export_row_count(self, demo_dir):
        """CSV for node 1, 1 hour has 3 data rows."""
        path = os.path.join(demo_dir, "api", "export", "1_1.csv")
        with open(path) as f:
            rows = list(csv.reader(f))
        assert len(rows) == 4  # header + 3 data rows

    def test_export_null_handling(self, demo_dir):
        """Null temps appear as empty strings in CSV."""
        path = os.path.join(demo_dir, "api", "export", "1_1.csv")
        with open(path) as f:
            rows = list(csv.reader(f))
        for row in rows[1:]:
            assert row[4] == ""  # temp_3 column for node 1

    def test_export_values(self, demo_dir):
        """CSV data values match the database content."""
        path = os.path.join(demo_dir, "api", "export", "1_1.csv")
        with open(path) as f:
            rows = list(csv.reader(f))
        # Last row should be the 12:01:00 reading
        last = rows[-1]
        assert last[0] == "2024-06-01T12:01:00Z"
        assert last[1] == "222"


class TestTransformHtml:
    """index.html transformations for static serving."""

    def test_relative_css_path(self, demo_dir):
        """CSS link uses relative path."""
        with open(os.path.join(demo_dir, "index.html")) as f:
            html = f.read()
        assert 'href="style.css"' in html
        assert 'href="/static/style.css"' not in html

    def test_relative_js_path(self, demo_dir):
        """Chart.js script uses relative path."""
        with open(os.path.join(demo_dir, "index.html")) as f:
            html = f.read()
        assert 'src="vendor/chart.umd.min.js"' in html
        assert 'src="/static/vendor/' not in html

    def test_api_current_rewritten(self, demo_dir):
        """fetch for /api/current points to api/current.json."""
        with open(os.path.join(demo_dir, "index.html")) as f:
            html = f.read()
        assert 'fetch("api/current.json")' in html
        assert 'fetch("/api/current")' not in html

    def test_api_sensors_rewritten(self, demo_dir):
        """fetch for /api/sensors points to api/sensors.json."""
        with open(os.path.join(demo_dir, "index.html")) as f:
            html = f.read()
        assert 'fetch("api/sensors.json")' in html
        assert 'fetch("/api/sensors")' not in html

    def test_api_history_rewritten(self, demo_dir):
        """fetch for /api/history points to static JSON files."""
        with open(os.path.join(demo_dir, "index.html")) as f:
            html = f.read()
        assert 'api/history/' in html
        assert '"/api/history?' not in html

    def test_api_export_rewritten(self, demo_dir):
        """window.open for /api/export points to static CSV files."""
        with open(os.path.join(demo_dir, "index.html")) as f:
            html = f.read()
        assert 'api/export/' in html
        assert '"/api/export?' not in html

    def test_no_polling(self, demo_dir):
        """setInterval for refreshCurrent is removed."""
        with open(os.path.join(demo_dir, "index.html")) as f:
            html = f.read()
        assert "setInterval" not in html


class TestEmptyDb:
    """Edge case: building from an empty database."""

    def test_sensors_empty(self, empty_demo_dir):
        """sensors.json is an empty list."""
        with open(os.path.join(empty_demo_dir, "api", "sensors.json")) as f:
            data = json.load(f)
        assert data == []

    def test_current_empty(self, empty_demo_dir):
        """current.json is an empty list."""
        with open(os.path.join(empty_demo_dir, "api", "current.json")) as f:
            data = json.load(f)
        assert data == []

    def test_range_nulls(self, empty_demo_dir):
        """range.json has null min and max."""
        with open(os.path.join(empty_demo_dir, "api", "range.json")) as f:
            data = json.load(f)
        assert data["min"] is None
        assert data["max"] is None

    def test_index_exists(self, empty_demo_dir):
        """index.html is still generated."""
        assert os.path.isfile(
            os.path.join(empty_demo_dir, "index.html")
        )
