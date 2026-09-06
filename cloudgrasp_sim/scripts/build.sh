#!/usr/bin/env bash
set -euo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
set +u
source /opt/ros/jazzy/setup.bash
set -u
cd "$WS"
colcon build --symlink-install --parallel-workers 3 --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
