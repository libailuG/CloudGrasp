#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
if [[ -f "$WS/logs/session.env" ]]; then source "$WS/logs/session.env"; fi
source /opt/ros/jazzy/setup.bash
source "$WS/install/setup.bash"
exec /usr/bin/python3 "$SCRIPT_DIR/run_pick.py" "$@"
