#!/bin/bash
# install.sh -- install tmon on a target machine
#
# Run as root from the project root directory:
#   sudo deploy/install.sh
#
# Installs the daemon, panel, config files, and systemd services.
# Services are installed but NOT enabled -- choose which to enable:
#   sudo systemctl enable --now tmond-serial
#   sudo systemctl enable --now tmond-udp
#   sudo systemctl enable --now tmon-panel

set -euo pipefail

ETC_DIR="/etc/tmon"
VAR_DIR="/var/lib/tmon"
VENV_DIR="${VAR_DIR}/venv"
PANEL_DIR="${VAR_DIR}/panel"
FW_DIR="${VAR_DIR}/firmware"
SYSTEMD_DIR="/etc/systemd/system"

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
# Config files (no-clobber: preserve existing user edits)
# ------------------------------------------------------------------

echo "Copying config files to ${ETC_DIR}..."
cp -n server/tmon.toml "${ETC_DIR}/tmon.toml" 2>/dev/null || true
cp -n server/wifi.toml.example "${ETC_DIR}/wifi.toml.example" 2>/dev/null || true

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
cp deploy/tmond-serial.service "${SYSTEMD_DIR}/"
cp deploy/tmond-udp.service "${SYSTEMD_DIR}/"
cp deploy/tmon-panel.service "${SYSTEMD_DIR}/"
systemctl daemon-reload

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

echo ""
echo "tmon installed successfully."
echo ""
echo "  Config:   ${ETC_DIR}/"
echo "  Data:     ${VAR_DIR}/"
echo "  Venv:     ${VENV_DIR}/"
echo "  Panel:    ${PANEL_DIR}/"
echo "  Firmware: ${FW_DIR}/"
echo "  Flash:    /usr/local/bin/tmon-flash, tmon-patch"
echo ""
echo "Next steps:"
echo "  1. Edit ${ETC_DIR}/tmon.toml for your setup"
echo "  2. Enable a daemon transport:"
echo "       sudo systemctl enable --now tmond-serial"
echo "       sudo systemctl enable --now tmond-udp"
echo "  3. Enable the panel:"
echo "       sudo systemctl enable --now tmon-panel"
echo "  4. View the panel at http://$(hostname):5000"
echo "  5. Flash an ESP32:"
echo "       tmon-flash --mode=serial --addr=1"
