"""
Gerador de Trajetórias para Robô Paletizador
=============================================
Gera a sequência de pontos (waypoints) para o robô executar o pick-and-place
de cada caixa. Exportável em formato CSV ou JSON para o controlador Yaskawa.

Referencial:
- Origem (0,0,0) = centro da base do robô
- X+ = direção do pallet
- Y+ = lateral
- Z+ = para cima
- Unidades: milímetros e graus (padrão Yaskawa)
"""
import math


# Posição da esteira em relação ao robô (mm)
PICK_POSITION = {
    "x": 0,
    "y": -800,   # 80cm à frente
    "z": 500,    # 50cm de altura (altura da esteira)
    "rx": 180,   # gripper apontando para baixo
    "ry": 0,
    "rz": 0,
}

# Offset do pallet em relação ao robô (mm)
# Centro do pallet
PALLET_OFFSET = {
    "x": 700,    # 70cm à direita
    "y": 0,      # centralizado
    "z": 150,    # 15cm (altura do pallet)
}

# Alturas de segurança (mm)
APPROACH_HEIGHT = 200   # 20cm acima do ponto de place
SAFE_HEIGHT = 800       # 80cm para movimentação livre
PICK_APPROACH = 100     # 10cm acima do ponto de pick

# Velocidades (% da velocidade máxima)
SPEED_FAST = 80     # Movimentação livre
SPEED_MEDIUM = 50   # Approach
SPEED_SLOW = 20     # Pick/Place (precisão)


