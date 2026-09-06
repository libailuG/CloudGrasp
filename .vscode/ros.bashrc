# ROS environment for new terminals in this project.
if [[ -f "$HOME/.bashrc" ]]; then source "$HOME/.bashrc"; fi
source /opt/ros/jazzy/setup.bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/install/setup.bash"

# CloudGrasp terminal colors: cyan command input, default program output.
if [[ $- == *i* ]]; then
  PS1='\n\[\e[1;32m\][CloudGrasp \W]\[\e[0m\]\n\[\e[1;36m\]➜ '
  PS2='\[\e[1;36m\]… '
  PS0=$'\e[0m'
fi
