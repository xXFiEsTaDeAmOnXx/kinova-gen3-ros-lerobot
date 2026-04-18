# LeRobot ROS — Kinova Gen3

ROS 2 interface for the [LeRobot](https://github.com/huggingface/lerobot) framework, tested with the **Kinova Gen3** (7-DoF). Based on [ycheng517/lerobot-ros](https://github.com/ycheng517/lerobot-ros).

Supports joint trajectory control via `ros2_control` and gripper control via the Gripper Action Controller.

---

## Requirements

- Docker + Docker Compose
- Kinova Gen3 with a running ROS 2 stack (Gazebo simulation or real robot)

---

## Quickstart

### 1. Clone the repository

```bash
git clone <this-repo>
cd lerobot-ros
```

### 2. Build the Docker image

```bash
docker compose -f docker/docker-compose.yaml build
```

### 3. Start teleoperation

```bash
docker compose -f docker/docker-compose.yaml run --rm lerobot-ros /start_gen3_teleop.sh
```

---

## Key Bindings

| Keys   | Joint |
|--------|-------|
| Q / A  | Joint 1 |
| W / S  | Joint 2 |
| E / D  | Joint 3 |
| R / F  | Joint 4 |
| T / G  | Joint 5 |
| Y / H  | Joint 6 |
| U / J  | Joint 7 |
| O / L  | Gripper (close / open) |
| Ctrl+C | Quit |

---

## Supported Control Modes

**Arm**
- Joint Trajectory Control via `joint_trajectory_controller`
- Joint Position Control via `position_controllers`
- End-Effector Velocity Control via MoveIt Servo

**Gripper**
- Trajectory Control (`JointTrajectoryController`)
- Action Control (`GripperActionController`)

---

## Integrating Your Own Robot

Subclass `ROS2Robot` in `robot.py`:

```python
class MyRobot(ROS2Robot):
    pass
```

Add a matching config in `config.py`:

```python
@RobotConfig.register_subclass("my_ros2_robot")
@dataclass
class MyRobotConfig(ROS2Config):
    action_type: ActionType = ActionType.JOINT_TRAJECTORY
    ros2_interface: ROS2InterfaceConfig = field(
        default_factory=lambda: ROS2InterfaceConfig(
            base_link="base_link",
            arm_joint_names=["joint_1", "joint_2", "joint_3",
                             "joint_4", "joint_5", "joint_6"],
            gripper_joint_name="gripper_joint",
            gripper_open_position=0.0,
            gripper_close_position=1.0,
        )
    )
```

---

## Based on

- [ycheng517/lerobot-ros](https://github.com/ycheng517/lerobot-ros)
- [huggingface/lerobot](https://github.com/huggingface/lerobot)
