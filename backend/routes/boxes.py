"""
Rotas de CRUD dos modelos de caixa cadastrados no banco.
"""
from flask import Blueprint, request, jsonify

from database import get_all_boxes, create_box, update_box, delete_box

boxes_bp = Blueprint("boxes", __name__, url_prefix="/api/boxes")


@boxes_bp.route("", methods=["GET"])
def list_boxes():
    """Lista todos os modelos de caixa cadastrados."""
    return jsonify(get_all_boxes())


@boxes_bp.route("", methods=["POST"])
def add_box():
    """Cadastra um novo modelo de caixa."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400
    new_id = create_box(data)
    return jsonify({"success": True, "id": new_id})


@boxes_bp.route("/<int:box_id>", methods=["PUT"])
def edit_box(box_id):
    """Atualiza um modelo de caixa existente."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400
    update_box(box_id, data)
    return jsonify({"success": True})


@boxes_bp.route("/<int:box_id>", methods=["DELETE"])
def remove_box(box_id):
    """Remove um modelo de caixa."""
    delete_box(box_id)
    return jsonify({"success": True})
