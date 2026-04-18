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

import logging
import threading
import time

import rclpy
from builtin_interfaces.msg import Duration
from control_msgs.action import GripperCommand
from lerobot.utils.errors import DeviceNotConnectedError
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import Executor, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.publisher import Publisher
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from .config import ActionType, GripperActionType, ROS2InterfaceConfig
from .moveit_servo import MoveIt2Servo

logger = logging.getLogger(__name__)


class ROS2Interface:
    """Class to interface with a MoveIt2 manipulator."""

    def __init__(self, config: ROS2InterfaceConfig, action_type: ActionType):
        self.config = config
        self.action_type = action_type
        self.robot_node: Node | None = None
        self.pos_cmd_pub: Publisher | None = None
        self.traj_cmd_pub: Publisher | None = None
        self.gripper_action_client: ActionClient | None = None
        self.gripper_traj_pub: Publisher | None = None
        self.executor: Executor | None = None
        self.moveit2_servo: MoveIt2Servo | None = None
        self.executor_thread: threading.Thread | None = None
        self.is_connected = False
        self._last_joint_state: dict[str, dict[str, float]] | None = None
        # ADDED: Keep track of the last sent goal to avoid spamming the Action Server
        self._last_gripper_goal: float | None = None

    def connect(self) -> None:
        if not rclpy.ok():
            rclpy.init()

        self.robot_node = Node(
            "moveit2_interface_node", namespace=self.config.namespace
        )
        if self.action_type == ActionType.JOINT_POSITION:
            self.pos_cmd_pub = self.robot_node.create_publisher(
                Float64MultiArray, "/position_controller/commands", 10
            )
        elif self.action_type == ActionType.JOINT_TRAJECTORY:
            self.traj_cmd_pub = self.robot_node.create_publisher(
                JointTrajectory, "/joint_trajectory_controller/joint_trajectory", 10
            )
        elif self.action_type == ActionType.CARTESIAN_VELOCITY:
            self.moveit2_servo = MoveIt2Servo(
                node=self.robot_node,
                frame_id=self.config.base_link,
                callback_group=ReentrantCallbackGroup(),
            )

        if self.config.gripper_action_type == GripperActionType.TRAJECTORY:
            self.gripper_traj_pub = self.robot_node.create_publisher(
                JointTrajectory, "/gripper_controller/joint_trajectory", 10
            )
        else:
            gripper_action_topic = getattr(
                self.config, "gripper_action_topic", "/gripper_controller/gripper_cmd"
            )
            self.gripper_action_client = ActionClient(
                self.robot_node,
                GripperCommand,
                gripper_action_topic,
                callback_group=ReentrantCallbackGroup(),
            )
            self._goal_msg = GripperCommand.Goal()

        self.joint_state_sub = self.robot_node.create_subscription(
            JointState,
            "joint_states",
            self._joint_state_callback,
            10,
        )

        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.robot_node)
        self.executor_thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.executor_thread.start()

        start_time = time.time()
        while self._last_joint_state is None and time.time() - start_time < 10.0:
            time.sleep(0.1)

        if self._last_joint_state is None:
            logger.warning("No joint state received within 10 seconds.")
        else:
            logger.info(
                f"Joint state received: {list(self._last_joint_state.get('position', {}).keys())}"
            )

        self.is_connected = True

    def send_joint_position_command(
        self, joint_positions: list[float], unnormalize: bool = True
    ) -> None:
        if not self.robot_node:
            raise DeviceNotConnectedError(
                "ROS2Interface is not connected. You need to call `connect()`."
            )

        if unnormalize:
            if (
                self.config.min_joint_positions is None
                or self.config.max_joint_positions is None
            ):
                raise ValueError(
                    "Joint position normalization requires min and max joint positions to be set."
                )
            joint_positions = [
                min(max(pos, min_pos), max_pos)
                for pos, min_pos, max_pos in zip(
                    joint_positions,
                    self.config.min_joint_positions,
                    self.config.max_joint_positions,
                    strict=True,
                )
            ]

        if len(joint_positions) != len(self.config.arm_joint_names):
            raise ValueError(
                f"Expected {len(self.config.arm_joint_names)} joint positions, but got {len(joint_positions)}."
            )

        if self.action_type == ActionType.JOINT_TRAJECTORY:
            if self.traj_cmd_pub is None:
                raise DeviceNotConnectedError(
                    "Trajectory command publisher is not initialized."
                )

            msg = JointTrajectory()
            msg.header.stamp = self.robot_node.get_clock().now().to_msg()
            msg.joint_names = self.config.arm_joint_names

            point = JointTrajectoryPoint()
            point.positions = [float(p) for p in joint_positions]
            point.time_from_start = Duration(sec=0, nanosec=100_000_000)

            msg.points = [point]
            self.traj_cmd_pub.publish(msg)
        else:
            if self.pos_cmd_pub is None:
                raise DeviceNotConnectedError(
                    "Position command publisher is not initialized."
                )
            msg = Float64MultiArray()
            msg.data = joint_positions
            self.pos_cmd_pub.publish(msg)

    def servo(self, linear, angular, normalize: bool = True) -> None:
        if not self.moveit2_servo:
            raise DeviceNotConnectedError(
                "ROS2Interface is not connected. You need to call `connect()`."
            )

        if normalize:
            linear = [v * self.config.max_linear_velocity for v in linear]
            angular = [v * self.config.max_angular_velocity for v in angular]
        self.moveit2_servo.servo(linear=linear, angular=angular)

    def send_gripper_command(self, position: float, unnormalize: bool = True) -> bool:
        if not self.robot_node:
            raise DeviceNotConnectedError(
                "ROS2Interface is not connected. You need to call `connect()`."
            )

        if unnormalize:
            open_pos = self.config.gripper_open_position
            closed_pos = self.config.gripper_close_position
            gripper_goal = open_pos + position * (closed_pos - open_pos)
        else:
            gripper_goal = position

        if self.config.gripper_action_type == GripperActionType.TRAJECTORY:
            if self.gripper_traj_pub is None:
                raise DeviceNotConnectedError(
                    "Gripper command publisher is not initialized."
                )

            msg = JointTrajectory()
            msg.header.stamp = self.robot_node.get_clock().now().to_msg()
            msg.joint_names = [self.config.gripper_joint_name]

            point = JointTrajectoryPoint()
            point.positions = [float(gripper_goal)]
            point.time_from_start = Duration(sec=0, nanosec=100_000_000)

            msg.points = [point]
            self.gripper_traj_pub.publish(msg)
            return True
        else:
            if not self.gripper_action_client:
                raise DeviceNotConnectedError(
                    "Gripper action client is not initialized."
                )

            if not self.gripper_action_client.server_is_ready():
                return False

            # ADDED: Prevent spamming! Only send if the goal has changed by a small threshold
            if (
                self._last_gripper_goal is not None
                and abs(self._last_gripper_goal - gripper_goal) < 1e-4
            ):
                return True

            self._last_gripper_goal = float(gripper_goal)
            self._goal_msg.command.position = float(gripper_goal)
            self.gripper_action_client.send_goal_async(self._goal_msg)
            return True

    @property
    def joint_state(self) -> dict[str, dict[str, float]] | None:
        return self._last_joint_state

    def _joint_state_callback(self, msg: "JointState") -> None:
        self._last_joint_state = self._last_joint_state or {}
        positions = {}
        velocities = {}
        name_to_index = {name: i for i, name in enumerate(msg.name)}

        for joint_name in self.config.arm_joint_names:
            idx = name_to_index.get(joint_name)
            if idx is not None:
                positions[joint_name] = msg.position[idx]
                velocities[joint_name] = msg.velocity[idx]
            else:
                if not hasattr(self, "_warned_missing_joint_state"):
                    self._warned_missing_joint_state = set()
                if joint_name not in self._warned_missing_joint_state:
                    logger.warning(
                        f"Joint '{joint_name}' not found in joint state message."
                    )
                    self._warned_missing_joint_state.add(joint_name)

        if self.config.gripper_joint_name:
            idx = name_to_index.get(self.config.gripper_joint_name)
            if idx is not None:
                positions[self.config.gripper_joint_name] = msg.position[idx]
                velocities[self.config.gripper_joint_name] = msg.velocity[idx]
            else:
                if not hasattr(self, "_warned_missing_gripper_state"):
                    logger.warning(
                        f"Gripper joint '{self.config.gripper_joint_name}' not found in joint state message."
                    )
                    self._warned_missing_gripper_state = True

        if positions:
            self._last_joint_state["position"] = positions
            self._last_joint_state["velocity"] = velocities

    def disconnect(self):
        if self.joint_state_sub:
            self.joint_state_sub.destroy()
            self.joint_state_sub = None
        if self.pos_cmd_pub:
            self.pos_cmd_pub.destroy()
            self.pos_cmd_pub = None
        if self.traj_cmd_pub:
            self.traj_cmd_pub.destroy()
            self.traj_cmd_pub = None
        if self.gripper_action_client:
            self.gripper_action_client.destroy()
            self.gripper_action_client = None
        if self.gripper_traj_pub:
            self.gripper_traj_pub.destroy()
            self.gripper_traj_pub = None
        if self.robot_node:
            self.robot_node.destroy_node()
            self.robot_node = None
        if self.moveit2_servo:
            self.moveit2_servo = None

        if self.executor:
            self.executor.shutdown()
            self.executor = None
        if self.executor_thread:
            self.executor_thread.join()
            self.executor_thread = None

        self.is_connected = False
