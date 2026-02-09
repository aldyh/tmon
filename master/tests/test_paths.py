"""Tests for tmon.paths."""

import os

import pytest

from tmon.paths import resolve_config, resolve_db, find_db
import tmon.paths as paths_mod


class TestResolveConfig:
    """Tests for resolve_config()."""

    def test_finds_local_file(self, tmp_path, monkeypatch):
        """Bare filename found in current directory is returned."""
        cfg = tmp_path / "config.toml"
        cfg.write_text("")
        monkeypatch.chdir(tmp_path)

        result = resolve_config("config.toml")

        assert result == str(cfg)

    def test_falls_back_to_etc(self, tmp_path, monkeypatch):
        """Bare filename not in cwd falls back to ETC_DIR."""
        etc = tmp_path / "etc_tmon"
        etc.mkdir()
        (etc / "config.toml").write_text("")
        monkeypatch.setattr(paths_mod, "ETC_DIR", str(etc))
        monkeypatch.chdir(tmp_path / "nonexistent_cwd_for_test"
                          if False else tmp_path)
        # Remove any local config.toml so fallback triggers
        local = tmp_path / "config.toml"
        if local.exists():
            local.unlink()

        result = resolve_config("config.toml")

        assert result == str(etc / "config.toml")

    def test_raises_when_not_found(self, tmp_path, monkeypatch):
        """FileNotFoundError raised when config is nowhere."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(paths_mod, "ETC_DIR", str(tmp_path / "no_etc"))

        with pytest.raises(FileNotFoundError, match="config.toml"):
            resolve_config("config.toml")

    def test_explicit_path_exists(self, tmp_path):
        """Path containing '/' is treated as explicit; returned absolute."""
        cfg = tmp_path / "sub" / "config.toml"
        cfg.parent.mkdir()
        cfg.write_text("")

        result = resolve_config(str(cfg))

        assert result == str(cfg)
        assert os.path.isabs(result)

    def test_explicit_path_not_found(self, tmp_path):
        """Explicit path that doesn't exist raises FileNotFoundError."""
        bad = str(tmp_path / "nope" / "config.toml")

        with pytest.raises(FileNotFoundError, match="not found"):
            resolve_config(bad)


class TestResolveDb:
    """Tests for resolve_db()."""

    def test_local_config_returns_data_subdir(self, tmp_path):
        """Config outside /etc/tmon/ -> <config_dir>/data/<name>."""
        config_path = str(tmp_path / "config.toml")

        result = resolve_db(config_path, "tmon.db")

        assert result == str(tmp_path / "data" / "tmon.db")

    def test_etc_config_returns_var_path(self):
        """Config under /etc/tmon/ -> /var/lib/tmon/<name>."""
        result = resolve_db("/etc/tmon/config.toml", "tmon.db")

        assert result == "/var/lib/tmon/tmon.db"

    def test_etc_subdir_returns_var_path(self):
        """Config under /etc/tmon/subdir/ still maps to /var/lib/tmon/."""
        result = resolve_db("/etc/tmon/nodes/config.toml", "tmon.db")

        assert result == "/var/lib/tmon/tmon.db"


class TestFindDb:
    """Tests for find_db()."""

    def test_finds_local_data_dir(self, tmp_path, monkeypatch):
        """DB in ./data/ is found first."""
        monkeypatch.chdir(tmp_path)
        data = tmp_path / "data"
        data.mkdir()
        db = data / "tmon.db"
        db.write_text("")

        result = find_db("tmon.db")

        assert result == str(db)

    def test_falls_back_to_var(self, tmp_path, monkeypatch):
        """When no local DB, falls back to VAR_DIR."""
        monkeypatch.chdir(tmp_path)
        var = tmp_path / "var_tmon"
        var.mkdir()
        db = var / "tmon.db"
        db.write_text("")
        monkeypatch.setattr(paths_mod, "VAR_DIR", str(var))

        result = find_db("tmon.db")

        assert result == str(db)

    def test_returns_prod_path_when_nothing_exists(self, tmp_path, monkeypatch):
        """When neither local nor prod exists, returns prod path anyway."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(paths_mod, "VAR_DIR", "/var/lib/tmon")

        result = find_db("tmon.db")

        assert result == "/var/lib/tmon/tmon.db"
