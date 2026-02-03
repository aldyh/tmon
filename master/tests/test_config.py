"""Tests for tmon.config."""

import os

import pytest

from tmon.config import BUS_TIMEOUT_MS, load_config


def test_bus_timeout_ms_is_positive_int():
    """BUS_TIMEOUT_MS is a positive integer."""
    assert isinstance(BUS_TIMEOUT_MS, int)
    assert BUS_TIMEOUT_MS > 0


def _write_toml(tmp_path: str, text: str) -> str:
    """Write TOML text to a temp file and return its path."""
    path = os.path.join(tmp_path, "cfg.toml")
    with open(path, "w") as f:
        f.write(text)
    return path


class TestLoadConfig:
    """Tests for load_config()."""

    def test_valid_config(self, tmp_path):
        """A valid TOML file returns the expected dict."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = [1, 2, 3]\n'
            'db = "data/readings.db"\n'
            'interval = 30\n'
        ))
        cfg = load_config(path)
        assert cfg["port"] == "/dev/ttyUSB0"
        assert cfg["slaves"] == [1, 2, 3]
        assert cfg["db"] == "data/readings.db"
        assert cfg["interval"] == 30

    def test_missing_port(self, tmp_path):
        """Missing 'port' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'slaves = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="port"):
            load_config(path)

    def test_missing_slaves(self, tmp_path):
        """Missing 'slaves' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="slaves"):
            load_config(path)

    def test_missing_db(self, tmp_path):
        """Missing 'db' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = [1]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="db"):
            load_config(path)

    def test_missing_interval(self, tmp_path):
        """Missing 'interval' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = [1]\n'
            'db = "test.db"\n'
        ))
        with pytest.raises(ValueError, match="interval"):
            load_config(path)

    def test_port_wrong_type(self, tmp_path):
        """Non-string 'port' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = 123\n'
            'slaves = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="port"):
            load_config(path)

    def test_slaves_wrong_type(self, tmp_path):
        """Non-list 'slaves' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = "not a list"\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="slaves"):
            load_config(path)

    def test_slaves_element_wrong_type(self, tmp_path):
        """Non-int element in 'slaves' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = [1, "two"]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="slaves"):
            load_config(path)

    def test_slaves_empty(self, tmp_path):
        """Empty 'slaves' list raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = []\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="slaves"):
            load_config(path)

    def test_interval_wrong_type(self, tmp_path):
        """Non-int 'interval' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = [1]\n'
            'db = "test.db"\n'
            'interval = "fast"\n'
        ))
        with pytest.raises(ValueError, match="interval"):
            load_config(path)

    def test_extra_keys_ignored(self, tmp_path):
        """Extra keys in the TOML are silently ignored."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'slaves = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
            'extra = "ignored"\n'
        ))
        cfg = load_config(path)
        assert "extra" not in cfg
