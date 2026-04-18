FROM ros:jazzy-perception-noble

ENV ROS_WS=/root/ros2_ws
ENV VENV_PATH=/root/lerobot-venv
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR ${ROS_WS}

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

COPY lerobot-ros ${ROS_WS}/src/lerobot-ros

RUN python3 -m venv --system-site-packages ${VENV_PATH}

RUN pip install --upgrade pip setuptools wheel

RUN --mount=type=cache,target=/root/.cache/pip \
  pip install \
  -e ${ROS_WS}/src/lerobot-ros/lerobot_robot_ros \
  -e ${ROS_WS}/src/lerobot-ros/lerobot_teleoperator_devices

RUN bash -c "\
  source /opt/ros/jazzy/setup.bash && \
  cd ${ROS_WS} && \
  colcon build --symlink-install"

WORKDIR ${ROS_WS}

COPY docker/start_gen3_teleop.sh /start_gen3_teleop.sh

RUN chmod +x /start_gen3_teleop.sh

