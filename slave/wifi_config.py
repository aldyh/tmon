"""
PlatformIO extra script to inject WiFi credentials from wifi.toml.

Reads ../master/wifi.toml and sets build flags for WIFI_SSID,
WIFI_PASSWORD, and MASTER_HOST.  Also reads [udp].port and
[udp].push_interval from ../master/config-udp.toml.

Fails with a clear error if wifi.toml is missing.
"""
Import("env")
import sys
import tomllib
from pathlib import Path

project_dir = Path(env.subst("$PROJECT_DIR"))
master_dir = project_dir.parent / "master"

wifi_path = master_dir / "wifi.toml"
if not wifi_path.exists():
    example_path = master_dir / "wifi.toml.example"
    sys.stderr.write(
        "\n"
        "ERROR: wifi.toml not found.\n"
        "\n"
        "Copy wifi.toml.example to wifi.toml and fill in your credentials:\n"
        f"  cp {example_path} {wifi_path}\n"
        "\n"
    )
    env.Exit(1)

wifi = tomllib.loads(wifi_path.read_text())

# Read UDP settings from config-udp.toml [udp] section
config_path = master_dir / "config-udp.toml"
master_port = 5555
push_interval = 60
if config_path.exists():
    cfg = tomllib.loads(config_path.read_text())
    udp_cfg = cfg.get("udp", {})
    master_port = udp_cfg.get("port", 5555)
    push_interval = udp_cfg.get("push_interval", 60)

env.Append(BUILD_FLAGS=[
    f'-DWIFI_SSID=\\"{wifi.get("ssid", "changeme")}\\"',
    f'-DWIFI_PASSWORD=\\"{wifi.get("password", "changeme")}\\"',
    f'-DMASTER_HOST=\\"{wifi.get("master_host", "192.168.1.100")}\\"',
    f"-DMASTER_PORT={master_port}",
    f"-DPUSH_INTERVAL_S={push_interval}",
])
