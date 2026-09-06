#!/usr/bin/env bash
set -euo pipefail
source /etc/os-release
if [[ "${VERSION_CODENAME:-}" != noble ]]; then
  echo 'This deployment targets Ubuntu 24.04 (noble) and ROS 2 Jazzy.' >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y ros-jazzy-desktop ros-jazzy-moveit ros-jazzy-ros-gz \
  ros-jazzy-gz-ros2-control ros-jazzy-ros2-controllers ros-jazzy-ur-description \
  ros-jazzy-robotiq-description ros-jazzy-grasping-msgs ros-jazzy-pcl-ros \
  ros-jazzy-xacro python3-colcon-common-extensions
