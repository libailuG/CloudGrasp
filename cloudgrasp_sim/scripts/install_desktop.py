#!/usr/bin/python3
from pathlib import Path
root=Path(__file__).resolve().parent
desktop=Path.home()/'Desktop';desktop.mkdir(exist_ok=True)
for action,label,icon in [('start','Start Simulation','applications-engineering'),('pick','Run Pick and Place','media-playback-start'),('stop','Stop Simulation','media-playback-stop')]:
 p=desktop/f'cloudgrasp-{action}.desktop'
 p.write_text(f'[Desktop Entry]\nType=Application\nName=CloudGrasp - {label}\nExec=xfce4-terminal --hold --command="/usr/bin/python3 {root}/manage.py {action}"\nIcon={icon}\nTerminal=false\nStartupNotify=false\n');p.chmod(0o755)
p=desktop/'cloudgrasp-reset.desktop';p.write_text(f'[Desktop Entry]\nType=Application\nName=CloudGrasp - Reset Cube\nExec=xfce4-terminal --hold --command="bash {root}/reset_cube.sh"\nIcon=view-refresh\nTerminal=false\n');p.chmod(0o755)
