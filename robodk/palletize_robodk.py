"""
SoundBox Pallet Optimizer - Integração RoboDK
==============================================
Script que conecta o backend de paletização ao RoboDK para simulação
realista do Yaskawa GP88 fazendo pick-and-place.

Pré-requisitos:
    - RoboDK instalado e aberto
    - pip install robodk requests
    
Uso:
    python palletize_robodk.py

O script:
    1. Conecta ao RoboDK
    2. Carrega o robô GP88 (ou usa o que já está na cena)
    3. Busca as coordenadas do backend SoundBox
    4. Cria a esteira, pallet e caixas na cena
    5. Executa o pick-and-place de cada caixa com IK real
"""
import requests
import time
import sys

from robodk.robolink import Robolink, ITEM_TYPE_ROBOT, ITEM_TYPE_FRAME, ITEM_TYPE_TOOL
from robodk.robomath import Mat, transl, rotx, roty, rotz, eye
import robodk.robomath as robomath


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BACKEND_URL = "http://localhost:5000"

# Modelo do robô (nome na biblioteca RoboDK)
ROBOT_NAME = "Motoman GP88"

# Posições em mm (relativas à base do robô)
# GP88 alcance: 2236mm. Zona confortável com gripper para baixo: ~1000-1500mm à frente, 200-800mm de altura
PICK_POSITION = [800, 0, 300, 180, 0, 0]       # Esteira: 0.8m à frente no eixo X, 0.3m altura
PICK_APPROACH = [800, 0, 550, 180, 0, 0]        # Acima da esteira

# Offset do pallet em relação à base do robô (mm)
PALLET_OFFSET_X = -200    # Atrás-lateral
PALLET_OFFSET_Y = 1000    # 1m ao lado
PALLET_OFFSET_Z = 0       # Nível do chão

# Alturas de segurança (mm)
APPROACH_HEIGHT = 200      # Acima do ponto de place
SAFE_HEIGHT = 800          # Para movimentação livre

# Velocidades
SPEED_FAST = 500           # mm/s - movimentação livre
SPEED_MEDIUM = 300         # mm/s - approach
SPEED_SLOW = 100           # mm/s - pick/place

# ============================================================


def connect_robodk():
    """Conecta ao RoboDK."""
    print("Conectando ao RoboDK...")
    RDK = Robolink()
    
    if not RDK:
        print("ERRO: Não foi possível conectar ao RoboDK.")
        print("Certifique-se de que o RoboDK está aberto.")
        sys.exit(1)
    
    print("✓ Conectado ao RoboDK")
    return RDK


def setup_robot(RDK):
    """Carrega ou encontra o robô GP88 na cena."""
    robot = None
    
    # Procurar robô já carregado
    all_items = RDK.ItemList(ITEM_TYPE_ROBOT)
    for item in all_items:
        if "gp88" in item.Name().lower() or "motoman" in item.Name().lower():
            robot = item
            break
    
    if robot is None:
        print(f"Robô '{ROBOT_NAME}' não encontrado na cena.")
        print("Carregando da biblioteca...")
        
        # Tentar carregar da biblioteca online
        robot = RDK.AddFile(r'')  # Será buscado na biblioteca
        
        if robot is None:
            print("\nINSTRUÇÕES:")
            print("1. No RoboDK, vá em File → Open Online Library")
            print("2. Pesquise 'Motoman GP88' ou 'Yaskawa GP88'")
            print("3. Faça download e adicione à cena")
            print("4. Rode este script novamente")
            sys.exit(1)
    
    print(f"✓ Robô encontrado: {robot.Name()}")
    
    # Configurar velocidade
    robot.setSpeed(SPEED_FAST)
    robot.setAcceleration(1000)
    
    return robot


