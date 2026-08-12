"""
SoundBox Palletizer - MoveIt2 Trajectory Planner
=================================================
Nó ROS2 que planeja trajetórias via MoveIt2 e publica os resultados
em um tópico ou expõe via serviço para o web visualizer consumir.
Roda como servidor HTTP na porta 9091.
"""
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from pymoveit2 import MoveIt2
from geometry_msgs.msg import Pose, Point, Quaternion
from sensor_msgs.msg import JointState
from flask import Flask, jsonify, request as flask_request
from flask_cors import CORS
import threading
import time
import math
import requests
import json

# Flask app para expor trajetórias
flask_app = Flask(__name__)
CORS(flask_app)

# Dados globais compartilhados
planned_trajectories = []
planning_status = {"state": "idle", "progress": 0, "message": ""}
joint_names = ["joint_1_s", "joint_2_l", "joint_3_u", "joint_4_r", "joint_5_b", "joint_6_t"]

# Posições chave em coordenadas do mundo (metros)
# Cena: robô em (-1.2, 0, 0), esteira em (-1.2, 0.55, -1.8), pallet em (1.2, 0.13, 0.3)
ROBOT_BASE = {"x": -1.2, "y": 0.0, "z": 0.0}
CONVEYOR_TOP = {"x": -1.2, "y": 0.55, "z": -1.8}
PALLET_BASE = {"x": 1.2, "y": 0.13, "z": 0.3}

HOME_POS = {"x": -1.2, "y": 2.0, "z": 0.0}  # Acima do robô
PICK_ABOVE_POS = {"x": -1.2, "y": 1.2, "z": -1.8}  # Acima da esteira
PICK_POS = {"x": -1.2, "y": 0.6, "z": -1.8}  # Na esteira


def compute_place_positions(box_data, pallet_info):
    """
    Calcula posições XYZ do gripper para place de uma caixa.
    Retorna: place_above e place positions em metros.
    """
    px = box_data.get("x", 0) / 100.0  # cm → m
    py = box_data.get("y", 0) / 100.0
    pz = box_data.get("z", 0) / 100.0
    sx = box_data.get("sizex", 50) / 100.0
    sy = box_data.get("sizey", 50) / 100.0
    sz = box_data.get("sizez", 50) / 100.0

    pallet_sx = pallet_info.get("sizex", 100) / 100.0
    pallet_sy = pallet_info.get("sizey", 120) / 100.0

    # Centro da caixa no pallet (local)
    local_x = px + sx/2 - pallet_sx/2
    local_z = py + sy/2 - pallet_sy/2

    # Posição no mundo (pallet está em PALLET_BASE)
    world_x = PALLET_BASE["x"] + local_x
    world_y = PALLET_BASE["y"] + pz + sz  # Topo da caixa
    world_z = PALLET_BASE["z"] + local_z

    place_pos = {"x": world_x, "y": world_y, "z": world_z}
    place_above_pos = {"x": world_x, "y": world_y + 0.4, "z": world_z}

    return place_above_pos, place_pos


def generate_pick_and_place_sequence(boxes, pallet_info):
    """
    Gera sequência de posições XYZ do gripper para pick-and-place.
    """
    global planned_trajectories, planning_status

    planned_trajectories = []
    planning_status = {"state": "planning", "progress": 0, "message": "Planejando..."}

    for i, box in enumerate(boxes):
        progress = int((i / len(boxes)) * 100)
        planning_status = {"state": "planning", "progress": progress, "message": f"Planejando caixa {i+1}/{len(boxes)}"}

        place_above_pos, place_pos = compute_place_positions(box, pallet_info)

        # Sequência de waypoints (posições XYZ do gripper)
        box_trajectory = {
            "box_index": i,
            "box_data": box,
            "waypoints": [
                {"label": "home", "position": HOME_POS, "duration": 1.0, "gripper": "open"},
                {"label": "pick_above", "position": PICK_ABOVE_POS, "duration": 0.8, "gripper": "open"},
                {"label": "pick", "position": PICK_POS, "duration": 0.6, "gripper": "open"},
                {"label": "grab", "position": PICK_POS, "duration": 0.3, "gripper": "close"},
                {"label": "pick_lift", "position": PICK_ABOVE_POS, "duration": 0.6, "gripper": "close"},
                {"label": "transit", "position": HOME_POS, "duration": 0.8, "gripper": "close"},
                {"label": "place_above", "position": place_above_pos, "duration": 0.8, "gripper": "close"},
                {"label": "place", "position": place_pos, "duration": 0.6, "gripper": "close"},
                {"label": "release", "position": place_pos, "duration": 0.3, "gripper": "open"},
                {"label": "place_retreat", "position": place_above_pos, "duration": 0.5, "gripper": "open"},
            ]
        }
        planned_trajectories.append(box_trajectory)

    planning_status = {"state": "done", "progress": 100, "message": f"Planejamento completo: {len(boxes)} caixas"}
    return planned_trajectories


