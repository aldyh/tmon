"""Tests for tmon.config."""

from tmon.config import BUS_TIMEOUT_MS


def test_bus_timeout_ms_is_positive_int():
    """BUS_TIMEOUT_MS is a positive integer."""
    assert isinstance(BUS_TIMEOUT_MS, int)
    assert BUS_TIMEOUT_MS > 0