def create_box_stl(filepath, sx, sy, sz):
    """Cria um arquivo STL simples de um paralelepípedo."""
    # Vértices do cubo centrado na origem
    x, y, z = sx/2, sy/2, sz/2
    vertices = [
        [-x,-y,-z], [x,-y,-z], [x,y,-z], [-x,y,-z],  # bottom
        [-x,-y,z], [x,-y,z], [x,y,z], [-x,y,z],      # top
    ]
    # 12 triângulos (2 por face)
    triangles = [
        (0,1,2),(0,2,3),  # bottom
        (4,6,5),(4,7,6),  # top
        (0,4,5),(0,5,1),  # front
        (2,6,7),(2,7,3),  # back
        (0,3,7),(0,7,4),  # left
        (1,5,6),(1,6,2),  # right
    ]
    
    with open(filepath, 'w') as f:
        f.write("solid box\n")
        for tri in triangles:
            v0, v1, v2 = vertices[tri[0]], vertices[tri[1]], vertices[tri[2]]
            f.write(f"  facet normal 0 0 0\n")
            f.write(f"    outer loop\n")
            f.write(f"      vertex {v0[0]} {v0[1]} {v0[2]}\n")
            f.write(f"      vertex {v1[0]} {v1[1]} {v1[2]}\n")
            f.write(f"      vertex {v2[0]} {v2[1]} {v2[2]}\n")
            f.write(f"    endloop\n")
            f.write(f"  endfacet\n")
        f.write("endsolid box\n")


def setup_scene(RDK, robot, cases, pallet_info):
    """Cria os elementos da cena: pallet, esteira, caixas."""
    import tempfile, os
    print("Configurando cena...")
    
    parent = robot.Parent()
    
    # Usar a estação (world) como referência
    station = RDK.ActiveStation()
    
    # Criar frame do pallet no mundo
    pallet_frame = RDK.AddFrame("Pallet_Frame", station)
    pallet_frame.setPose(transl(PALLET_OFFSET_X, PALLET_OFFSET_Y, PALLET_OFFSET_Z))
    
    # Criar frame da esteira no mundo
    conveyor_frame = RDK.AddFrame("Conveyor_Frame", station)
    conveyor_frame.setPose(transl(0, 800, 300))
    
    # Dimensões (mm)
    pallet_sx = pallet_info.get("sizex", 100) * 10
    pallet_sy = pallet_info.get("sizey", 120) * 10
    
    # Criar pallet como STL
    tmp_dir = tempfile.gettempdir()
    
    pallet_stl = os.path.join(tmp_dir, "pallet.stl")
    create_box_stl(pallet_stl, pallet_sx, pallet_sy, 40)
    pallet_obj = RDK.AddFile(pallet_stl, pallet_frame)
    if pallet_obj.Valid():
        pallet_obj.setName("Pallet")
        pallet_obj.setPose(transl(0, 0, 20))  # Centro do pallet
        pallet_obj.setColor([0.65, 0.45, 0.25, 1.0])
    
    # Criar esteira como STL
    conveyor_stl = os.path.join(tmp_dir, "conveyor.stl")
    create_box_stl(conveyor_stl, 600, 400, 80)
    conveyor_obj = RDK.AddFile(conveyor_stl, conveyor_frame)
    if conveyor_obj.Valid():
        conveyor_obj.setName("Esteira")
        conveyor_obj.setPose(transl(0, 0, 40))
        conveyor_obj.setColor([0.3, 0.3, 0.35, 1.0])
    
    print(f"  Pallet: {pallet_sx}x{pallet_sy}mm em ({PALLET_OFFSET_X}, {PALLET_OFFSET_Y}, {PALLET_OFFSET_Z})")
    print(f"  Esteira em: ({PICK_POSITION[0]}, {PICK_POSITION[1]}, {PICK_POSITION[2]})")
    print(f"  Caixas: {len(cases)}")
    
    return pallet_frame, conveyor_frame


