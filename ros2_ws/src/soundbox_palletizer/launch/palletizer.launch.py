"""Launch file para o sistema de paletização SoundBox."""
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_dir = get_package_share_directory('soundbox_palletizer')
    params_file = os.path.join(pkg_dir, 'config', 'palletizer_params.yaml')

    return LaunchDescription([
        # Nó de visualização do pallet (TF estático)
        Node(
            package='soundbox_palletizer',
            executable='pallet_visualizer',
            name='pallet_visualizer',
            output='screen',
        ),
        # Nó principal que publica coordenadas
        Node(
            package='soundbox_palletizer',
            executable='coordinate_publisher',
            name='coordinate_publisher',
            output='screen',
            parameters=[params_file],
        ),
        # RViz para visualização
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', os.path.join(pkg_dir, 'config', 'palletizer.rviz')],
        ),
    ])
