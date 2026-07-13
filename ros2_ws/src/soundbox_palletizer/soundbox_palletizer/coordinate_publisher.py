"""
SoundBox Palletizer - Coordinate Publisher Node
================================================
Busca as coordenadas calculadas pelo backend SoundBox e publica como:
- Markers no RViz (visualização das caixas e pontos de pega)
- PoseArray para planejamento de trajetória do MoveIt2
- Sequence de goals para execução do pick-and-place
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose, PoseArray, PoseStamped, Point
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA, Header
import requests
import json
import math


class CoordinatePublisher(Node):
    def __init__(self):
        super().__init__('coordinate_publisher')

        # Parâmetros
        self.declare_parameter('backend_url', 'http://host.docker.internal:5000')
        self.declare_parameter('pick_height_offset', 10.0)
        self.declare_parameter('safe_height', 80.0)
        self.declare_parameter('velocity_scaling', 0.3)
        self.declare_parameter('pick_position.x', 0.0)
        self.declare_parameter('pick_position.y', -80.0)
        self.declare_parameter('pick_position.z', 50.0)
        self.declare_parameter('pallet_offset.x', -50.0)
        self.declare_parameter('pallet_offset.y', 50.0)
        self.declare_parameter('pallet_offset.z', 0.0)

        # Publishers
        self.marker_pub = self.create_publisher(MarkerArray, '/pallet_visualization', 10)
        self.pose_pub = self.create_publisher(PoseArray, '/place_poses', 10)
        self.pick_pub = self.create_publisher(PoseStamped, '/pick_pose', 10)

        # Timer para publicar periodicamente (visualização)
        self.timer = self.create_timer(2.0, self.publish_visualization)

        # Dados das caixas (carregados do backend)
        self.cases = []
        self.pallet_info = None

        self.get_logger().info('CoordinatePublisher inicializado.')
        self.get_logger().info('Use: ros2 service call /load_pallet std_srvs/srv/Trigger')

    def fetch_from_backend(self, model_id=None):
        """Busca coordenadas do backend SoundBox."""
        backend_url = self.get_parameter('backend_url').get_parameter_value().string_value

        try:
            # Buscar modelos disponíveis
            response = requests.get(f'{backend_url}/api/boxes')
            if response.status_code != 200:
                self.get_logger().error(f'Erro ao buscar modelos: {response.status_code}')
                return False

            models = response.json()
            if not models:
                self.get_logger().warn('Nenhum modelo cadastrado no backend.')
                return False

            # Usar o primeiro modelo ou o especificado
            model = models[0] if model_id is None else next(
                (m for m in models if m['id'] == model_id), models[0]
            )

            self.get_logger().info(f'Carregando modelo: {model["name"]}')

            # Montar payload de cálculo
            payload = {
                "pallet": {
                    "sizex": model.get("pallet_sizex", 100),
                    "sizey": model.get("pallet_sizey", 120),
                    "sizez": model.get("pallet_sizez", 200),
                    "max_weight": model.get("pallet_max_weight", 1200),
                },
                "cases": [{
                    "code": model.get("code", "BOX"),
                    "sizex": model["sizex"],
                    "sizey": model["sizey"],
                    "sizez": model["sizez"],
                    "weight": model.get("weight", 0),
                    "quantity": model.get("quantity", 10),
                    "strength": model.get("strength", 10),
                    "pallet_face": model.get("pallet_face", "xy"),
                    "interlocking_type": model.get("interlocking_type", "mirror"),
                }],
                "overhang": model.get("overhang", 5),
            }

            # Calcular
            response = requests.post(f'{backend_url}/api/calculate', json=payload)
            if response.status_code != 200:
                self.get_logger().error(f'Erro no cálculo: {response.text}')
                return False

            result = response.json()
            self.cases = result.get('cases', [])
            self.pallet_info = result.get('pallet', {})

            self.get_logger().info(
                f'Carregadas {len(self.cases)} caixas | '
                f'Utilização: {result.get("volume_utilization", 0)}%'
            )
            return True

        except requests.exceptions.ConnectionError:
            self.get_logger().error(
                f'Não foi possível conectar ao backend ({backend_url}). '
                'Verifique se o Flask está rodando.'
            )
            return False

    def publish_visualization(self):
        """Publica marcadores para visualização no RViz."""
        if not self.cases:
            # Tenta carregar na primeira vez
            self.fetch_from_backend()
            if not self.cases:
                return

        marker_array = MarkerArray()
        pose_array = PoseArray()
        pose_array.header = Header(frame_id='world')

        pallet_offset_x = self.get_parameter('pallet_offset.x').get_parameter_value().double_value / 100.0
        pallet_offset_y = self.get_parameter('pallet_offset.y').get_parameter_value().double_value / 100.0
        pallet_offset_z = self.get_parameter('pallet_offset.z').get_parameter_value().double_value / 100.0

        # Marcador do pallet (base)
        pallet_marker = Marker()
        pallet_marker.header.frame_id = 'world'
        pallet_marker.ns = 'pallet'
        pallet_marker.id = 0
        pallet_marker.type = Marker.CUBE
        pallet_marker.action = Marker.ADD
        pallet_marker.pose.position.x = pallet_offset_x
        pallet_marker.pose.position.y = pallet_offset_y
        pallet_marker.pose.position.z = pallet_offset_z - 0.02
        pallet_marker.scale.x = (self.pallet_info.get('sizex', 100)) / 100.0
        pallet_marker.scale.y = (self.pallet_info.get('sizey', 120)) / 100.0
        pallet_marker.scale.z = 0.04  # 4cm de espessura
        pallet_marker.color = ColorRGBA(r=0.55, g=0.35, b=0.17, a=0.9)
        marker_array.markers.append(pallet_marker)

        # Marcadores das caixas
        for i, case in enumerate(self.cases):
            # Converter cm para metros
            cx = case['x'] / 100.0 + pallet_offset_x - (self.pallet_info.get('sizex', 100) / 200.0)
            cy = case['y'] / 100.0 + pallet_offset_y - (self.pallet_info.get('sizey', 120) / 200.0)
            cz = case['z'] / 100.0 + pallet_offset_z
            sx = case['sizex'] / 100.0
            sy = case['sizey'] / 100.0
            sz = case['sizez'] / 100.0

            # Caixa como cubo
            box_marker = Marker()
            box_marker.header.frame_id = 'world'
            box_marker.ns = 'boxes'
            box_marker.id = i + 1
            box_marker.type = Marker.CUBE
            box_marker.action = Marker.ADD
            box_marker.pose.position.x = cx + sx / 2
            box_marker.pose.position.y = cy + sy / 2
            box_marker.pose.position.z = cz + sz / 2
            box_marker.scale.x = sx
            box_marker.scale.y = sy
            box_marker.scale.z = sz
            box_marker.color = ColorRGBA(r=0.76, g=0.60, b=0.42, a=0.85)
            marker_array.markers.append(box_marker)

            # Ponto de pega (esfera vermelha no centro do topo)
            pick_marker = Marker()
            pick_marker.header.frame_id = 'world'
            pick_marker.ns = 'pick_points'
            pick_marker.id = i + 1000
            pick_marker.type = Marker.SPHERE
            pick_marker.action = Marker.ADD
            pick_marker.pose.position.x = cx + sx / 2
            pick_marker.pose.position.y = cy + sy / 2
            pick_marker.pose.position.z = cz + sz
            pick_marker.scale.x = 0.02
            pick_marker.scale.y = 0.02
            pick_marker.scale.z = 0.02
            pick_marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
            marker_array.markers.append(pick_marker)

            # Pose de place para MoveIt
            place_pose = Pose()
            place_pose.position.x = cx + sx / 2
            place_pose.position.y = cy + sy / 2
            place_pose.position.z = cz + sz
            place_pose.orientation.w = 1.0  # Gripper apontando para baixo
            pose_array.poses.append(place_pose)

        self.marker_pub.publish(marker_array)
        self.pose_pub.publish(pose_array)


def main(args=None):
    rclpy.init(args=args)
    node = CoordinatePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
