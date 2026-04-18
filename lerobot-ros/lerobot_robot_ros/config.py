# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from dataclasses import dataclass, field
from enum import Enum

from lerobot.cameras import CameraConfig
from lerobot.robots import RobotConfig


class ActionType(Enum):
    CARTESIAN_VELOCITY = "cartesian_velocity"
    JOINT_POSITION = "joint_position"
    JOINT_TRAJECTORY = "joint_trajectory"


class GripperActionType(Enum):
    TRAJECTORY = "trajectory"  # Use JointTrajectoryController for gripper
    ACTION = "action"  # Use GripperActionClient


@dataclass
class ROS2InterfaceConfig:
    namespace: str = ""

    arm_joint_names: list[str] = field(
        default_factory=lambda: [
            "joint_1",
            "joint_2",
            "joint_3",
            "joint_4",
            "joint_5",
            "joint_6",
        ]
    )
    gripper_joint_name: str = "gripper_joint"

    base_link: str = "base_link"

    max_linear_velocity: float = 0.10
    max_angular_velocity: float = 0.25

    min_joint_positions: list[float] | None = None
    max_joint_positions: list[float] | None = None

    gripper_open_position: float = 0.0
    gripper_close_position: float = 1.0

    gripper_action_type: GripperActionType = GripperActionType.TRAJECTORY


@dataclass
class AnninAR4ROS2InterfaceConfig(ROS2InterfaceConfig):
    """Annin Robotics AR4 robot configuration - extends ROS2Config with
    AR4-specific settings
    """

    action_type: ActionType = ActionType.CARTESIAN_VELOCITY

    ros2_interface: ROS2InterfaceConfig = field(
        default_factory=lambda: ROS2InterfaceConfig(
            gripper_joint_name="gripper_jaw1_joint",
            base_link="base_link",
            min_joint_positions=[-2.9671, -0.7330, -1.5533, -2.8798, -1.8326, -2.7053],
            max_joint_positions=[2.9671, 1.5708, 0.9076, 2.8798, 1.8326, 2.7053],
            gripper_open_position=0.014,
            gripper_close_position=0.0,
            gripper_action_type=GripperActionType.ACTION,
        ),
    )


@dataclass
class SO101ROSInterfaceConfig(ROS2InterfaceConfig):
    """Configuration for the ROS 2 version of SO101: https://github.com/Pavankv92/lerobot_ws."""

    action_type: ActionType = ActionType.JOINT_TRAJECTORY

    ros2_interface: ROS2InterfaceConfig = field(
        default_factory=lambda: ROS2InterfaceConfig(
            arm_joint_names=["1", "2", "3", "4", "5"],
            gripper_joint_name="6",
            base_link="base",
            min_joint_positions=[-1.91986, -1.74533, -1.74533, -1.65806, -2.79253],
            max_joint_positions=[1.91986, 1.74533, 1.5708, 1.65806, 2.79253],
            gripper_open_position=1.74533,
            gripper_close_position=0.0,
        ),
    )


@dataclass
class KinovaGen3ROS2InterfaceConfig(ROS2InterfaceConfig):
    arm_joint_names: list[str] = field(
        default_factory=lambda: [
            "joint_1",
            "joint_2",
            "joint_3",
            "joint_4",
            "joint_5",
            "joint_6",
            "joint_7",
        ]
    )

    gripper_joint_name: str = "finger_joint"
    base_link: str = "base_link"

    min_joint_positions: list[float] = field(
        default_factory=lambda: [
            -3.283,  # joint_1
            -2.25,  # joint_2
            -3.283,  # joint_3
            -2.58,  # joint_4
            -3.283,  # joint_5
            -2.10,  # joint_6
            -3.283,  # joint_7
        ]
    )

    max_joint_positions: list[float] = field(
        default_factory=lambda: [
            3.283,
            2.25,
            3.283,
            2.58,
            3.283,
            2.10,
            3.283,
        ]
    )

    gripper_open_position: float = 0.0
    gripper_close_position: float = 1.2
    gripper_action_type: GripperActionType = GripperActionType.ACTION
    gripper_action_topic: str = "/robotiq_gripper_controller/gripper_cmd"


@dataclass
class ROS2Config(RobotConfig):
    action_type: ActionType = ActionType.JOINT_POSITION
    max_relative_target: int | None = None
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    ros2_interface: ROS2InterfaceConfig = field(default_factory=ROS2InterfaceConfig)


@RobotConfig.register_subclass("annin_ar4_mk1")
@dataclass
class AnninAR4Config(ROS2Config):
    action_type: ActionType = ActionType.CARTESIAN_VELOCITY
    ros2_interface: AnninAR4ROS2InterfaceConfig = field(
        default_factory=AnninAR4ROS2InterfaceConfig
    )


@RobotConfig.register_subclass("so101_ros")
@dataclass
class SO101ROSConfig(ROS2Config):
    action_type: ActionType = ActionType.JOINT_TRAJECTORY
    ros2_interface: SO101ROSInterfaceConfig = field(
        default_factory=SO101ROSInterfaceConfig
    )


@RobotConfig.register_subclass("kinova_gen3")
@dataclass
class KinovaGen3Config(ROS2Config):
    action_type: ActionType = ActionType.JOINT_TRAJECTORY
    ros2_interface: KinovaGen3ROS2InterfaceConfig = field(
        default_factory=KinovaGen3ROS2InterfaceConfig
    )
