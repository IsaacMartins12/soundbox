"""
Rotas de CRUD dos presets (modelos salvos em arquivo JSON).
"""
import os
import json
import uuid

from flask import Blueprint, request, jsonify

presets_bp = Blueprint("presets", __name__, url_prefix="/api/presets")

# presets.json fica na raiz do backend (um nivel acima da pasta routes)
PRESETS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets.json")


def _load_presets():
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_presets(presets):
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)


@presets_bp.route("", methods=["GET"])
def get_presets():
    """Retorna todos os modelos salvos."""
    return jsonify(_load_presets())


@presets_bp.route("", methods=["POST"])
def save_preset():
    """Salva um novo modelo ou atualiza existente."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400

    presets = _load_presets()

    preset_id = data.get("id") or str(uuid.uuid4())[:8]
    data["id"] = preset_id

    existing = next((i for i, p in enumerate(presets) if p["id"] == preset_id), None)
    if existing is not None:
        presets[existing] = data
    else:
        presets.append(data)

    _save_presets(presets)
    return jsonify({"success": True, "id": preset_id})


@presets_bp.route("/<preset_id>", methods=["DELETE"])
def delete_preset(preset_id):
    """Remove um modelo salvo."""
    if not os.path.exists(PRESETS_FILE):
        return jsonify({"error": "Nenhum preset encontrado"}), 404

    presets = [p for p in _load_presets() if p["id"] != preset_id]
    _save_presets(presets)
    return jsonify({"success": True})
