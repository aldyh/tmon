"""Project-wide configuration constants and config-file loading.

Central place for tuneable parameters shared across modules.
Import individual names where needed.
"""

import tomllib

# Receive timeout in milliseconds for bus communication.
TIMEOUT_MS = 200


def load_config(path: str, transport: str) -> dict:
    """Read a TOML config file and validate required keys.

    The *transport* selects which section to validate: ``[rs485]`` or
    ``[wifi]``.  The transport is not read from the TOML file itself.

    Common keys: ``db`` (str).

    For rs485: ``[rs485]`` section with ``clients`` (list[int]),
    ``interval`` (int), ``port`` (str), ``baudrate`` (int).
    For wifi: ``[wifi]`` section with ``port`` (int).

    Raises:
        ValueError: If any required key is missing or has the wrong type.
    """
    if transport not in ("rs485", "wifi"):
        raise ValueError("transport must be 'rs485' or 'wifi', got '%s'" % transport)

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    _require_str(raw, "db")

    result = {
        "transport": transport,
        "db": raw["db"],
    }

    if transport == "wifi":
        _require_wifi_section(raw)
        result["wifi_port"] = raw["wifi"]["port"]
    else:
        section = raw.get("rs485")
        if not isinstance(section, dict):
            raise ValueError("rs485 transport requires [rs485] section")
        _require_clients(section)
        _require_int(section, "interval")
        _require_str(section, "port")
        _require_int(section, "baudrate")
        result["clients"] = section["clients"]
        result["interval"] = section["interval"]
        result["port"] = section["port"]
        result["baudrate"] = section["baudrate"]

    return result


def _require_clients(raw: dict[str, object]) -> None:
    """Validate that clients exists and is a non-empty list of ints."""
    if "clients" not in raw:
        raise ValueError("missing required key: clients")
    if not isinstance(raw["clients"], list):
        raise ValueError("clients must be a list of ints")
    for i, v in enumerate(raw["clients"]):
        if not isinstance(v, int):
            raise ValueError("clients[%d] must be int, got %s" % (i, type(v).__name__))
        if v < 1 or v > 247:
            raise ValueError("clients[%d] must be 1-247, got %d" % (i, v))
    if len(raw["clients"]) == 0:
        raise ValueError("clients must not be empty")


def _require_wifi_section(raw: dict[str, object]) -> None:
    """Validate [wifi] section has port (int)."""
    if "wifi" not in raw:
        raise ValueError("wifi transport requires [wifi] section")
    wifi = raw["wifi"]
    if not isinstance(wifi, dict):
        raise ValueError("[wifi] must be a table")
    if "port" not in wifi:
        raise ValueError("missing required key: wifi.port")
    if not isinstance(wifi["port"], int):
        raise ValueError("wifi.port must be int, got %s" % type(wifi["port"]).__name__)


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
