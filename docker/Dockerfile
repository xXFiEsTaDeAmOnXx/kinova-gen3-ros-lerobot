FROM ros:jazzy-perception-noble

ENV ROS_WS=/root/ros2_ws
ENV VENV_PATH=/root/lerobot-venv
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR ${ROS_WS}

# System dependencies
RUN apt-get update && apt-get install -y \
  python3-pip \
  python3-venv \
  python3-full \
  git \
  libglib2.0-0 \
  libgl1 \
  libstdc++6 \
  ros-jazzy-moveit-msgs \
  ros-jazzy-moveit-servo \
  ros-jazzy-control-msgs \
  ros-jazzy-trajectory-msgs \
  ros-jazzy-geometry-msgs \
  ros-jazzy-sensor-msgs \
  ros-jazzy-std-msgs \
  ros-jazzy-std-srvs \
  && rm -rf /var/lib/apt/lists/*

# Copy source
COPY lerobot-ros ${ROS_WS}/src/lerobot-ros

# --system-site-packages: venv sieht rclpy & andere ROS-Python-Pakete aus apt
RUN python3 -m venv --system-site-packages ${VENV_PATH}

# pip upgraden
RUN pip install --upgrade pip setuptools wheel

# lerobot-ros installieren — zieht automatisch lerobot>=0.4.0,<0.5.0 mit rein
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install \
  -e ${ROS_WS}/src/lerobot-ros/lerobot_robot_ros \
  -e ${ROS_WS}/src/lerobot-ros/lerobot_teleoperator_devices

# ROS2 Workspace bauen (braucht ROS sourced)
RUN bash -c "\
  source /opt/ros/jazzy/setup.bash && \
  cd ${ROS_WS} && \
  colcon build --symlink-install"

WORKDIR ${ROS_WS}

COPY docker/start_gen3_teleop.sh /root/start_gen3_teleop.sh

# Executable machen
RUN chmod +x /root/start_gen3_teleop.sh

