FROM osrf/ros:humble-desktop-full

# Instalar dependências adicionais
RUN apt-get update && apt-get install -y \
    ros-humble-moveit \
    ros-humble-ros2-control \
    ros-humble-ros2-controllers \
    ros-humble-gazebo-ros2-control \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-joint-state-publisher-gui \
    ros-humble-xacro \
    ros-humble-robot-state-publisher \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
RUN pip3 install requests numpy

# Criar workspace
RUN mkdir -p /ros2_ws/src
WORKDIR /ros2_ws

# Copiar pacotes
COPY src/ /ros2_ws/src/

# Build do workspace
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --symlink-install"

# Source automático
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "source /ros2_ws/install/setup.bash" >> ~/.bashrc

# Variáveis de ambiente para GUI (necessário para Gazebo/RViz via X11)
ENV DISPLAY=host.docker.internal:0
ENV QT_X11_NO_MITSHM=1

CMD ["/bin/bash"]
