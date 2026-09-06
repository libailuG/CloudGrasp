#!/usr/bin/python3
"""Manage one simulation process group, including bounded startup/shutdown checks."""
from pathlib import Path
import fcntl
import os
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]
LOG = WS / 'logs'
LOG.mkdir(exist_ok=True)
PID = LOG / 'sim.pid'

def running():
    try:
        pid = int(PID.read_text())
        command = Path(f'/proc/{pid}/cmdline').read_bytes()
        if b'ros2' in command and b'cloudgrasp_sim' in command and b'sim.launch.py' in command:
            return pid
    except (OSError, ValueError):
        pass
    return None

def live_group(pgid):
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                return True
        except (OSError, ValueError, IndexError):
            continue
    return False

def stop_group(pid):
    if Path(f'/proc/{pid}').exists() and os.getpgid(pid) != pid:
        raise SystemExit('Refusing to stop a process outside its own simulation group.')
    for sig, seconds in [(signal.SIGINT, 6), (signal.SIGTERM, 4), (signal.SIGKILL, 2)]:
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            break
        deadline = time.monotonic() + seconds
        while live_group(pid) and time.monotonic() < deadline:
            time.sleep(.1)
        if not live_group(pid):
            break
    if live_group(pid):
        raise SystemExit('Simulation processes did not stop; refusing to start a second instance.')
    PID.unlink(missing_ok=True)

def cleanup_leftover_servers():
    # Only this workspace's Gazebo servers with our generated session marker.
    groups = set()
    world = str(WS / 'install/cloudgrasp_sim/share/cloudgrasp_sim/worlds/tabletop.sdf').encode()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / 'cmdline').read_bytes()
            if world not in command or b'gz' not in command:
                continue
            pgid = os.getpgid(int(entry.name))
            marker = f'GZ_PARTITION=cloudgrasp_{os.getuid()}_{pgid}_'.encode()
            if any(value.startswith(marker) for value in (entry / 'environ').read_bytes().split(b'\0')):
                groups.add(pgid)
        except (OSError, ValueError):
            continue
    for pgid in groups:
        print(f'Stopping leftover CloudGrasp simulation group {pgid}.', flush=True)
        stop_group(pgid)

def ready(seconds):
    return subprocess.call(['bash', str(HERE / 'ready.sh'), '--timeout', str(seconds)]) == 0

action = sys.argv[1] if len(sys.argv) > 1 else 'status'
with (LOG / 'sim-manager.lock').open('w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    if action == 'start':
        pid = running()
        if pid:
            print(f'Simulation process exists: PID {pid}; checking readiness...', flush=True)
            if not ready(8):
                raise SystemExit('Simulation is not ready. Run manage.py stop, then manage.py start.')
        else:
            cleanup_leftover_servers()
            with (LOG / 'sim.log').open('w') as out:
                process = subprocess.Popen(['bash', str(HERE / 'start.sh')], stdout=out,
                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            PID.write_text(str(process.pid))
            print('Starting Gazebo, robot, controllers and camera...', flush=True)
            if not ready(45):
                if process.poll() is None:
                    stop_group(process.pid)
                raise SystemExit('Startup failed. See ' + str(LOG / 'sim.log'))
            print('Simulation ready. You can run pick.sh.', flush=True)
    elif action == 'stop':
        pid = running()
        if pid:
            stop_group(pid)
            print('CloudGrasp stopped.')
        else:
            cleanup_leftover_servers()
            print('No managed simulation is running.')
    elif action == 'pick':
        if not running():
            raise SystemExit('Start the simulation first.')
        # pick.sh has its own readiness check and exclusive grasp lock.
        fcntl.flock(lock, fcntl.LOCK_UN)
        raise SystemExit(subprocess.call(['bash', str(HERE / 'pick.sh')]))
    elif action == 'status':
        print('Running: ' + str(running()) if running() else 'Stopped')
    else:
        raise SystemExit('Usage: manage.py start|stop|pick|status')
