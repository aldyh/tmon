"""
PlatformIO extra script to inject WiFi credentials from config-wifi.toml.

Reads ../master/config-wifi.toml and sets build flags for WIFI_SSID,
WIFI_PASSWORD, MASTER_HOST, and MASTER_PORT.

Also reads SLAVE_ADDR from the environment variable if set.
"""
Import("env")
import os
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
        f'-DMASTER_HOST=\\"{wifi.get("master_ip", "192.168.1.100")}\\"',
        f"-DMASTER_PORT={wifi.get('port', 5555)}",
    ])

# Override SLAVE_ADDR from environment variable if set
slave_addr = os.environ.get("SLAVE_ADDR")
if slave_addr is not None:
    env.Append(BUILD_FLAGS=[f"-DSLAVE_ADDR={slave_addr}"])
