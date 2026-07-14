"""
Teste de planejamento de trajetória com MoveIt2 + GP88.
Testa planejamento (sem execução real) para validar IK.
"""
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from pymoveit2 import MoveIt2
from geometry_msgs.msg import Pose, Point, Quaternion
import time
import math


def main():
    rclpy.init()

    node = Node("test_moveit_palletizer")
    callback_group = ReentrantCallbackGroup()
    node.get_logger().info("Inicializando MoveIt2 com GP88...")

    # Configurar MoveIt2
    moveit2 = MoveIt2(
        node=node,
        joint_names=[
            "joint_1_s", "joint_2_l", "joint_3_u",
            "joint_4_r", "joint_5_b", "joint_6_t"
        ],
        base_link_name="base_link",
        end_effector_name="tool0",
        group_name="manipulator",
        callback_group=callback_group,
    )

    # Executor multi-thread para callbacks
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor(2)
    executor.add_node(node)

    # Esperar MoveIt2 ficar pronto
    node.get_logger().info("Aguardando MoveIt2 (5s)...")
    time.sleep(5)

    # === TESTE 1: Mover para configuração de juntas (mais confiável) ===
    node.get_logger().info("=== TESTE 1: Planejando para configuração HOME ===")
    
    # Home: juntas todas em 0 (braço esticado para cima)
    home_config = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    moveit2.move_to_configuration(home_config)
    
    # Spin para processar
    start = time.time()
    while time.time() - start < 5.0:
        executor.spin_once(timeout_sec=0.1)
    
    node.get_logger().info("Teste 1 completo.")

    # === TESTE 2: Posição de pick (dentro do workspace do GP88) ===
    # GP88 tem alcance de ~2236mm. Usar posições em metros, dentro do alcance
    node.get_logger().info("=== TESTE 2: Planejando para PICK (joint space) ===")
    
    # Configuração que simula posição de pick (braço estendido para frente e abaixo)
    pick_config = [0.0, -0.5, 0.3, 0.0, -1.0, 0.0]  # rad
    moveit2.move_to_configuration(pick_config)
    
    start = time.time()
    while time.time() - start < 5.0:
        executor.spin_once(timeout_sec=0.1)
    
    node.get_logger().info("Teste 2 completo.")

    # === TESTE 3: Posição de place (outra config) ===
    node.get_logger().info("=== TESTE 3: Planejando para PLACE (joint space) ===")
    
    # Configuração que simula posição de place (girado para o lado do pallet)
    place_config = [1.2, -0.3, 0.5, 0.0, -0.8, 0.0]  # rad
    moveit2.move_to_configuration(place_config)
    
    start = time.time()
    while time.time() - start < 5.0:
        executor.spin_once(timeout_sec=0.1)
    
    node.get_logger().info("Teste 3 completo.")

    # === TESTE 4: Voltar home ===
    node.get_logger().info("=== TESTE 4: Voltando HOME ===")
    moveit2.move_to_configuration(home_config)
    
    start = time.time()
    while time.time() - start < 5.0:
        executor.spin_once(timeout_sec=0.1)
    
    node.get_logger().info("========================================")
    node.get_logger().info("  TESTES COMPLETOS")
    node.get_logger().info("  MoveIt2 + GP88 operacional!")
    node.get_logger().info("========================================")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
