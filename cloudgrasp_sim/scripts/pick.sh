#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
set +u
source /opt/ros/jazzy/setup.bash
source "$WS/install/setup.bash"
set -u
mkdir -p "$WS/logs"
exec 9>"$WS/logs/pick.lock"
flock -n 9 || { echo 'A grasp is already running.'; exit 1; }
RUN="$WS/logs/pick-$(date +%Y%m%d-%H%M%S)"
/usr/bin/python3 "$SCRIPT_DIR/watch_cube.py" 300 "$RUN.json" > "$RUN-monitor.log" 2>&1 &
WATCH=$!
trap 'kill -TERM "$WATCH" 2>/dev/null || true' EXIT
ros2 launch cloudgrasp_sim pick.launch.py "$@" 2>&1 | tee "$RUN.log"
kill -TERM "$WATCH" 2>/dev/null || true
wait "$WATCH" || true
trap - EXIT
grep -q 'MOTION_SEQUENCE_COMPLETE' "$RUN.log" || { echo "Motion failed. Log: $RUN.log"; exit 1; }
/usr/bin/python3 - "$RUN.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);r=json.loads(p.read_text());f=r.get('final',{});i=r.get('initial',{})
ok=r.get('lifted',False) and abs(f.get('y',999)+.25)<.03 and abs(f.get('x',999)-i.get('x',0))<.03 and abs(f.get('z',999)-.025)<.015
r['physical_pass']=ok;p.write_text(json.dumps(r,indent=2))
print('PHYSICAL_PICK_PLACE_PASS' if ok else 'PHYSICAL_PICK_PLACE_FAILED')
print('Peak height:',r.get('max_height'),'Final:',f,'Report:',p)
sys.exit(0 if ok else 1)
PY
