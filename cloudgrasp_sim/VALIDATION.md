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
