# Validation on the cloud server

Validated on Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic (gz-sim 8), UR5 and Robotiq 2F-85.

The grasp planner consumes camera point clouds via the original CloudGrasp `simple_grasping` pipeline. Gazebo truth is observed independently by `watch_cube.py` for verification. No Gazebo attach/teleport operation is used during a grasp. `reset_cube.sh` only resets the scene between demonstrations.

| Test | Initial object position (m) | Final object position (m) | Peak z (m) | Outcome |
|---|---|---|---|---|
| Original-position run using final scripts | (0.45, 0.15, 0.025) | (0.449958, -0.249487, 0.025000) | 0.204168 | PHYSICAL_PICK_PLACE_PASS |
| Changed-position run using final scripts | (0.50, 0.10, 0.025) | (0.500434, -0.250512, 0.025000) | 0.205395 | PHYSICAL_PICK_PLACE_PASS |

An earlier development run also completed the physical pick and place. These are a small number of simulation trials, not a statistical success-rate estimate or a real-hardware validation.

The first final-script run took approximately 65 seconds; the changed-position run approximately 47 seconds. Runtime varies with planning and rendering load.

Build: all six workspace packages compiled on Jazzy. Python scripts and launch files were syntax checked; shell scripts were checked with `bash -n`.

Full runtime logs and sampled object trajectories remain on the server in `/root/gpufree-data/cloudgrasp_ws/logs/`. They are not included in the source patch.

Negative test: move the target outside the camera field of view to (0.90, 0.60, 0.025). The system reported `No graspable box found in camera point cloud`, stopped before the pregrasp stage, and `pick.sh` returned exit code 1. The cube was reset to the normal initial position afterward.

## 2026-09-06: restart and stalled-grasp repair

- Observed failure: Gazebo world had no robot, controllers were unavailable,
  ROS clock was stale, and an orphan grasp process retained the old shell lock.
- Added explicit spawn world, per-run Gazebo partition, world-specific clock
  bridge, bounded readiness checks, process-group shutdown, and a Python grasp
  supervisor whose lock descriptor is not inherited by children.
- Incremental `colcon build --symlink-install --packages-select cloudgrasp_sim`
  passed; Python syntax, shell syntax, and `git diff --check` passed.
- Paused-simulation negative check: pick exited 1 after the 15-second readiness
  timeout without sending a grasp action; simulation then resumed.
- Full simulated physical grasp passed: peak cube height 0.204853 m; final
  position (0.449953, -0.249499, 0.025000) m. Motion and Gazebo displacement
  both passed. No remaining grasp/watcher process; exclusive lock released.

- Final managed stop/start passed readiness. A new grasp was already running when reset was requested; reset correctly refused to interfere.

## Learning-session orphan-server regression

A Gazebo server survived after its launch leader exited. A later session's
motion report succeeded while its observed cube did not move (physical_pass=false).
Manager now discovers leftover servers by this workspace's exact world path and
its generated GZ_PARTITION process-group marker before starting another session.
After removal and restart, physical grasp passed: peak 0.204463 m, final
(0.449927, -0.249607, 0.025000) m. Cube reset for the learner.
