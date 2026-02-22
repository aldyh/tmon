"""Path resolution for config and data files.

Resolves config and database paths for both development and production
contexts:

  Dev:        ./tmon.toml       -> ./data/tmon.db
  Production: /etc/tmon/tmon.toml -> /var/lib/tmon/tmon.db
"""

import os

ETC_DIR = "/etc/tmon"
VAR_DIR = "/var/lib/tmon"


def resolve_config(name: str) -> str:
    """Resolve a config file name to an absolute path.

    If *name* contains a ``/``, it is treated as an explicit path and
    returned as-is (made absolute) after verifying it exists.

    If *name* is a bare filename, the current directory is searched
    first, then ``/etc/tmon/``.  The first match is returned.

    Args:
        name: A bare filename (e.g. ``"tmon.toml"``) or a path
              (e.g. ``"server/tmon.toml"``).

    Raises:
        FileNotFoundError: If the file cannot be found.
    """
    if "/" in name:
        path = os.path.abspath(name)
        if not os.path.isfile(path):
            raise FileNotFoundError("config file not found: %s" % path)
        return path

    local = os.path.abspath(name)
    if os.path.isfile(local):
        return local

    etc = os.path.join(ETC_DIR, name)
    if os.path.isfile(etc):
        return os.path.abspath(etc)

    raise FileNotFoundError(
        "config file '%s' not found in ./ or %s/" % (name, ETC_DIR)
    )


def resolve_db(config_path: str, db_name: str) -> str:
    """Resolve the database path based on the config file location.

    If *config_path* is under ``/etc/tmon/``, the database is placed
    in ``/var/lib/tmon/``.  Otherwise it goes in a ``data/``
    subdirectory next to the config file.

    Args:
        config_path: Absolute path to the resolved config file.
        db_name: Bare database filename from the config (e.g. ``"tmon.db"``).
    """
    config_dir = os.path.dirname(config_path)
    if config_dir.startswith(ETC_DIR):
        return os.path.join(VAR_DIR, db_name)
    return os.path.join(config_dir, "data", db_name)


def find_db(db_name: str) -> str:
    """Find an existing database file, or return the production path.

    Searches ``./data/<db_name>`` first, then ``/var/lib/tmon/<db_name>``.
    Returns the first path that exists, or falls back to the production
    path if neither exists.

    Args:
        db_name: Bare database filename (e.g. ``"tmon.db"``).
    """
    local = os.path.join("data", db_name)
    if os.path.isfile(local):
        return os.path.abspath(local)

    prod = os.path.join(VAR_DIR, db_name)
    if os.path.isfile(prod):
        return prod

    return prod