def generate_trajectory(pallet_result, config=None):
    """
    Gera a trajetória completa de paletização.
    
    :param pallet_result: Resultado do cálculo de paletização (dict com 'cases' e 'pallet')
    :param config: Configurações opcionais (posições, velocidades)
    :return: Lista de waypoints para cada caixa
    """
    cases = pallet_result.get("cases", [])
    pallet = pallet_result.get("pallet", {})
    
    if not cases:
        return {"error": "Nenhuma caixa para gerar trajetória", "waypoints": []}
    
    # Configurações (usar defaults ou custom)
    pick_pos = config.get("pick_position", PICK_POSITION) if config else PICK_POSITION
    pallet_offset = config.get("pallet_offset", PALLET_OFFSET) if config else PALLET_OFFSET
    approach_h = config.get("approach_height", APPROACH_HEIGHT) if config else APPROACH_HEIGHT
    safe_h = config.get("safe_height", SAFE_HEIGHT) if config else SAFE_HEIGHT
    
    pallet_sizex = pallet.get("sizex", 100) * 10  # cm → mm
    pallet_sizey = pallet.get("sizey", 120) * 10
    
    all_waypoints = []
    
    # Ponto HOME (posição inicial e final do robô)
    home_point = {
        "type": "JOINT",
        "label": "HOME",
        "x": 0, "y": 0, "z": safe_h,
        "rx": 180, "ry": 0, "rz": 0,
        "speed": SPEED_FAST,
        "motion": "JOINT",
    }
    
    for i, case in enumerate(cases):
        # Converter posição da caixa de cm para mm
        cx = case["x"] * 10   # posição X no pallet
        cy = case["y"] * 10   # posição Y no pallet
        cz = case["z"] * 10   # posição Z (altura da camada)
        sx = case["sizex"] * 10
        sy = case["sizey"] * 10
        sz = case["sizez"] * 10
        
        # Centro da face superior da caixa (ponto de place)
        # Em relação ao robô = pallet_offset + posição no pallet (centralizado)
        place_x = pallet_offset["x"] + cx + sx/2 - pallet_sizex/2
        place_y = pallet_offset["y"] + cy + sy/2 - pallet_sizey/2
        place_z = pallet_offset["z"] + cz + sz  # topo da caixa
        
        # Orientação do gripper (sempre para baixo, rotaciona se caixa rotacionada)
        rz = 90 if case.get("rotated", False) else 0
        
        # Gerar sequência de waypoints para esta caixa
        box_waypoints = {
            "box_index": i + 1,
            "box_code": case.get("code", f"BOX-{i+1}"),
            "box_size": {"x": sx, "y": sy, "z": sz},
            "sequence": [
                # 1. Mover para acima da posição de pick
                {
                    "step": 1,
                    "label": f"PICK_APPROACH_{i+1}",
                    "type": "MOVE",
                    "motion": "JOINT",
                    "x": pick_pos["x"],
                    "y": pick_pos["y"],
                    "z": pick_pos["z"] + PICK_APPROACH,
                    "rx": 180, "ry": 0, "rz": 0,
                    "speed": SPEED_FAST,
                    "description": "Approach acima da esteira",
                },
                # 2. Descer para pegar
                {
                    "step": 2,
                    "label": f"PICK_{i+1}",
                    "type": "PICK",
                    "motion": "LINEAR",
                    "x": pick_pos["x"],
                    "y": pick_pos["y"],
                    "z": pick_pos["z"],
                    "rx": 180, "ry": 0, "rz": rz,
                    "speed": SPEED_SLOW,
                    "description": "Posição de pega (ativar vácuo)",
                    "gripper": "CLOSE",
                },
                # 3. Levantar com a caixa
                {
                    "step": 3,
                    "label": f"PICK_LIFT_{i+1}",
                    "type": "MOVE",
                    "motion": "LINEAR",
                    "x": pick_pos["x"],
                    "y": pick_pos["y"],
                    "z": safe_h,
                    "rx": 180, "ry": 0, "rz": rz,
                    "speed": SPEED_MEDIUM,
                    "description": "Levantar para altura segura",
                },
                # 4. Mover para acima da posição de place
                {
                    "step": 4,
                    "label": f"PLACE_APPROACH_{i+1}",
                    "type": "MOVE",
                    "motion": "JOINT",
                    "x": place_x,
                    "y": place_y,
                    "z": place_z + approach_h,
                    "rx": 180, "ry": 0, "rz": rz,
                    "speed": SPEED_FAST,
                    "description": "Approach acima do destino no pallet",
                },
                # 5. Descer para posicionar
                {
                    "step": 5,
                    "label": f"PLACE_{i+1}",
                    "type": "PLACE",
                    "motion": "LINEAR",
                    "x": place_x,
                    "y": place_y,
                    "z": place_z,
                    "rx": 180, "ry": 0, "rz": rz,
                    "speed": SPEED_SLOW,
                    "description": "Posicionar caixa (desativar vácuo)",
                    "gripper": "OPEN",
                },
                # 6. Levantar após soltar
                {
                    "step": 6,
                    "label": f"PLACE_RETREAT_{i+1}",
                    "type": "MOVE",
                    "motion": "LINEAR",
                    "x": place_x,
                    "y": place_y,
                    "z": place_z + approach_h,
                    "rx": 180, "ry": 0, "rz": rz,
                    "speed": SPEED_MEDIUM,
                    "description": "Recuar acima da caixa posicionada",
                },
            ]
        }
        
        all_waypoints.append(box_waypoints)
    
    # Resumo
    total_points = sum(len(w["sequence"]) for w in all_waypoints)
    
    return {
        "total_boxes": len(cases),
        "total_waypoints": total_points,
        "home_position": home_point,
        "pallet_offset": pallet_offset,
        "pick_position": pick_pos,
        "waypoints": all_waypoints,
    }


def export_csv(trajectory):
    """
    Exporta a trajetória em formato CSV compatível com programação offline.
    Formato: step, label, motion, x, y, z, rx, ry, rz, speed, gripper
    """
    lines = ["step,label,motion,x_mm,y_mm,z_mm,rx_deg,ry_deg,rz_deg,speed_pct,gripper"]
    
    step_counter = 0
    
    # HOME inicial
    home = trajectory["home_position"]
    step_counter += 1
    lines.append(f"{step_counter},HOME,JOINT,{home['x']},{home['y']},{home['z']},{home['rx']},{home['ry']},{home['rz']},{home['speed']},")
    
    for box_wp in trajectory["waypoints"]:
        for wp in box_wp["sequence"]:
            step_counter += 1
            gripper = wp.get("gripper", "")
            lines.append(
                f"{step_counter},{wp['label']},{wp['motion']},"
                f"{wp['x']:.1f},{wp['y']:.1f},{wp['z']:.1f},"
                f"{wp['rx']:.1f},{wp['ry']:.1f},{wp['rz']:.1f},"
                f"{wp['speed']},{gripper}"
            )
    
    # HOME final
    step_counter += 1
    lines.append(f"{step_counter},HOME_FINAL,JOINT,{home['x']},{home['y']},{home['z']},{home['rx']},{home['ry']},{home['rz']},{home['speed']},")
    
    return "\n".join(lines)
