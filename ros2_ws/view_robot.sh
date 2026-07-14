#!/bin/bash
source /opt/ros/humble/setup.bash

# Matar processos anteriores
pkill -f robot_state_publisher 2>/dev/null
pkill -f joint_state_publisher 2>/dev/null
pkill -f rviz2 2>/dev/null
sleep 1

# Gerar URDF se não existir
if [ ! -s /tmp/gp88.urdf ]; then
    bash /tmp/gen_urdf.sh
fi

# Publicar o robot_description via parâmetro de arquivo
ros2 run robot_state_publisher robot_state_publisher \
    --ros-args -p robot_description:="$(cat /tmp/gp88.urdf)" \
    -p use_sim_time:=false &

sleep 2

# Verificar se publicou
echo "=== Checando TF ==="
ros2 topic echo /tf_static --once --no-daemon &
TFPID=$!
sleep 3
kill $TFPID 2>/dev/null

# Joint state publisher (sem GUI pra evitar problemas X11)
ros2 run joint_state_publisher joint_state_publisher &

sleep 1

echo "=== Nós ativos ==="
ros2 node list

echo ""
echo "=== Para visualizar, abra RViz em outro terminal ==="
echo "docker exec -e DISPLAY=host.docker.internal:0.0 soundbox_ros2 bash -c 'source /opt/ros/humble/setup.bash && rviz2 -d /tmp/robot_view.rviz'"

# Manter rodando
wait
