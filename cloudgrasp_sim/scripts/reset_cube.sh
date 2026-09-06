#!/usr/bin/env bash
set -e
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
source /opt/ros/jazzy/setup.bash
exec 9>"$WS/logs/pick.lock"
flock -n 9 || { echo 'Wait for the current grasp to finish.'; exit 1; }
gz service -s /world/cloudgrasp/set_pose --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 5000 --req 'name: "target_cube", position: {x: 0.45, y: 0.15, z: 0.025}, orientation: {w: 1.0}'
