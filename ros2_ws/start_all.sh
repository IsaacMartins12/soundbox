#!/bin/bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash 2>/dev/null

echo "=== Gerando URDF do GP88 ==="
bash /tmp/gen_urdf.sh

echo ""
echo "=== Iniciando Foxglove Bridge (porta 8765) ==="
ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765 &
sleep 2

echo ""
echo "=== Iniciando Robot State Publisher ==="
ros2 launch /tmp/robot_launch.py &
sleep 2

echo ""
echo "=== Iniciando Coordinate Publisher (caixas) ==="
ros2 run soundbox_palletizer coordinate_publisher &
sleep 2

echo ""
echo "============================================="
echo "  TUDO RODANDO!"
echo "  Abra o Foxglove Studio no Windows e conecte:"
echo "  ws://localhost:8765"
echo "============================================="
echo ""
echo "Nós ativos:"
ros2 node list

# Manter rodando
wait
