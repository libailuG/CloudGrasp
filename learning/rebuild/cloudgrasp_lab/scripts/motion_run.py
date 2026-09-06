"""Propagate executable-level failures even when ros2 launch exits successfully."""
import subprocess,sys
from pathlib import Path
subprocess.run([sys.executable,str(Path(__file__).with_name("scene.py")),"table"],check=True)
p=subprocess.Popen(['ros2','launch','cloudgrasp_lab','motion.launch.py',*sys.argv[1:]],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
planned=executed=False
try:
    for line in p.stdout:
        print(line,end='',flush=True)
        planned |= 'PLAN_OK:' in line
        executed |= 'EXECUTION_OK' in line
    code=p.wait()
except KeyboardInterrupt:
    p.wait(timeout=8);raise
needs_execution=any(x.lower()=='execute:=true' for x in sys.argv[1:])
raise SystemExit(0 if code==0 and planned and (executed or not needs_execution) else 1)
