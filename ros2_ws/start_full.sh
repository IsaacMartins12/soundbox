#!/bin/bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash 2>/dev/null

echo "=== 1. Gerando URDF do GP88 ==="
bash /tmp/gen_urdf.sh 2>/dev/null

echo ""
echo "=== 2. Subindo MoveIt2 ==="
ros2 launch /tmp/launch_moveit.py &
sleep 5

echo ""
echo "=== 3. Subindo Web Visualizer (porta 9090) ==="
pkill -f web_visualizer 2>/dev/null
python3 /ros2_ws/src/soundbox_palletizer/soundbox_palletizer/web_visualizer.py &
sleep 2

echo ""
echo "=== 4. Subindo MoveIt Planner HTTP (porta 9091) ==="
pkill -f moveit_planner 2>/dev/null
python3 /ros2_ws/src/soundbox_palletizer/soundbox_palletizer/moveit_planner.py &
sleep 2

echo ""
echo "============================================="
echo "  SISTEMA COMPLETO RODANDO"
echo "  Web Visualizer: http://localhost:9090"
echo "  MoveIt2: move_group ativo"
echo "============================================="
echo ""
ros2 node list

wait
