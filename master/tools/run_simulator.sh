#!/bin/bash
# Start a socat PTY pair and run the tmon simulator.
#
# Creates two linked pseudo-terminals:
#   /tmp/tmon-master  -- the master connects here
#   /tmp/tmon-slave   -- the simulator listens here
#
# Usage:
#   ./run_simulator.sh
#
# Example:
#   ./run_simulator.sh

set -e

MASTER_PTY="/tmp/tmon-master"
SLAVE_PTY="/tmp/tmon-slave"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/../.venv"

cleanup() {
    [ -n "$SIM_PID" ] && kill "$SIM_PID" 2>/dev/null || true
    [ -n "$SOCAT_PID" ] && kill "$SOCAT_PID" 2>/dev/null || true
    rm -f "$MASTER_PTY" "$SLAVE_PTY"
}
trap cleanup EXIT

# Start socat PTY pair
socat -d -d \
    "PTY,raw,echo=0,link=$MASTER_PTY" \
    "PTY,raw,echo=0,link=$SLAVE_PTY" &
SOCAT_PID=$!

# Wait for PTYs to appear
for i in $(seq 1 20); do
    [ -e "$MASTER_PTY" ] && [ -e "$SLAVE_PTY" ] && break
    sleep 0.1
done

if [ ! -e "$MASTER_PTY" ] || [ ! -e "$SLAVE_PTY" ]; then
    echo "error: socat PTYs did not appear" >&2
    exit 1
fi

echo "PTY pair ready: master=$MASTER_PTY slave=$SLAVE_PTY"

# Run simulator
. "$VENV_DIR/bin/activate"
python3 "$SCRIPT_DIR/simulator.py" "$SLAVE_PTY"
