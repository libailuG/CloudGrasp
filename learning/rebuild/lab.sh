#!/usr/bin/env bash
set -e
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
mkdir -p "$LAB_ROOT/.runtime"
S="$LAB_ROOT/cloudgrasp_lab/scripts"
command="${1:-help}"; shift || true
case "$command" in
  start) exec /usr/bin/python3 "$S/runner.py" "$@" ;;
  stop) exec /usr/bin/python3 "$S/runner.py" stop ;;
  ready) exec /usr/bin/python3 "$S/ready.py" "$@" ;;
  joint) exec flock -n -o "$LAB_ROOT/.runtime/action.lock" timeout --kill-after=5 35 /usr/bin/python3 "$S/joint.py" "$@" ;;
  panel) exec /usr/bin/python3 "$S/control_panel.py" ;;
  observe) exec /usr/bin/python3 "$S/observe.py" ;;
  scene) exec flock -n -o "$LAB_ROOT/.runtime/action.lock" timeout --kill-after=5 30 /usr/bin/python3 "$S/scene.py" "$@" ;;
  move) exec flock -n -o "$LAB_ROOT/.runtime/action.lock" timeout --kill-after=5 120 /usr/bin/python3 "$S/motion_run.py" "$@" ;;
  perceive) exec /usr/bin/python3 "$S/perceive.py" ;;
  pick) exec flock -n -o "$LAB_ROOT/.runtime/action.lock" /usr/bin/python3 "$S/reference_pick.py" ;;
  reset) exec flock -n -o "$LAB_ROOT/.runtime/action.lock" gz service -s /world/cloudgrasp/set_pose --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 5000 --req 'name: "target_cube", position: {x: 0.45, y: 0.15, z: 0.025}, orientation: {w: 1.0}' ;;
  *) echo 'Usage: bash learning/rebuild/lab.sh start 1..7 [gui:=false] [rviz:=false] | stop | ready 1..7 | joint wrist|home|open|close | panel | observe | move [execute:=true] [target:=home] | scene table|add|block|remove|list | perceive | reset | pick' ;;
esac
