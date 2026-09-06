#!/usr/bin/env bash
set -e
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
source /opt/ros/jazzy/setup.bash
source "$WS/install/setup.bash"
export DISPLAY="${DISPLAY:-:20}"
# A fresh Gazebo transport partition prevents reconnecting to an old world.
export GZ_PARTITION="cloudgrasp_$(id -u)_$$_$(date +%s)"
mkdir -p "$WS/logs"
printf 'export GZ_PARTITION=%q\n' "$GZ_PARTITION" > "$WS/logs/session.env"
exec ros2 launch cloudgrasp_sim sim.launch.py "$@"
