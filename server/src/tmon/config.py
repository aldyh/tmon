"""Project-wide configuration constants and config-file loading.

Central place for tuneable parameters shared across modules.
Import individual names where needed.

Example:
    >>> from tmon.config import load_config, TIMEOUT_MS
    >>> cfg = load_config("config-485.toml")
    >>> cfg["transport"]
    'rs485'
"""

import tomllib

# Receive timeout in milliseconds for bus communication.
TIMEOUT_MS = 200


def load_config(path: str) -> dict:
    """Read a TOML config file and validate required keys.

    Common keys: ``transport`` (str, "rs485" or "udp"), ``db`` (str).

    For rs485: ``sensors`` (list[int]), ``interval`` (int), ``port`` (str),
    ``baudrate`` (int).
    For udp: ``[udp]`` section with ``port`` (int).

    Raises:
        ValueError: If any required key is missing or has the wrong type.

    Example:
        >>> cfg = load_config("server/config-485.toml")
        >>> cfg["sensors"]
        [1, 2, 3]
    """
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    transport = raw.get("transport", "rs485")
    if not isinstance(transport, str):
        raise ValueError("transport must be str, got %s" % type(transport).__name__)
    if transport not in ("rs485", "udp"):
        raise ValueError("transport must be 'rs485' or 'udp', got '%s'" % transport)

    _require_str(raw, "db")

    result = {
        "transport": transport,
        "db": raw["db"],
    }

    if transport == "udp":
        _require_udp_section(raw)
        result["udp_port"] = raw["udp"]["port"]
    else:
        # RS-485 needs sensors, interval, port, baudrate
        _require_int(raw, "interval")
        _require_sensors(raw)
        _require_str(raw, "port")
        _require_int(raw, "baudrate")
        result["sensors"] = raw["sensors"]
        result["interval"] = raw["interval"]
        result["port"] = raw["port"]
        result["baudrate"] = raw["baudrate"]

    return result


def _require_sensors(raw: dict[str, object]) -> None:
    """Validate that sensors exists and is a non-empty list of ints."""
    if "sensors" not in raw:
        raise ValueError("missing required key: sensors")
    if not isinstance(raw["sensors"], list):
        raise ValueError("sensors must be a list of ints")
    for i, v in enumerate(raw["sensors"]):
        if not isinstance(v, int):
            raise ValueError("sensors[%d] must be int, got %s" % (i, type(v).__name__))
    if len(raw["sensors"]) == 0:
        raise ValueError("sensors must not be empty")


def _require_udp_section(raw: dict[str, object]) -> None:
    """Validate [udp] section has port (int)."""
    if "udp" not in raw:
        raise ValueError("udp transport requires [udp] section")
    udp = raw["udp"]
    if not isinstance(udp, dict):
        raise ValueError("[udp] must be a table")
    if "port" not in udp:
        raise ValueError("missing required key: udp.port")
    if not isinstance(udp["port"], int):
        raise ValueError("udp.port must be int, got %s" % type(udp["port"]).__name__)


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
