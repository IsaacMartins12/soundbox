"""
SoundBox Pallet Optimizer - Backend API
"""
import os
import csv
import io
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from models.pallet import Pallet
from algorithms.packer import pack_pallet
from algorithms.packer_L import pack_pallet_L
from algorithms.trajectory_generator import generate_trajectory, export_csv as export_trajectory_csv
from database import init_db, get_all_boxes, get_box, create_box, update_box, delete_box, get_all_pallets, create_pallet, delete_pallet

PRESETS_FILE = os.path.join(os.path.dirname(__file__), "presets.json")

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# Inicializa banco de dados
init_db()


@app.route("/")
def index():
    """Serve a página principal."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """Serve arquivos estáticos do frontend."""
    return send_from_directory(app.static_folder, path)


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """
    Endpoint principal de cálculo.

    Body JSON esperado:
    {
        "pallet": {
            "sizex": 120,
            "sizey": 100,
            "sizez": 150,
            "max_weight": 1000
        },
        "cases": [
            {
                "code": "BOX-A",
                "sizex": 30,
                "sizey": 25,
                "sizez": 20,
                "weight": 2.5,
                "quantity": 40,
                "strength": 5
            }
        ]
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Body JSON é obrigatório"}), 400

    pallet_data = data.get("pallet")
    cases_data = data.get("cases")

    if not pallet_data or not cases_data:
        return jsonify({"error": "Campos 'pallet' e 'cases' são obrigatórios"}), 400

    # Valida dimensões do palete
    try:
        pallet_size = (
            float(pallet_data["sizex"]),
            float(pallet_data["sizey"]),
            float(pallet_data["sizez"]),
        )
        max_weight = float(pallet_data.get("max_weight") or "inf")
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Dimensões do palete inválidas: {str(e)}"}), 400

    # Valida caixas
    validated_cases = []
    for i, case in enumerate(cases_data):
        try:
            validated_cases.append({
                "code": case.get("code", f"BOX-{i+1}"),
                "sizex": float(case["sizex"]),
                "sizey": float(case["sizey"]),
                "sizez": float(case["sizez"]),
                "weight": float(case.get("weight", 0)),
                "quantity": int(case.get("quantity", 1)),
                "strength": int(case.get("strength", 100)),
                "pallet_face": case.get("pallet_face", "xy"),
                "interlocking_type": case.get("interlocking_type", "mirror"),
            })
        except (KeyError, ValueError, TypeError) as e:
            return jsonify({"error": f"Caixa {i+1} inválida: {str(e)}"}), 400

    # Parâmetro de overhang (saliência permitida)
    overhang = float(data.get("overhang", 5.0))

    # Executa o algoritmo
    pallet = Pallet(pallet_size, max_weight)
    result = pack_pallet(pallet, validated_cases, overhang=overhang)

    response = result.to_dict()
    response["requested_cases"] = sum(c["quantity"] for c in validated_cases)

    return jsonify(response)


@app.route("/api/calculate-l", methods=["POST"])
def calculate_l():
    """
    Endpoint para cálculo com caixas em formato L.

    Body JSON esperado:
    {
        "pallet": {
            "sizex": 100,
            "sizey": 120,
            "sizez": 200,
            "max_weight": 1200
        },
        "l_box": {
            "comp_total": 91.4,
            "largura": 26.3,
            "alt_total": 43.5,
            "braco": 26.3,
            "alt_base": 17.2,
            "weight": 8.0,
            "quantity": 20
        },
        "regular_box": {
            "code": "BOX-RECT",
            "sizex": 60,
            "sizey": 40,
            "sizez": 20,
            "weight": 4.0,
            "quantity": 0,
            "strength": 10
        }
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Body JSON é obrigatório"}), 400

    pallet_data = data.get("pallet")
    l_box_data = data.get("l_box")
    regular_box_data = data.get("regular_box")

    if not pallet_data or not l_box_data:
        return jsonify({"error": "Campos 'pallet' e 'l_box' são obrigatórios"}), 400

    # Valida pallet
    try:
        pallet_size = (
            float(pallet_data["sizex"]),
            float(pallet_data["sizey"]),
            float(pallet_data["sizez"]),
        )
        max_weight = float(pallet_data.get("max_weight") or 99999)
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Dimensões do palete inválidas: {str(e)}"}), 400

    # Valida caixa L
    try:
        l_dims = {
            "comp_total": float(l_box_data["comp_total"]),
            "largura": float(l_box_data["largura"]),
            "alt_vertical": float(l_box_data["alt_vertical"]),
            "alt_perpendicular": float(l_box_data["alt_perpendicular"]),
            "comp_braco": float(l_box_data.get("comp_braco", float(l_box_data["comp_total"]) / 2)),
            "l_orientation": l_box_data.get("l_orientation", "vertical"),
        }
        l_weight = float(l_box_data.get("weight", 0))
        l_quantity = int(l_box_data.get("quantity", 1))
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Dimensões da caixa L inválidas: {str(e)}"}), 400

    # Calcula empacotamento da caixa L
    overhang = float(data.get("overhang", 0))
    print(f"[DEBUG] l_dims: {l_dims}")
    print(f"[DEBUG] orientation: {l_dims.get('l_orientation')}, par será: comp={l_dims['comp_total']}, larg={'largura' if l_dims.get('l_orientation')=='vertical' else 'alt_v+alt_p'}, alt={'alt_v+alt_p' if l_dims.get('l_orientation')=='vertical' else 'largura'}")
    result_l = pack_pallet_L(
        pallet_size=pallet_size,
        l_dims=l_dims,
        quantidade=l_quantity,
        peso_caixa=l_weight,
        max_weight=max_weight,
        overhang=overhang,
    )

    # Se também tem caixa retangular, calcula separadamente
    result_regular = None
    if regular_box_data and int(regular_box_data.get("quantity", 0)) > 0:
        overhang = float(data.get("overhang", 5.0))
        pallet_obj = Pallet(pallet_size, max_weight)
        cases_input = [{
            "code": regular_box_data.get("code", "BOX-RECT"),
            "sizex": float(regular_box_data["sizex"]),
            "sizey": float(regular_box_data["sizey"]),
            "sizez": float(regular_box_data["sizez"]),
            "weight": float(regular_box_data.get("weight", 0)),
            "quantity": int(regular_box_data["quantity"]),
            "strength": int(regular_box_data.get("strength", 100)),
        }]
        pallet_result = pack_pallet(pallet_obj, cases_input, overhang=overhang)
        result_regular = pallet_result.to_dict()

    response = {
        "l_result": result_l,
        "regular_result": result_regular,
        "pallet": {
            "sizex": pallet_size[0],
            "sizey": pallet_size[1],
            "sizez": pallet_size[2],
            "max_weight": max_weight,
        },
    }

    return jsonify(response)


@app.route("/api/boxes", methods=["GET"])
def list_boxes():
    """Lista todos os modelos de caixa cadastrados."""
    return jsonify(get_all_boxes())


@app.route("/api/boxes", methods=["POST"])
def add_box():
    """Cadastra um novo modelo de caixa."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400
    new_id = create_box(data)
    return jsonify({"success": True, "id": new_id})


@app.route("/api/boxes/<int:box_id>", methods=["PUT"])
def edit_box(box_id):
    """Atualiza um modelo de caixa existente."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400
    update_box(box_id, data)
    return jsonify({"success": True})


@app.route("/api/boxes/<int:box_id>", methods=["DELETE"])
def remove_box(box_id):
    """Remove um modelo de caixa."""
    delete_box(box_id)
    return jsonify({"success": True})


@app.route("/api/pallets-db", methods=["GET"])
def list_pallets_db():
    """Lista todos os modelos de pallet cadastrados."""
    return jsonify(get_all_pallets())


@app.route("/api/pallets-db", methods=["POST"])
def add_pallet_db():
    """Cadastra um novo modelo de pallet."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400
    new_id = create_pallet(data)
    return jsonify({"success": True, "id": new_id})


@app.route("/api/pallets-db/<int:pallet_id>", methods=["DELETE"])
def remove_pallet_db(pallet_id):
    """Remove um modelo de pallet."""
    delete_pallet(pallet_id)
    return jsonify({"success": True})


@app.route("/api/presets", methods=["GET"])
def get_presets():
    """Retorna todos os modelos salvos."""
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            presets = json.load(f)
    else:
        presets = []
    return jsonify(presets)


@app.route("/api/presets", methods=["POST"])
def save_preset():
    """Salva um novo modelo ou atualiza existente."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400

    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            presets = json.load(f)
    else:
        presets = []

    # Se tem id, atualiza; senão cria novo
    preset_id = data.get("id") or str(uuid.uuid4())[:8]
    data["id"] = preset_id

    existing = next((i for i, p in enumerate(presets) if p["id"] == preset_id), None)
    if existing is not None:
        presets[existing] = data
    else:
        presets.append(data)

    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)

    return jsonify({"success": True, "id": preset_id})


@app.route("/api/presets/<preset_id>", methods=["DELETE"])
def delete_preset(preset_id):
    """Remove um modelo salvo."""
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            presets = json.load(f)
    else:
        return jsonify({"error": "Nenhum preset encontrado"}), 404

    presets = [p for p in presets if p["id"] != preset_id]

    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)

    return jsonify({"success": True})


@app.route("/api/trajectory", methods=["POST"])
def get_trajectory():
    """
    Gera a trajetória de pick-and-place para o robô.
    
    Body JSON esperado (mesmo do /api/calculate):
    {
        "pallet": {...},
        "cases": [...],
        "overhang": 5,
        "trajectory_config": {  // opcional
            "pick_position": {"x": 0, "y": -800, "z": 500},
            "pallet_offset": {"x": 700, "y": 0, "z": 150},
            "approach_height": 200,
            "safe_height": 800
        }
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON é obrigatório"}), 400

    # Primeiro calcula o packing
    pallet_data = data.get("pallet")
    cases_data = data.get("cases")
    
    if not pallet_data or not cases_data:
        return jsonify({"error": "Campos 'pallet' e 'cases' são obrigatórios"}), 400

    try:
        pallet_size = (
            float(pallet_data["sizex"]),
            float(pallet_data["sizey"]),
            float(pallet_data["sizez"]),
        )
        max_weight = float(pallet_data.get("max_weight") or 99999)
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Pallet inválido: {str(e)}"}), 400

    validated_cases = []
    for i, case in enumerate(cases_data):
        try:
            validated_cases.append({
                "code": case.get("code", f"BOX-{i+1}"),
                "sizex": float(case["sizex"]),
                "sizey": float(case["sizey"]),
                "sizez": float(case["sizez"]),
                "weight": float(case.get("weight", 0)),
                "quantity": int(case.get("quantity", 1)),
                "strength": int(case.get("strength", 100)),
                "pallet_face": case.get("pallet_face", "xy"),
                "interlocking_type": case.get("interlocking_type", "mirror"),
            })
        except (KeyError, ValueError) as e:
            return jsonify({"error": f"Caixa inválida: {str(e)}"}), 400

    overhang = float(data.get("overhang", 5.0))
    pallet = Pallet(pallet_size, max_weight)
    result = pack_pallet(pallet, validated_cases, overhang=overhang)
    pallet_result = result.to_dict()

    # Gerar trajetória
    config = data.get("trajectory_config", None)
    trajectory = generate_trajectory(pallet_result, config)

    return jsonify(trajectory)


@app.route("/api/trajectory/csv", methods=["POST"])
def get_trajectory_csv():
    """Gera a trajetória em formato CSV para download."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON é obrigatório"}), 400

    # Mesmo processamento
    pallet_data = data.get("pallet")
    cases_data = data.get("cases")
    
    if not pallet_data or not cases_data:
        return jsonify({"error": "Campos 'pallet' e 'cases' são obrigatórios"}), 400

    pallet_size = (
        float(pallet_data["sizex"]),
        float(pallet_data["sizey"]),
        float(pallet_data["sizez"]),
    )
    max_weight = float(pallet_data.get("max_weight") or 99999)

    validated_cases = [{
        "code": c.get("code", "BOX"),
        "sizex": float(c["sizex"]),
        "sizey": float(c["sizey"]),
        "sizez": float(c["sizez"]),
        "weight": float(c.get("weight", 0)),
        "quantity": int(c.get("quantity", 1)),
        "strength": int(c.get("strength", 100)),
        "pallet_face": c.get("pallet_face", "xy"),
        "interlocking_type": c.get("interlocking_type", "mirror"),
    } for c in cases_data]

    overhang = float(data.get("overhang", 5.0))
    pallet = Pallet(pallet_size, max_weight)
    result = pack_pallet(pallet, validated_cases, overhang=overhang)
    pallet_result = result.to_dict()

    config = data.get("trajectory_config", None)
    trajectory = generate_trajectory(pallet_result, config)
    csv_content = export_trajectory_csv(trajectory)

    return jsonify({"csv": csv_content, "total_waypoints": trajectory["total_waypoints"]})


@app.route("/api/export-csv", methods=["POST"])
def export_csv():
    """Exporta as coordenadas das caixas posicionadas em formato CSV."""
    data = request.get_json()

    if not data or "cases" not in data:
        return jsonify({"error": "Dados de caixas são obrigatórios"}), 400

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["code", "x", "y", "z", "sizex", "sizey", "sizez", "weight", "rotated"])

    for case in data["cases"]:
        writer.writerow([
            case.get("code", ""),
            case.get("x", 0),
            case.get("y", 0),
            case.get("z", 0),
            case.get("sizex", 0),
            case.get("sizey", 0),
            case.get("sizez", 0),
            case.get("weight", 0),
            case.get("rotated", False),
        ])

    csv_content = output.getvalue()
    return jsonify({"csv": csv_content})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
