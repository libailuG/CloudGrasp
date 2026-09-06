#!/usr/bin/python3
"""Lifecycle manager for this CloudGrasp workspace only."""
from pathlib import Path
import os, signal, subprocess, sys, time
HERE=Path(__file__).resolve().parent
WS=HERE.parents[3]
LOG=WS/'logs';LOG.mkdir(exist_ok=True)
PID=LOG/'sim.pid'
def running():
    try:
        pid=int(PID.read_text())
        command=Path(f'/proc/{pid}/cmdline').read_bytes()
        if b'ros2' in command and b'cloudgrasp_sim' in command and b'sim.launch.py' in command:
            return pid
    except (OSError,ValueError):pass
    return None
action=sys.argv[1] if len(sys.argv)>1 else 'status'
if action=='start':
    if running():print(f'Simulation already running: PID {running()}')
    else:
        with (LOG/'sim.log').open('w') as out:
            p=subprocess.Popen(['bash',str(HERE/'start.sh')],stdout=out,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        PID.write_text(str(p.pid));time.sleep(3)
        if p.poll() is not None:raise SystemExit('Startup failed. See '+str(LOG/'sim.log'))
        print('Gazebo and RViz started. Wait for the robot and point cloud before picking.')
elif action=='stop':
    pid=running()
    if pid:
        os.killpg(pid,signal.SIGINT)
        time.sleep(4)
        try:os.killpg(pid,signal.SIGTERM)
        except ProcessLookupError:pass
        PID.unlink(missing_ok=True);print('CloudGrasp stopped.')
    else:print('No managed simulation is running.')
elif action=='pick':
    if not running():raise SystemExit('Start the simulation first.')
    raise SystemExit(subprocess.call(['bash',str(HERE/'pick.sh')]))
elif action=='status':print('Running: '+str(running()) if running() else 'Stopped')
else:raise SystemExit('Usage: manage.py start|stop|pick|status')
