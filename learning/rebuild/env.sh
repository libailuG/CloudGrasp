# Source this file in every terminal used for this learning lab.
LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_WS="$(cd "$LAB_ROOT/../../../.." && pwd)"
source /opt/ros/jazzy/setup.bash
source "$LAB_WS/install/setup.bash"
export ROS_DOMAIN_ID=42
export GZ_PARTITION="cloudgrasp_lab_$(id -u)"
export DISPLAY="${DISPLAY:-:20}"
export ROS2CLI_NO_DAEMON=1
