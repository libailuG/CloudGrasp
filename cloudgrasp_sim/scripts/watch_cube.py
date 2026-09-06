#!/usr/bin/python3
"""Record Gazebo ground truth for validation only; never used by the grasp planner."""
import json, re, subprocess, sys, time, threading, signal
from pathlib import Path
seconds=float(sys.argv[1]) if len(sys.argv)>1 else 90
output=Path(sys.argv[2]) if len(sys.argv)>2 else Path('/tmp/cloudgrasp-cube.json')
p=subprocess.Popen(['gz','topic','-e','-t','/world/cloudgrasp/dynamic_pose/info'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
timer=threading.Timer(seconds,p.terminate);timer.start()
def stop(signum,frame):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
samples=[];target=False;position=False;values={};start=time.monotonic();last=0
try:
 for line in p.stdout:
  line=line.strip()
  if line.startswith('name:'):target=line=='name: "target_cube"'
  if target and line=='position {':position=True;values={}
  elif position and line=='}':
   position=False;target=False;t=time.monotonic()-start
   if t-last>=.1:
    samples.append({'t':round(t,3),**{k:values.get(k,0.) for k in ['x','y','z']}});last=t
  elif position:
   m=re.fullmatch(r'([xyz]): (.*)',line)
   if m:values[m[1]]=float(m[2])
except KeyboardInterrupt:
 pass
finally:
 timer.cancel();p.terminate();p.wait()
report={'samples':samples,'count':len(samples)}
if samples:
 report.update(initial=samples[0],final=samples[-1],max_height=max(s['z'] for s in samples),lifted=max(s['z'] for s in samples)>samples[0]['z']+.08)
output.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
