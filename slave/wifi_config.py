"""
PlatformIO extra script to inject WiFi credentials from config-wifi.toml.

Reads ../master/config-wifi.toml and sets build flags for WIFI_SSID,
WIFI_PASSWORD, MASTER_HOST, and MASTER_PORT.
"""
Import("env")
import tomllib
from pathlib import Path

project_dir = Path(env.subst("$PROJECT_DIR"))
config_path = project_dir.parent / "master" / "config-wifi.toml"
if config_path.exists():
    cfg = tomllib.loads(config_path.read_text())
    wifi = cfg.get("wifi", {})
    env.Append(BUILD_FLAGS=[
        f'-DWIFI_SSID=\\"{wifi.get("ssid", "changeme")}\\"',
        f'-DWIFI_PASSWORD=\\"{wifi.get("password", "changeme")}\\"',
        f'-DMASTER_HOST=\\"{wifi.get("master_host", "192.168.1.100")}\\"',
        f"-DMASTER_PORT={wifi.get('port', 5555)}",
    ])
