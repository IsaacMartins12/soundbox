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

# Clonar o repositório motoman para pegar o URDF do GP88
RUN git clone --depth 1 https://github.com/ros-industrial/motoman.git /tmp/motoman && \
    mkdir -p /ros2_ws/src/gp88_description && \
    cp -r /tmp/motoman/motoman_gp88_support/* /ros2_ws/src/gp88_description/ 2>/dev/null || \
    echo "GP88 support not found, will use GP7 as fallback" && \
    cp -r /tmp/motoman/motoman_gp7_support/* /ros2_ws/src/gp88_description/ 2>/dev/null || true && \
    rm -rf /tmp/motoman

# Criar workspace
RUN mkdir -p /ros2_ws/src
WORKDIR /ros2_ws

# Copiar pacotes
COPY src/ /ros2_ws/src/

# Build do workspace
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --symlink-install 2>/dev/null || true"

# Source automático
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "source /ros2_ws/install/setup.bash 2>/dev/null || true" >> ~/.bashrc

# Variáveis de ambiente para GUI
ENV DISPLAY=host.docker.internal:0.0
ENV QT_X11_NO_MITSHM=1
ENV LIBGL_ALWAYS_INDIRECT=1

CMD ["/bin/bash"]
