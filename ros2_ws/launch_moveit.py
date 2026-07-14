"""Launch MoveIt2 com GP88 (sem GUI)"""
import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Ler URDF e SRDF
    with open("/tmp/gp88.urdf", "r") as f:
        robot_description = f.read()

    with open("/tmp/gp88.srdf", "r") as f:
        robot_description_semantic = f.read()

    # Ler configs
    import yaml
    with open("/tmp/moveit_config/kinematics.yaml", "r") as f:
        kinematics_yaml = yaml.safe_load(f)

    with open("/tmp/moveit_config/joint_limits.yaml", "r") as f:
        joint_limits_yaml = yaml.safe_load(f)

    with open("/tmp/moveit_config/planning.yaml", "r") as f:
        planning_yaml = yaml.safe_load(f)

    moveit_config = {
        "robot_description": robot_description,
        "robot_description_semantic": robot_description_semantic,
        "robot_description_kinematics": kinematics_yaml,
        "robot_description_planning": planning_yaml,
    }

    return LaunchDescription([
        # Robot State Publisher
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description}],
            output="screen",
        ),
        # Joint State Publisher (simulado)
        Node(
            package="joint_state_publisher",
            executable="joint_state_publisher",
            output="screen",
        ),
        # MoveIt2 Move Group
        Node(
            package="moveit_ros_move_group",
            executable="move_group",
            output="screen",
            parameters=[
                moveit_config,
                {"use_sim_time": False},
                {
                    "planning_scene_monitor_options": {
                        "robot_description": "robot_description",
                        "joint_state_topic": "/joint_states",
                    }
                },
            ],
        ),
    ])
