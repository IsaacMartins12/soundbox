"""
SoundBox Palletizer - Pallet Visualizer Node
=============================================
Nó simples que publica um TF estático do pallet no world frame
e serve como ponto de referência para o planejamento.
"""
import rclpy
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped
import math


class PalletVisualizer(Node):
    def __init__(self):
        super().__init__('pallet_visualizer')

        self.tf_broadcaster = StaticTransformBroadcaster(self)

        # Publicar frame do pallet
        self.publish_pallet_frame()
        self.get_logger().info('PalletVisualizer: frame do pallet publicado.')

    def publish_pallet_frame(self):
        """Publica o frame estático do pallet no mundo."""
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = 'pallet_base'
        t.transform.translation.x = 0.5  # 50cm do robô
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = PalletVisualizer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
