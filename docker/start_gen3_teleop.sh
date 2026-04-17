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
import os


pkg_parent = "/root/ros2_ws/src/lerobot-ros"
sys.path.insert(0, pkg_parent)


import lerobot_robot_ros.config   # registriert Subklassen
from lerobot_robot_ros.robot import KinovaGen3, SO101ROS, AnninAR4, ROS2Robot

import lerobot_teleoperator_devices.config_keyboard_joint
from lerobot_teleoperator_devices.keyboard_joint import KeyboardJointTeleop

from lerobot.utils.import_utils import register_third_party_plugins
register_third_party_plugins()

from lerobot.scripts.lerobot_teleoperate import main

sys.argv = [
    "lerobot-teleoperate",
    "--robot.type", "kinova_gen3",
    "--robot.id", "gen3",
    "--robot.ros2_interface.namespace", "",
    "--teleop.type", "keyboard_joint",
    "--teleop.id", "keyboard",
    "--teleop.arm_action_keys", "['joint_1.pos', 'joint_2.pos', 'joint_3.pos', 'joint_4.pos', 'joint_5.pos', 'joint_6.pos', 'joint_7.pos']",
    "--teleop.gripper_action_key", "gripper.pos",
    "--display_data", "false",
]

main()
EOF