def generate_pick_and_place_sequence(boxes, pallet_info):
    """
    Gera sequência completa de configurações de juntas para pick-and-place.
    Cada caixa tem: home → pick_above → pick → pick_above → place_above → place → place_above → home
    """
    global planned_trajectories, planning_status

    planned_trajectories = []
    planning_status = {"state": "planning", "progress": 0, "message": "Planejando..."}

    for i, box in enumerate(boxes):
        progress = int((i / len(boxes)) * 100)
        planning_status = {"state": "planning", "progress": progress, "message": f"Planejando caixa {i+1}/{len(boxes)}"}

        place_config = compute_place_config(box, pallet_info, i, len(boxes))

        # Configuração "acima" do place (mesma posição lateral mas J2/J3 mais retraídos)
        place_above_config = list(place_config)
        place_above_config[1] += 0.2  # Shoulder mais para cima
        place_above_config[2] -= 0.15  # Elbow menos estendido
        place_above_config[4] = -(place_above_config[1] + place_above_config[2]) - 1.57

        # Sequência de waypoints para esta caixa
        box_trajectory = {
            "box_index": i,
            "box_data": box,
            "waypoints": [
                {"label": "home", "joints": list(HOME_CONFIG), "duration": 1.2, "gripper": "open"},
                {"label": "pick_above", "joints": list(PICK_ABOVE_CONFIG), "duration": 1.0, "gripper": "open"},
                {"label": "pick", "joints": list(PICK_CONFIG), "duration": 0.8, "gripper": "open"},
                {"label": "grab", "joints": list(PICK_CONFIG), "duration": 0.3, "gripper": "close"},
                {"label": "pick_lift", "joints": list(PICK_ABOVE_CONFIG), "duration": 0.8, "gripper": "close"},
                {"label": "place_above", "joints": place_above_config, "duration": 1.2, "gripper": "close"},
                {"label": "place", "joints": place_config, "duration": 0.8, "gripper": "close"},
                {"label": "release", "joints": place_config, "duration": 0.3, "gripper": "open"},
                {"label": "place_retreat", "joints": place_above_config, "duration": 0.8, "gripper": "open"},
            ]
        }
        planned_trajectories.append(box_trajectory)

    # Final: home
    planning_status = {"state": "done", "progress": 100, "message": f"Planejamento completo: {len(boxes)} caixas"}
    return planned_trajectories


# === Flask endpoints ===

@flask_app.route('/api/plan', methods=['POST'])
def plan():
    """Planeja trajetória completa para todas as caixas."""
    data = flask_request.get_json()
    boxes = data.get("cases", [])
    pallet = data.get("pallet", {})

    if not boxes:
        return jsonify({"error": "Nenhuma caixa para planejar"}), 400

    # Gerar sequência
    trajectories = generate_pick_and_place_sequence(boxes, pallet)

    return jsonify({
        "status": "success",
        "total_boxes": len(boxes),
        "total_waypoints": sum(len(t["waypoints"]) for t in trajectories),
        "trajectories": trajectories,
        "joint_names": joint_names,
    })


@flask_app.route('/api/plan-status')
def plan_status():
    return jsonify(planning_status)


@flask_app.route('/api/joint-limits')
def joint_limits():
    """Retorna limites das juntas do GP88."""
    return jsonify({
        "joint_names": joint_names,
        "limits": {
            "joint_1_s": {"min": -3.14, "max": 3.14},
            "joint_2_l": {"min": -1.57, "max": 2.36},
            "joint_3_u": {"min": -1.22, "max": 3.67},
            "joint_4_r": {"min": -3.49, "max": 3.49},
            "joint_5_b": {"min": -2.18, "max": 2.18},
            "joint_6_t": {"min": -7.85, "max": 7.85},
        }
    })


def run_flask():
    flask_app.run(host='0.0.0.0', port=9091, debug=False)


if __name__ == '__main__':
    print("MoveIt Planner HTTP Server na porta 9091")
    run_flask()
