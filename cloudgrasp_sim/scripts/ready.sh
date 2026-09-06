#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$HERE/../../../.." && pwd)"
source /opt/ros/jazzy/setup.bash
source "$WS/install/setup.bash"
exec /usr/bin/python3 "$HERE/preflight.py" "$@"
