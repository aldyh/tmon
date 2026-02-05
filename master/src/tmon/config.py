"""Project-wide configuration constants and config-file loading.

Central place for tuneable parameters shared across modules.
Import individual names where needed.

Example:
    >>> from tmon.config import load_config, TIMEOUT_MS
    >>> cfg = load_config("config.toml")
    >>> cfg["transport"]
    'rs485'
"""

import tomllib

# Receive timeout in milliseconds for bus communication.
TIMEOUT_MS = 200


def load_config(path: str) -> dict:
    """Read a TOML config file and validate required keys.

    Common keys: ``transport`` (str, "rs485", "wifi", or "udp"), ``db`` (str).

    For rs485/wifi: ``slaves`` (list[int]), ``interval`` (int).
    For rs485: ``port`` (str), ``baudrate`` (int).
    For wifi: ``[wifi]`` section with ``host`` (str), ``port`` (int).
    For udp: ``[udp]`` section with ``port`` (int).

    Raises:
        ValueError: If any required key is missing or has the wrong type.

    Example:
        >>> cfg = load_config("master/config.toml")
        >>> cfg["slaves"]
        [1, 2, 3]
    """
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    transport = raw.get("transport", "rs485")
    if not isinstance(transport, str):
        raise ValueError("transport must be str, got %s" % type(transport).__name__)
    if transport not in ("rs485", "wifi", "udp"):
        raise ValueError("transport must be 'rs485', 'wifi', or 'udp', got '%s'" % transport)

    _require_str(raw, "db")

    result = {
        "transport": transport,
        "db": raw["db"],
    }

    if transport == "udp":
        _require_udp_section(raw)
        result["udp_port"] = raw["udp"]["port"]
    else:
        # Poll-based transports need slaves and interval
        _require_int(raw, "interval")
        _require_slaves(raw)
        result["slaves"] = raw["slaves"]
        result["interval"] = raw["interval"]

        if transport == "rs485":
            _require_str(raw, "port")
            _require_int(raw, "baudrate")
            result["port"] = raw["port"]
            result["baudrate"] = raw["baudrate"]
        else:
            _require_wifi_section(raw)
            result["wifi_host"] = raw["wifi"]["host"]
            result["wifi_port"] = raw["wifi"]["port"]

    return result


def _require_slaves(raw: dict[str, object]) -> None:
    """Validate that slaves exists and is a non-empty list of ints."""
    if "slaves" not in raw:
        raise ValueError("missing required key: slaves")
    if not isinstance(raw["slaves"], list):
        raise ValueError("slaves must be a list of ints")
    for i, v in enumerate(raw["slaves"]):
        if not isinstance(v, int):
            raise ValueError("slaves[%d] must be int, got %s" % (i, type(v).__name__))
    if len(raw["slaves"]) == 0:
        raise ValueError("slaves must not be empty")


def _require_wifi_section(raw: dict[str, object]) -> None:
    """Validate [wifi] section has host (str) and port (int)."""
    if "wifi" not in raw:
        raise ValueError("wifi transport requires [wifi] section")
    wifi = raw["wifi"]
    if not isinstance(wifi, dict):
        raise ValueError("[wifi] must be a table")
    if "host" not in wifi:
        raise ValueError("missing required key: wifi.host")
    if not isinstance(wifi["host"], str):
        raise ValueError("wifi.host must be str, got %s" % type(wifi["host"]).__name__)
    if "port" not in wifi:
        raise ValueError("missing required key: wifi.port")
    if not isinstance(wifi["port"], int):
        raise ValueError("wifi.port must be int, got %s" % type(wifi["port"]).__name__)


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
