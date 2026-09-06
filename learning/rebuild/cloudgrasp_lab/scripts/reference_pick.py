# Stage 07 supervisor: runs the independent lab_task executable adapted from the validated reference.
# Build your own task orchestration alongside it, then compare physical results.
#!/usr/bin/python3
"""Supervise a grasp without leaking ROS children or the exclusive lock."""
import fcntl
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WS = ROOT.parents[1]
LOG = HERE.parents[1] / '.runtime'
LOG.mkdir(exist_ok=True)

def interrupt(signum, frame):
    raise KeyboardInterrupt

def stop_group(process):
    if process is None:
        return
    # Every launch below is created with start_new_session=True.
    for sig, delay in [(signal.SIGINT, 1.), (signal.SIGTERM, 1.), (signal.SIGKILL, .1)]:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        time.sleep(delay)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

def main():
    with (LOG / 'pick.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('A grasp is already running.', flush=True)
            return 1
        # Python file descriptors are non-inheritable; children cannot retain this lock.
        if subprocess.call(['/usr/bin/python3', str(HERE / 'ready.py'), '7', '--timeout', '15']):
            return 1
        run = LOG / time.strftime('pick-%Y%m%d-%H%M%S')
        report_path = Path(str(run) + '.json')
        launch = watcher = None
        completed = False
        returncode = 1
        try:
            with Path(str(run) + '-monitor.log').open('w') as monitor, Path(str(run) + '.log').open('w') as log:
                watcher = subprocess.Popen(['/usr/bin/python3', str(ROOT / 'cloudgrasp_sim/scripts/watch_cube.py'), '300', str(report_path)], stdout=monitor, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
                launch = subprocess.Popen(['ros2', 'launch', 'cloudgrasp_lab', 'task.launch.py', *sys.argv[1:]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, start_new_session=True)
                deadline = time.monotonic() + 240
                with selectors.DefaultSelector() as selector:
                    selector.register(launch.stdout, selectors.EVENT_READ)
                    while time.monotonic() < deadline:
                        if not selector.select(timeout=.5):
                            if launch.poll() is not None:
                                break
                            continue
                        line = launch.stdout.readline()
                        if not line:
                            break
                        print(line, end='', flush=True)
                        log.write(line)
                        log.flush()
                        completed |= 'MOTION_SEQUENCE_COMPLETE' in line
                    else:
                        print('FAILED: grasp exceeded the 240-second wall-time limit.', flush=True)
                if launch.poll() is None and completed:
                    try:
                        launch.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                returncode = launch.poll()
        except KeyboardInterrupt:
            print('\nGrasp interrupted; stopping its ROS processes.', flush=True)
        finally:
            stop_group(launch)
            if watcher is not None:
                watcher.terminate()
                try:
                    watcher.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    watcher.kill()
                    watcher.wait()
        if not completed or returncode != 0:
            print(f'Motion failed. Log: {run}.log', flush=True)
            return 1
        try:
            report = json.loads(report_path.read_text())
        except (OSError, ValueError) as error:
            print(f'Physical verification unavailable: {error}', flush=True)
            return 1
        final, initial = report.get('final', {}), report.get('initial', {})
        passed = bool(report.get('lifted')) and abs(final.get('y', 999)+.25)<.03 and abs(final.get('x',999)-initial.get('x',0))<.03 and abs(final.get('z',999)-.025)<.015
        report['physical_pass'] = passed
        report_path.write_text(json.dumps(report, indent=2))
        print('PHYSICAL_PICK_PLACE_PASS' if passed else 'PHYSICAL_PICK_PLACE_FAILED', flush=True)
        print('Peak height:', report.get('max_height'), 'Final:', final, 'Report:', report_path, flush=True)
        return 0 if passed else 1

if __name__ == '__main__':
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
