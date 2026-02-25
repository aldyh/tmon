#!/bin/bash
# install.sh -- install tmon on a target machine
#
# Run as root from the project root directory:
#   sudo deploy/install.sh
#
# Interactive installer: prompts for configuration, writes config files,
# installs packages, and enables systemd services in one pass.
# Re-running clobbers previous config (KISS).

set -euo pipefail

ETC_DIR="/etc/tmon"
VAR_DIR="/var/lib/tmon"
VENV_DIR="${VAR_DIR}/venv"
PANEL_DIR="${VAR_DIR}/panel"
FW_DIR="${VAR_DIR}/firmware"
SYSTEMD_DIR="/etc/systemd/system"

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

prompt () {
  # Usage: prompt "Label" DEFAULT_VALUE
  # Prints "Label [DEFAULT_VALUE]: " and reads a line.
  # Returns the user's input, or the default if they pressed Enter.
  local label="$1"
  local default="$2"
  local input
  read -rp "  ${label} [${default}]: " input
  echo "${input:-${default}}"
}

prompt_secret () {
  # Like prompt, but no default shown and no echo.
  local label="$1"
  local input
  read -rsp "  ${label}: " input
  echo >&2  # newline after hidden input
  echo "${input}"
}

prompt_yn () {
  # Usage: prompt_yn "Question" DEFAULT (y or n)
  # Returns 0 for yes, 1 for no.
  local label="$1"
  local default="$2"
  local hint
  if [ "${default}" = "y" ]; then hint="Y/n"; else hint="y/N"; fi
  local input
  read -rp "  ${label} [${hint}]: " input
  input="${input:-${default}}"
  case "${input}" in
    [Yy]*) return 0 ;;
    *)     return 1 ;;
  esac
}