def fetch_pallet_data(model_id=None):
    """Busca dados de paletização do backend."""
    print(f"Buscando dados do backend ({BACKEND_URL})...")
    
    try:
        # Buscar modelos
        resp = requests.get(f"{BACKEND_URL}/api/boxes")
        if resp.status_code != 200:
            print(f"ERRO: Backend retornou {resp.status_code}")
            sys.exit(1)
        
        models = resp.json()
        if not models:
            print("ERRO: Nenhum modelo cadastrado no backend.")
            sys.exit(1)
        
        # Selecionar modelo
        if model_id:
            model = next((m for m in models if m['id'] == model_id), models[0])
        else:
            # Mostrar opções
            print("\nModelos disponíveis:")
            for m in models:
                print(f"  [{m['id']}] {m['name']} ({m.get('sizex','?')}x{m.get('sizey','?')}x{m.get('sizez','?')})")
            
            choice = input("\nEscolha o ID do modelo (Enter para o primeiro): ").strip()
            if choice:
                model = next((m for m in models if str(m['id']) == choice), models[0])
            else:
                model = models[0]
        
        print(f"✓ Modelo selecionado: {model['name']}")
        
        # Calcular paletização
        payload = {
            "pallet": {
                "sizex": model.get("pallet_sizex", 100),
                "sizey": model.get("pallet_sizey", 120),
                "sizez": model.get("pallet_sizez", 200),
                "max_weight": model.get("pallet_max_weight", 1200),
            },
            "cases": [{
                "code": model.get("code", "BOX"),
                "sizex": model.get("sizex", 60),
                "sizey": model.get("sizey", 40),
                "sizez": model.get("sizez", 20),
                "weight": model.get("weight", 5),
                "quantity": model.get("quantity", 10),
                "strength": model.get("strength", 10),
                "pallet_face": model.get("pallet_face", "xy"),
                "interlocking_type": model.get("interlocking_type", "mirror"),
            }],
            "overhang": model.get("overhang", 5),
        }
        
        resp = requests.post(f"{BACKEND_URL}/api/calculate", json=payload)
        if resp.status_code != 200:
            print(f"ERRO no cálculo: {resp.text}")
            sys.exit(1)
        
        result = resp.json()
        print(f"✓ Paletização calculada: {result['total_cases']} caixas, {result['volume_utilization']}% utilização")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print(f"ERRO: Não foi possível conectar ao backend ({BACKEND_URL}).")
        print("Certifique-se de que o Flask está rodando: python app.py")
        sys.exit(1)


