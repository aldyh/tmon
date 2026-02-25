"""Tests for tmon.config."""

import os

import pytest

from tmon.config import load_config


def _write_toml(tmp_path: str, text: str) -> str:
    """Write TOML text to a temp file and return its path."""
    path = os.path.join(tmp_path, "cfg.toml")
    with open(path, "w") as f:
        f.write(text)
    return path


class TestLoadConfig:
    """Tests for load_config()."""

    def test_valid_rs485_config(self, tmp_path):
        """RS-485 config returns expected dict."""
        path = _write_toml(tmp_path, (
            'db = "data/readings.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1, 2, 3]\n'
            'interval = 30\n'
        ))
        cfg = load_config(path, "rs485")
        assert cfg["transport"] == "rs485"
        assert cfg["port"] == "/dev/ttyUSB0"
        assert cfg["baudrate"] == 9600
        assert cfg["clients"] == [1, 2, 3]
        assert cfg["db"] == "data/readings.db"
        assert cfg["interval"] == 30

    def test_missing_rs485_section(self, tmp_path):
        """Missing [rs485] section raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
        ))
        with pytest.raises(ValueError, match="rs485.*section"):
            load_config(path, "rs485")

    def test_missing_port(self, tmp_path):
        """Missing 'port' key in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="port"):
            load_config(path, "rs485")

    def test_missing_baudrate(self, tmp_path):
        """Missing 'baudrate' key in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'clients = [1]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="baudrate"):
            load_config(path, "rs485")

    def test_missing_clients(self, tmp_path):
        """Missing 'clients' key in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path, "rs485")

    def test_missing_db(self, tmp_path):
        """Missing 'db' key raises ValueError."""
        path = _write_toml(tmp_path, (
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="db"):
            load_config(path, "rs485")

    def test_missing_interval(self, tmp_path):
        """Missing 'interval' key in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
        ))
        with pytest.raises(ValueError, match="interval"):
            load_config(path, "rs485")

    def test_port_wrong_type(self, tmp_path):
        """Non-string 'port' in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = 123\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="port"):
            load_config(path, "rs485")

    def test_baudrate_wrong_type(self, tmp_path):
        """Non-int 'baudrate' in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = "fast"\n'
            'clients = [1]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="baudrate"):
            load_config(path, "rs485")

    def test_clients_wrong_type(self, tmp_path):
        """Non-list 'clients' in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = "not a list"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path, "rs485")

    def test_clients_element_wrong_type(self, tmp_path):
        """Non-int element in 'clients' raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1, "two"]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path, "rs485")

    def test_clients_addr_zero(self, tmp_path):
        """Address 0 in clients raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [0]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients.*1-247"):
            load_config(path, "rs485")

    def test_clients_addr_too_high(self, tmp_path):
        """Address 248 in clients raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1, 248]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients.*1-247"):
            load_config(path, "rs485")

    def test_clients_empty(self, tmp_path):
        """Empty 'clients' list raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = []\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path, "rs485")

    def test_interval_wrong_type(self, tmp_path):
        """Non-int 'interval' in [rs485] raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'interval = "fast"\n'
        ))
        with pytest.raises(ValueError, match="interval"):
            load_config(path, "rs485")

    def test_extra_keys_ignored(self, tmp_path):
        """Extra keys in the TOML are silently ignored."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            'extra = "ignored"\n'
            '\n'
            '[rs485]\n'
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'interval = 10\n'
        ))
        cfg = load_config(path, "rs485")
        assert "extra" not in cfg

    def test_invalid_transport(self, tmp_path):
        """Invalid transport value raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
        ))
        with pytest.raises(ValueError, match="transport"):
            load_config(path, "bluetooth")

    def test_valid_wifi_config(self, tmp_path):
        """WiFi config with [wifi] section returns expected dict."""
        path = _write_toml(tmp_path, (
            'db = "data/readings.db"\n'
            '\n'
            '[wifi]\n'
            'port = 5555\n'
        ))
        cfg = load_config(path, "wifi")
        assert cfg["transport"] == "wifi"
        assert cfg["wifi_port"] == 5555
        assert cfg["db"] == "data/readings.db"
        assert "clients" not in cfg
        assert "interval" not in cfg

    def test_wifi_missing_section(self, tmp_path):
        """WiFi transport without [wifi] section raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
        ))
        with pytest.raises(ValueError, match="wifi.*section"):
            load_config(path, "wifi")

    def test_wifi_missing_port(self, tmp_path):
        """WiFi section without port raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[wifi]\n'
        ))
        with pytest.raises(ValueError, match="wifi.port"):
            load_config(path, "wifi")

    def test_wifi_port_wrong_type(self, tmp_path):
        """WiFi port as string raises ValueError."""
        path = _write_toml(tmp_path, (
            'db = "test.db"\n'
            '\n'
            '[wifi]\n'
            'port = "5555"\n'
        ))
        with pytest.raises(ValueError, match="wifi.port.*int"):
            load_config(path, "wifi")