detect_serial_port () {
  local ports=()
  for pattern in /dev/ttyACM* /dev/ttyUSB*; do
    for p in ${pattern}; do
      [ -e "${p}" ] && ports+=("${p}")
    done
  done
  if [ ${#ports[@]} -gt 0 ]; then
    echo "${ports[0]}"
  else
    echo "/dev/ttyUSB0"
  fi
}

detect_ip () {
  hostname -I 2>/dev/null | awk '{print $1}' || echo "192.168.1.100"
}

# ------------------------------------------------------------------
# Preflight checks
# ------------------------------------------------------------------

if [ "$(id -u)" -ne 0 ]; then
  echo "error: must run as root" >&2
  exit 1
fi

if [ ! -f server/pyproject.toml ]; then
  echo "error: run from the project root directory" >&2
  exit 1
fi

# ------------------------------------------------------------------
# Interactive prompts
# ------------------------------------------------------------------

echo ""
echo "tmon installer"
echo "==============="
echo ""

SERIAL_PORT=$(prompt "Serial port" "$(detect_serial_port)")
CLIENTS=$(prompt "Client addresses" "1")
POLL_INTERVAL=$(prompt "Poll interval (seconds)" "5")

echo ""
ENABLE_WIFI=0
if prompt_yn "Enable WiFi clients?" "n"; then
  ENABLE_WIFI=1
  WIFI_SSID=$(prompt "WiFi SSID" "")
  WIFI_PASS=$(prompt_secret "WiFi password")
  SERVER_IP=$(prompt "Server IP" "$(detect_ip)")
  LISTEN_PORT=$(prompt "Listen port" "5555")
  PUSH_INTERVAL=$(prompt "Push interval (seconds)" "5")
fi

echo ""

# ------------------------------------------------------------------
# System user
# ------------------------------------------------------------------

if ! id tmon >/dev/null 2>&1; then
  echo "Creating system user 'tmon'..."
  useradd --system --no-create-home --shell /usr/sbin/nologin tmon
fi

# Serial access (RS-485 adapter)
if getent group dialout >/dev/null 2>&1; then
  usermod -aG dialout tmon
fi

# ------------------------------------------------------------------
# Directories
# ------------------------------------------------------------------

echo "Creating directories..."
mkdir -p "${ETC_DIR}" "${VAR_DIR}" "${FW_DIR}" "${PANEL_DIR}"

# ------------------------------------------------------------------
# Python virtual environment
# ------------------------------------------------------------------

echo "Creating virtual environment at ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}"

echo "Installing server daemon..."
"${VENV_DIR}/bin/pip" install --quiet server/

echo "Installing panel dependencies..."
"${VENV_DIR}/bin/pip" install --quiet panel/

echo "Installing esptool..."
"${VENV_DIR}/bin/pip" install --quiet esptool

# ------------------------------------------------------------------
# Write config files
# ------------------------------------------------------------------

echo "Writing ${ETC_DIR}/tmon.toml..."

# Build clients array: "1" → "[1]", "1, 2, 3" → "[1, 2, 3]"
CLIENTS_ARRAY="[${CLIENTS}]"

cat > "${ETC_DIR}/tmon.toml" <<TOML
db = "tmon.db"

[rs485]
clients = ${CLIENTS_ARRAY}
interval = ${POLL_INTERVAL}
port = "${SERIAL_PORT}"
baudrate = 9600

[wifi]
port = ${LISTEN_PORT:-5555}
push_interval = ${PUSH_INTERVAL:-5}
TOML

if [ "${ENABLE_WIFI}" -eq 1 ]; then
  echo "Writing ${ETC_DIR}/wifi.toml..."
  cat > "${ETC_DIR}/wifi.toml" <<TOML
ssid = "${WIFI_SSID}"
password = "${WIFI_PASS}"
server_host = "${SERVER_IP}"
TOML
fi

chown -R tmon:tmon "${ETC_DIR}"

# ------------------------------------------------------------------
# Panel app files
# ------------------------------------------------------------------

echo "Copying panel files to ${PANEL_DIR}..."
cp panel/app.py "${PANEL_DIR}/"
cp -r panel/templates "${PANEL_DIR}/"
cp -r panel/static "${PANEL_DIR}/"

# ------------------------------------------------------------------
# Firmware binaries
# ------------------------------------------------------------------

if [ -d firmware ]; then
  echo "Copying firmware from firmware/..."
  cp firmware/*.bin "${FW_DIR}/"
else
  echo "error: firmware/ directory not found (run 'make firmware')" >&2
  exit 1
fi

# ------------------------------------------------------------------
# Ownership
# ------------------------------------------------------------------

chown -R tmon:tmon "${VAR_DIR}"

# ------------------------------------------------------------------
# Flash tool
# ------------------------------------------------------------------

echo "Installing tmon-flash and tmon-patch to /usr/local/bin/..."
install -m 755 deploy/tmon-flash /usr/local/bin/tmon-flash
install -m 755 deploy/tmon-patch /usr/local/bin/tmon-patch

# ------------------------------------------------------------------
# systemd units
# ------------------------------------------------------------------

echo "Installing systemd services..."
cp deploy/tmond-485.service "${SYSTEMD_DIR}/"
cp deploy/tmond-wifi.service "${SYSTEMD_DIR}/"
cp deploy/tmon-panel.service "${SYSTEMD_DIR}/"
systemctl daemon-reload

echo "Enabling and starting services..."
systemctl enable --now tmond-485
if [ "${ENABLE_WIFI}" -eq 1 ]; then
  systemctl enable --now tmond-wifi
fi
systemctl enable --now tmon-panel

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

PANEL_IP=$(detect_ip)

echo ""
echo "tmon installed successfully."
echo ""
echo "  Config:      ${ETC_DIR}/tmon.toml"
if [ "${ENABLE_WIFI}" -eq 1 ]; then
echo "  WiFi config: ${ETC_DIR}/wifi.toml"
fi
echo "  Dashboard:   http://${PANEL_IP}:5000"
echo ""
echo "  Services running:"
echo "    tmond-485      ✓"
if [ "${ENABLE_WIFI}" -eq 1 ]; then
echo "    tmond-wifi     ✓"
fi
echo "    tmon-panel     ✓"
echo ""
echo "  Logs:"
echo "    journalctl -u tmond-485 -f"
if [ "${ENABLE_WIFI}" -eq 1 ]; then
echo "    journalctl -u tmond-wifi -f"
fi
echo ""
echo "  Reconfigure:"
echo "    edit ${ETC_DIR}/tmon.toml, then: sudo systemctl restart tmond-485"
if [ "${ENABLE_WIFI}" -eq 1 ]; then
echo "    edit ${ETC_DIR}/wifi.toml, then: sudo systemctl restart tmond-wifi"
fi
