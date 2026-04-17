#!/bin/bash
set -e

# ROS + Workspace sourcen
source /opt/ros/jazzy/setup.bash
source /root/ros2_ws/install/setup.bash
source /root/.bashrc

# Venv aktivieren
source /root/lerobot-venv/bin/activate

echo "Starting LeRobot Teleoperation (Kinova Gen3)..."

python3 - <<EOF
import sys

# Wichtig für Plugins
sys.path.insert(0, "/root/ros2_ws/src/lerobot-ros/lerobot_robot_ros")

import config
from lerobot.utils.import_utils import register_third_party_plugins
register_third_party_plugins()

from lerobot.scripts.lerobot_teleoperate import main

sys.argv = [
    "lerobot-teleoperate",

    "--robot.type", "kinova_gen3",
    "--robot.id", "gen3",

    "--teleop.type", "keyboard",
    "--teleop.id", "keyboard",

    "--display_data", "false",
]

main()
EOF
