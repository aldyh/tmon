#!/bin/bash
# uninstall.sh -- remove tmon from a target machine
#
# Run as root:
#   sudo deploy/uninstall.sh          # keeps config and data
#   sudo deploy/uninstall.sh --purge  # removes everything

set -euo pipefail

ETC_DIR="/etc/tmon"
VAR_DIR="/var/lib/tmon"
SYSTEMD_DIR="/etc/systemd/system"

PURGE=0
if [ "${1:-}" = "--purge" ]; then
  PURGE=1
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "error: must run as root" >&2
  exit 1
fi

# ------------------------------------------------------------------
# Stop and disable services
# ------------------------------------------------------------------

echo "Stopping services..."
for svc in tmond-485 tmond-wifi tmon-panel; do
  systemctl stop "${svc}" 2>/dev/null || true
  systemctl disable "${svc}" 2>/dev/null || true
done

# ------------------------------------------------------------------
# Remove systemd units
# ------------------------------------------------------------------

echo "Removing systemd units..."
rm -f "${SYSTEMD_DIR}/tmond-485.service"
rm -f "${SYSTEMD_DIR}/tmond-wifi.service"
rm -f "${SYSTEMD_DIR}/tmon-panel.service"
systemctl daemon-reload

# ------------------------------------------------------------------
# Remove flash tool
# ------------------------------------------------------------------

echo "Removing /usr/local/bin/tmon-flash and tmon-patch..."
rm -f /usr/local/bin/tmon-flash
rm -f /usr/local/bin/tmon-patch

# ------------------------------------------------------------------
# Remove venv and panel (always)
# ------------------------------------------------------------------

echo "Removing ${VAR_DIR}/venv/..."
rm -rf "${VAR_DIR}/venv"

echo "Removing ${VAR_DIR}/panel/..."
rm -rf "${VAR_DIR}/panel"

echo "Removing ${VAR_DIR}/firmware/..."
rm -rf "${VAR_DIR}/firmware"

# ------------------------------------------------------------------
# Remove user
# ------------------------------------------------------------------

if id tmon >/dev/null 2>&1; then
  echo "Removing system user 'tmon'..."
  userdel tmon 2>/dev/null || true
fi

# ------------------------------------------------------------------
# Purge (optional)
# ------------------------------------------------------------------

if [ "${PURGE}" -eq 1 ]; then
  echo "Purging ${ETC_DIR}/ and ${VAR_DIR}/..."
  rm -rf "${ETC_DIR}"
  rm -rf "${VAR_DIR}"
else
  echo ""
  echo "Config and data preserved:"
  echo "  ${ETC_DIR}/"
  echo "  ${VAR_DIR}/"
  echo "Use --purge to remove everything."
fi

echo ""
echo "tmon uninstalled."
