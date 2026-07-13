# SoundBox ROS2 Workspace

Workspace ROS2 para simulação da célula robótica de paletização com Yaskawa GP88.

## Pré-requisitos

- Docker Desktop com WSL2
- XServer (VcXsrv ou similar) para visualização GUI

## Como rodar

### 1. Subir o container
```bash
cd ros2_ws
docker compose up -d --build
```

### 2. Entrar no container
```bash
docker exec -it soundbox_ros2 bash
```

### 3. Dentro do container - rebuild e executar
```bash
source /opt/ros/humble/setup.bash
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash

# Rodar o sistema
ros2 launch soundbox_palletizer palletizer.launch.py
```

### 4. No host - garantir que o backend Flask está rodando
```bash
cd project/backend
python app.py
```

## Arquitetura

```
Backend Flask (host:5000) → API REST → coordinate_publisher (ROS2)
                                              ↓
                                     /pallet_visualization (MarkerArray)
                                     /place_poses (PoseArray)
                                              ↓
                                         RViz / MoveIt2
                                              ↓
                                      Gazebo (simulação)
```

## Pacotes

- `soundbox_palletizer`: Nó bridge entre backend e ROS2
- (futuro) `gp88_description`: URDF do Yaskawa GP88
- (futuro) `gp88_moveit_config`: Configuração MoveIt2
- (futuro) `soundbox_gazebo`: Mundo Gazebo com cena de paletização
