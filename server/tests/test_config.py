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
        """RS-485 config (default transport) returns expected dict."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1, 2, 3]\n'
            'db = "data/readings.db"\n'
            'interval = 30\n'
        ))
        cfg = load_config(path)
        assert cfg["transport"] == "rs485"
        assert cfg["port"] == "/dev/ttyUSB0"
        assert cfg["baudrate"] == 9600
        assert cfg["clients"] == [1, 2, 3]
        assert cfg["db"] == "data/readings.db"
        assert cfg["interval"] == 30

    def test_missing_port(self, tmp_path):
        """Missing 'port' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'baudrate = 9600\n'
            'clients = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="port"):
            load_config(path)

    def test_missing_baudrate(self, tmp_path):
        """Missing 'baudrate' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'clients = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="baudrate"):
            load_config(path)

    def test_missing_clients(self, tmp_path):
        """Missing 'clients' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path)

    def test_missing_db(self, tmp_path):
        """Missing 'db' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="db"):
            load_config(path)

    def test_missing_interval(self, tmp_path):
        """Missing 'interval' key raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'db = "test.db"\n'
        ))
        with pytest.raises(ValueError, match="interval"):
            load_config(path)

    def test_port_wrong_type(self, tmp_path):
        """Non-string 'port' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = 123\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="port"):
            load_config(path)

    def test_baudrate_wrong_type(self, tmp_path):
        """Non-int 'baudrate' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = "fast"\n'
            'clients = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="baudrate"):
            load_config(path)

    def test_clients_wrong_type(self, tmp_path):
        """Non-list 'clients' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = "not a list"\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path)

    def test_clients_element_wrong_type(self, tmp_path):
        """Non-int element in 'clients' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1, "two"]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path)

    def test_clients_addr_zero(self, tmp_path):
        """Address 0 in clients raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [0]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients.*1-247"):
            load_config(path)

    def test_clients_addr_too_high(self, tmp_path):
        """Address 248 in clients raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1, 248]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients.*1-247"):
            load_config(path)

    def test_clients_empty(self, tmp_path):
        """Empty 'clients' list raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = []\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="clients"):
            load_config(path)

    def test_interval_wrong_type(self, tmp_path):
        """Non-int 'interval' raises ValueError."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'db = "test.db"\n'
            'interval = "fast"\n'
        ))
        with pytest.raises(ValueError, match="interval"):
            load_config(path)

    def test_extra_keys_ignored(self, tmp_path):
        """Extra keys in the TOML are silently ignored."""
        path = _write_toml(tmp_path, (
            'port = "/dev/ttyUSB0"\n'
            'baudrate = 9600\n'
            'clients = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
            'extra = "ignored"\n'
        ))
        cfg = load_config(path)
        assert "extra" not in cfg

    def test_invalid_transport(self, tmp_path):
        """Invalid transport value raises ValueError."""
        path = _write_toml(tmp_path, (
            'transport = "bluetooth"\n'
            'clients = [1]\n'
            'db = "test.db"\n'
            'interval = 10\n'
        ))
        with pytest.raises(ValueError, match="transport"):
            load_config(path)

    def test_valid_udp_config(self, tmp_path):
        """UDP config with [udp] section returns expected dict."""
        path = _write_toml(tmp_path, (
            'transport = "udp"\n'
            'db = "data/readings.db"\n'
            '\n'
            '[udp]\n'
            'port = 5555\n'
        ))
        cfg = load_config(path)
        assert cfg["transport"] == "udp"
        assert cfg["udp_port"] == 5555
        assert cfg["db"] == "data/readings.db"
        assert "clients" not in cfg
        assert "interval" not in cfg

    def test_udp_missing_section(self, tmp_path):
        """UDP transport without [udp] section raises ValueError."""
        path = _write_toml(tmp_path, (
            'transport = "udp"\n'
            'db = "test.db"\n'
        ))
        with pytest.raises(ValueError, match="udp.*section"):
            load_config(path)

    def test_udp_missing_port(self, tmp_path):
        """UDP section without port raises ValueError."""
        path = _write_toml(tmp_path, (
            'transport = "udp"\n'
            'db = "test.db"\n'
            '\n'
            '[udp]\n'
        ))
        with pytest.raises(ValueError, match="udp.port"):
            load_config(path)

    def test_udp_port_wrong_type(self, tmp_path):
        """UDP port as string raises ValueError."""
        path = _write_toml(tmp_path, (
            'transport = "udp"\n'
            'db = "test.db"\n'
            '\n'
            '[udp]\n'
            'port = "5555"\n'
        ))
        with pytest.raises(ValueError, match="udp.port.*int"):
            load_config(path)
