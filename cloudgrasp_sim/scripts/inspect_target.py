#!/usr/bin/python3
# Gazebo ground truth is used only for evaluation, never to plan grasp motion.
import subprocess,json
r=subprocess.run(['gz','model','-m','target_cube','--pose'],text=True,capture_output=True,timeout=10)
print(r.stdout);print(r.stderr)
raise SystemExit(r.returncode)
