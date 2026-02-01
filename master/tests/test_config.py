"""Tests for tmon.config."""

from tmon.config import load_config


def test_placeholder():
    """Verify load_config is importable."""
    assert callable(load_config)
