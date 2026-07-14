import launch
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    with open("/tmp/gp88.urdf", "r") as f:
        urdf = f.read()

    return LaunchDescription([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": urdf}],
            output="screen",
        ),
        Node(
            package="joint_state_publisher",
            executable="joint_state_publisher",
            output="screen",
        ),
    ])
