#!/bin/bash
source /opt/ros/humble/setup.bash

# Criar SRDF para o GP88
cat > /tmp/gp88.srdf << 'EOF'
<?xml version="1.0" ?>
<robot name="motoman_gp88">
    <group name="manipulator">
        <chain base_link="base_link" tip_link="tool0"/>
    </group>
    <group_state name="home" group="manipulator">
        <joint name="joint_1_s" value="0"/>
        <joint name="joint_2_l" value="0"/>
        <joint name="joint_3_u" value="0"/>
        <joint name="joint_4_r" value="0"/>
        <joint name="joint_5_b" value="0"/>
        <joint name="joint_6_t" value="0"/>
    </group_state>
    <disable_collisions link1="base_link" link2="link_1_s" reason="Adjacent"/>
    <disable_collisions link1="link_1_s" link2="link_2_l" reason="Adjacent"/>
    <disable_collisions link1="link_2_l" link2="link_3_u" reason="Adjacent"/>
    <disable_collisions link1="link_3_u" link2="link_4_r" reason="Adjacent"/>
    <disable_collisions link1="link_4_r" link2="link_5_b" reason="Adjacent"/>
    <disable_collisions link1="link_5_b" link2="link_6_t" reason="Adjacent"/>
</robot>
EOF

# Criar config de controllers para MoveIt2
mkdir -p /tmp/moveit_config

cat > /tmp/moveit_config/moveit_controllers.yaml << 'EOF'
moveit_simple_controller_manager:
  controller_names:
    - manipulator_controller

  manipulator_controller:
    type: FollowJointTrajectory
    action_ns: follow_joint_trajectory
    default: true
    joints:
      - joint_1_s
      - joint_2_l
      - joint_3_u
      - joint_4_r
      - joint_5_b
      - joint_6_t
EOF

cat > /tmp/moveit_config/joint_limits.yaml << 'EOF'
joint_limits:
  joint_1_s:
    has_velocity_limits: true
    max_velocity: 2.96
    has_acceleration_limits: true
    max_acceleration: 5.0
  joint_2_l:
    has_velocity_limits: true
    max_velocity: 2.96
    has_acceleration_limits: true
    max_acceleration: 5.0
  joint_3_u:
    has_velocity_limits: true
    max_velocity: 2.96
    has_acceleration_limits: true
    max_acceleration: 5.0
  joint_4_r:
    has_velocity_limits: true
    max_velocity: 5.23
    has_acceleration_limits: true
    max_acceleration: 8.0
  joint_5_b:
    has_velocity_limits: true
    max_velocity: 5.23
    has_acceleration_limits: true
    max_acceleration: 8.0
  joint_6_t:
    has_velocity_limits: true
    max_velocity: 7.85
    has_acceleration_limits: true
    max_acceleration: 10.0
EOF

cat > /tmp/moveit_config/kinematics.yaml << 'EOF'
manipulator:
  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin
  kinematics_solver_search_resolution: 0.005
  kinematics_solver_timeout: 0.05
EOF

cat > /tmp/moveit_config/planning.yaml << 'EOF'
planning_plugin: ompl_interface/OMPLPlanner
request_adapters: >-
  default_planner_request_adapters/AddTimeOptimalParameterization
  default_planner_request_adapters/ResolveConstraintFrames
  default_planner_request_adapters/FixWorkspaceBounds
  default_planner_request_adapters/FixStartStateBounds
  default_planner_request_adapters/FixStartStateCollision
  default_planner_request_adapters/FixStartStatePathConstraints
start_state_max_bounds_error: 0.1
manipulator:
  planner_configs:
    - RRTConnect
    - RRT
    - PRM
  default_planner_config: RRTConnect
  projection_evaluator: joints(joint_1_s,joint_2_l)
  longest_valid_segment_fraction: 0.005
EOF

echo "=== MoveIt2 config criada ==="
echo "SRDF: /tmp/gp88.srdf"
echo "Controllers: /tmp/moveit_config/"
ls /tmp/moveit_config/
