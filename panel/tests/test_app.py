"""Tests for the Flask API endpoints."""

import json
import sqlite3

import pytest

from app import create_app


@pytest.fixture()
def client(sample_db):
    """Yield a Flask test client backed by the sample database."""
    app = create_app(sample_db)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def empty_client(empty_db):
    """Yield a Flask test client backed by an empty database."""
    app = create_app(empty_db)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestIndex:
    """Dashboard page."""

    def test_serves_html(self, client):
        """GET / returns 200 with HTML content."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"<!DOCTYPE html>" in resp.data


class TestApiCurrent:
    """GET /api/current endpoint."""

    def test_returns_latest_per_slave(self, client):
        """Each slave appears once with its most recent reading."""
        resp = client.get("/api/current")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        addrs = [r["addr"] for r in data]
        assert sorted(addrs) == [1, 2]
        # Latest for slave 1 is the 12:01:00 row
        s1 = [r for r in data if r["addr"] == 1][0]
        assert s1["temp_0"] == 222

    def test_empty_db(self, empty_client):
        """Empty database returns an empty list."""
        resp = empty_client.get("/api/current")
        assert resp.status_code == 200
        assert json.loads(resp.data) == []


class TestApiHistory:
    """GET /api/history endpoint."""

    def test_requires_addr(self, client):
        """Missing addr returns 400."""
        resp = client.get("/api/history?hours=1")
        assert resp.status_code == 400

    def test_requires_hours(self, client):
        """Missing hours returns 400."""
        resp = client.get("/api/history?addr=1")
        assert resp.status_code == 400

    def test_returns_history(self, client):
        """Returns readings for the specified slave within the time window."""
        resp = client.get("/api/history?addr=1&hours=1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 3  # 3 rows for slave 1

    def test_empty_for_unknown_slave(self, client):
        """Unknown slave address returns empty list."""
        resp = client.get("/api/history?addr=99&hours=24")
        assert resp.status_code == 200
        assert json.loads(resp.data) == []

    def test_invalid_hours(self, client):
        """Non-positive hours returns 400."""
        resp = client.get("/api/history?addr=1&hours=-1")
        assert resp.status_code == 400

    def test_invalid_points(self, client):
        """Non-positive points returns 400."""
        resp = client.get("/api/history?addr=1&hours=1&points=0")
        assert resp.status_code == 400

    def test_downsampling(self, client):
        """Requesting fewer points than available triggers downsampling."""
        resp = client.get("/api/history?addr=1&hours=1&points=2")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 2

    def test_null_handling(self, client):
        """Null temperature values are preserved as null in JSON."""
        resp = client.get("/api/history?addr=1&hours=1")
        data = json.loads(resp.data)
        # Slave 1 has temp_3 = None
        assert all(r["temp_3"] is None for r in data)

    def test_empty_db_history(self, empty_client):
        """Empty database returns empty list for any query."""
        resp = empty_client.get("/api/history?addr=1&hours=24")
        assert resp.status_code == 200
        assert json.loads(resp.data) == []


class TestApiSlaves:
    """GET /api/slaves endpoint."""

    def test_returns_slave_list(self, client):
        """Returns distinct slave addresses."""
        resp = client.get("/api/slaves")
        assert resp.status_code == 200
        assert json.loads(resp.data) == [1, 2]

    def test_empty_db(self, empty_client):
        """Empty database returns empty list."""
        resp = empty_client.get("/api/slaves")
        assert resp.status_code == 200
        assert json.loads(resp.data) == []


class TestApiRange:
    """GET /api/range endpoint."""

    def test_returns_range(self, client):
        """Returns min and max timestamps."""
        resp = client.get("/api/range")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["min"] == "2024-06-01T12:00:00Z"
        assert data["max"] == "2024-06-01T12:01:00Z"

    def test_empty_db(self, empty_client):
        """Empty database returns nulls."""
        resp = empty_client.get("/api/range")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["min"] is None
        assert data["max"] is None
