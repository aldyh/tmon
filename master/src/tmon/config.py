"""Project-wide configuration constants and config-file loading.

Central place for tuneable parameters shared across modules.
Import individual names where needed.

Example:
    >>> from tmon.config import BUS_TIMEOUT_MS
    >>> print(BUS_TIMEOUT_MS)
    200

    >>> from tmon.config import load_config
    >>> cfg = load_config("config.toml")
    >>> cfg["port"]
    '/dev/ttyUSB0'
"""

import tomllib


# Serial bus receive timeout in milliseconds.
BUS_TIMEOUT_MS = 200


def load_config(path: str) -> dict:
    """Read a TOML config file and validate required keys.

    Required keys: ``port`` (str), ``slaves`` (list[int]),
    ``db`` (str), ``interval`` (int).

    Raises:
        ValueError: If any required key is missing or has the wrong type.

    Example:
        >>> cfg = load_config("master/config.toml")
        >>> cfg["slaves"]
        [1, 2, 3]
    """
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    _require_str(raw, "port")
    _require_str(raw, "db")
    _require_int(raw, "interval")

    if "slaves" not in raw:
        raise ValueError("missing required key: slaves")
    if not isinstance(raw["slaves"], list):
        raise ValueError("slaves must be a list of ints")
    for i, v in enumerate(raw["slaves"]):
        if not isinstance(v, int):
            raise ValueError("slaves[%d] must be int, got %s" % (i, type(v).__name__))
    if len(raw["slaves"]) == 0:
        raise ValueError("slaves must not be empty")

    return {
        "port": raw["port"],
        "slaves": raw["slaves"],
        "db": raw["db"],
        "interval": raw["interval"],
    }


def _require_str(raw: dict[str, object], key: str) -> None:
    """Validate that *key* exists in *raw* and is a str."""
    if key not in raw:
        raise ValueError("missing required key: %s" % key)
    if not isinstance(raw[key], str):
        raise ValueError("%s must be str, got %s" % (key, type(raw[key]).__name__))


def _require_int(raw: dict[str, object], key: str) -> None:
    """Validate that *key* exists in *raw* and is an int."""
    if key not in raw:
        raise ValueError("missing required key: %s" % key)
    if not isinstance(raw[key], int):
        raise ValueError("%s must be int, got %s" % (key, type(raw[key]).__name__))