def execute_palletization(RDK, robot, cases, pallet_info, pallet_frame):
    """Executa o pick-and-place de todas as caixas."""
    pallet_sx = pallet_info.get("sizex", 100) * 10  # cm → mm
    pallet_sy = pallet_info.get("sizey", 120) * 10
    
    total = len(cases)
    print(f"\n{'='*50}")
    print(f"  INICIANDO PALETIZAÇÃO: {total} caixas")
    print(f"{'='*50}\n")
    
    for i, case in enumerate(cases):
        print(f"[{i+1}/{total}] Caixa {case.get('code', 'BOX')}...", end=" ")
        
        # Converter posição da caixa (cm → mm)
        cx = case["x"] * 10
        cy = case["y"] * 10
        cz = case["z"] * 10
        sx = case["sizex"] * 10
        sy = case["sizey"] * 10
        sz = case["sizez"] * 10
        
        # Centro da face superior no referencial do pallet
        place_x = cx + sx/2 - pallet_sx/2
        place_y = cy + sy/2 - pallet_sy/2
        place_z = cz + sz
        
        # Posição absoluta de place (base do robô)
        abs_place_x = PALLET_OFFSET_X + place_x
        abs_place_y = PALLET_OFFSET_Y + place_y
        abs_place_z = PALLET_OFFSET_Z + place_z
        
        # Rotação do gripper (para baixo)
        # xyzwpr: [x, y, z, rx, ry, rz]
        rz = 90 if case.get("rotated", False) else 0
        
        # === SEQUÊNCIA DE MOVIMENTOS ===
        
        try:
            # 1. Mover para acima da esteira (JOINT - rápido)
            robot.setSpeed(SPEED_FAST)
            target_pick_above = transl(PICK_APPROACH[0], PICK_APPROACH[1], PICK_APPROACH[2]) * rotx(3.14159) * rotz(0)
            robot.MoveJ(target_pick_above)
            
            # 2. Descer para pegar (LINEAR - lento)
            robot.setSpeed(SPEED_SLOW)
            target_pick = transl(PICK_POSITION[0], PICK_POSITION[1], PICK_POSITION[2]) * rotx(3.14159) * rotz(rz * 3.14159/180)
            robot.MoveL(target_pick)
            
            # 3. Fechar gripper (simular)
            time.sleep(0.1)
            RDK.RunMessage("Gripper CLOSE", True)
            
            # 4. Levantar (LINEAR)
            robot.setSpeed(SPEED_MEDIUM)
            robot.MoveL(target_pick_above)
            
            # 5. Mover para acima do ponto de place (JOINT - rápido)
            robot.setSpeed(SPEED_FAST)
            target_place_above = transl(abs_place_x, abs_place_y, abs_place_z + APPROACH_HEIGHT) * rotx(3.14159) * rotz(rz * 3.14159/180)
            robot.MoveJ(target_place_above)
            
            # 6. Descer para posicionar (LINEAR - lento)
            robot.setSpeed(SPEED_SLOW)
            target_place = transl(abs_place_x, abs_place_y, abs_place_z) * rotx(3.14159) * rotz(rz * 3.14159/180)
            robot.MoveL(target_place)
            
            # 7. Abrir gripper
            time.sleep(0.1)
            RDK.RunMessage("Gripper OPEN", True)
            
            # 8. Criar caixa visual na posição final
            try:
                import tempfile, os
                tmp_dir = tempfile.gettempdir()
                box_stl = os.path.join(tmp_dir, f"box_{i}.stl")
                create_box_stl(box_stl, sx, sy, sz)
                box_obj = RDK.AddFile(box_stl, pallet_frame)
                if box_obj.Valid():
                    box_obj.setName(f"Box_{i+1}")
                    box_obj.setPose(transl(place_x, place_y, place_z - sz/2))
                    box_obj.setColor([0.76, 0.58, 0.38, 1.0])
            except:
                pass
            
            # 9. Recuar (LINEAR)
            robot.setSpeed(SPEED_MEDIUM)
            robot.MoveL(target_place_above)
            
            print(f"✓ posição ({abs_place_x:.0f}, {abs_place_y:.0f}, {abs_place_z:.0f})")
            
        except Exception as e:
            print(f"✗ ERRO: {str(e)[:60]}")
            # Tentar voltar para posição segura
            try:
                robot.setSpeed(SPEED_FAST)
                safe = transl(0, 0, SAFE_HEIGHT) * rotx(3.14159)
                robot.MoveJ(safe)
            except:
                pass
        
        print(f"✓ posição ({abs_place_x:.0f}, {abs_place_y:.0f}, {abs_place_z:.0f})")
    
    # Voltar para HOME
    robot.setSpeed(SPEED_FAST)
    home = transl(0, 0, SAFE_HEIGHT) * rotx(3.14159)
    robot.MoveJ(home)
    
    print(f"\n{'='*50}")
    print(f"  PALETIZAÇÃO COMPLETA!")
    print(f"  {total} caixas posicionadas com sucesso.")
    print(f"{'='*50}")


def main():
    print("=" * 50)
    print("  SoundBox Pallet Optimizer → RoboDK")
    print("  Simulação Yaskawa GP88")
    print("=" * 50)
    print()
    
    # 1. Conectar ao RoboDK
    RDK = connect_robodk()
    
    # 2. Buscar dados do backend
    result = fetch_pallet_data()
    cases = result["cases"]
    pallet_info = result["pallet"]
    
    # 3. Configurar robô
    robot = setup_robot(RDK)
    
    # 4. Configurar cena
    pallet_frame, conveyor_frame = setup_scene(RDK, robot, cases, pallet_info)
    
    # 5. Executar paletização
    input("\nPressione ENTER para iniciar a simulação...")
    execute_palletization(RDK, robot, cases, pallet_info, pallet_frame)


if __name__ == "__main__":
    main()
