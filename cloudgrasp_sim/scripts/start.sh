#!/usr/bin/env bash
set -e
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
source /opt/ros/jazzy/setup.bash
source "$WS/install/setup.bash"
export DISPLAY="${DISPLAY:-:20}"
exec ros2 launch cloudgrasp_sim sim.launch.py "$@"
