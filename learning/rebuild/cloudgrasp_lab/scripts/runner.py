"""Foreground session owner: Ctrl+C cleans the entire launch process group."""
import fcntl,os,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];R=BASE/'.runtime';R.mkdir(exist_ok=True)
PID=R/'runner.pid'

def members(group):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            f=(p/'stat').read_text().rsplit(')',1)[1].split()
            if int(f[2])==group and f[0]!='Z':found.append(int(p.name))
        except (OSError,ValueError):pass
    return found

def cleanup(group):
    for sig,seconds in [(signal.SIGINT,4),(signal.SIGTERM,3),(signal.SIGKILL,2)]:
        try:os.killpg(group,sig)
        except ProcessLookupError:return
        end=time.monotonic()+seconds
        while members(group) and time.monotonic()<end:time.sleep(.1)
        if not members(group):return
    raise RuntimeError('Simulation group did not stop')

if len(sys.argv)<2:raise SystemExit('Specify stage 1..7 or stop')
if sys.argv[1]=='stop':
    if not PID.exists():raise SystemExit('No lab runner pid file; use Ctrl+C in the lab launch terminal if needed')
    pid=int(PID.read_text());p=Path(f'/proc/{pid}/cmdline')
    if p.exists() and str(HERE/'runner.py').encode() in p.read_bytes():
        os.kill(pid,signal.SIGINT);print('Stop requested; wait for LAB_STOPPED in the launch terminal.')
    else:print('Lab runner is no longer running.')
    raise SystemExit(0)
stage=int(sys.argv[1])
if stage not in range(1,8):raise SystemExit('stage must be 1..7')
lock=(R/'session.lock').open('w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit('A lab is already running. Stop it before changing stages.')
# An abruptly killed owner can leave a launch group: verify its exact command before cleanup.
launch_pid=R/'launch.pid'
if launch_pid.exists():
    group=int(launch_pid.read_text())
    for pid in members(group):
        try:cmd=Path(f'/proc/{pid}/cmdline').read_bytes();env=Path(f'/proc/{pid}/environ').read_bytes()
        except OSError:continue
        if b'GZ_PARTITION=cloudgrasp_lab_' in env and (b'cloudgrasp_lab' in cmd or b'01_table.sdf' in cmd):
            cleanup(group);break
PID.write_text(str(os.getpid()))
proc=None
signal.signal(signal.SIGTERM,lambda s,f:(_ for _ in ()).throw(KeyboardInterrupt()))
try:
    with (R/'sim.log').open('w') as log:
        proc=subprocess.Popen(['ros2','launch','cloudgrasp_lab','lab.launch.py',f'stage:={stage}',*sys.argv[2:]],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    launch_pid.write_text(str(proc.pid))
    print('Starting stage',stage,'Log:',R/'sim.log',flush=True)
    subprocess.run(['/usr/bin/python3',str(HERE/'ready.py'),str(stage)],check=True)
    print('Keep this terminal open. Ctrl+C stops the lab. Use another terminal for exercises.',flush=True)
    result=proc.wait()
    if result:raise SystemExit(result)
except KeyboardInterrupt:pass
finally:
    if proc is not None:cleanup(proc.pid);proc.wait()
    PID.unlink(missing_ok=True);launch_pid.unlink(missing_ok=True)
    print('LAB_STOPPED',flush=True)
