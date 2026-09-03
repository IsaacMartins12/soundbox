"""
Rotas de CRUD dos modelos de pallet cadastrados no banco.
"""
from flask import Blueprint, request, jsonify

from database import get_all_pallets, create_pallet, delete_pallet

pallets_bp = Blueprint("pallets", __name__, url_prefix="/api/pallets-db")


@pallets_bp.route("", methods=["GET"])
def list_pallets_db():
    """Lista todos os modelos de pallet cadastrados."""
    return jsonify(get_all_pallets())


@pallets_bp.route("", methods=["POST"])
def add_pallet_db():
    """Cadastra um novo modelo de pallet."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Campo 'name' é obrigatório"}), 400
    new_id = create_pallet(data)
    return jsonify({"success": True, "id": new_id})


@pallets_bp.route("/<int:pallet_id>", methods=["DELETE"])
def remove_pallet_db(pallet_id):
    """Remove um modelo de pallet."""
    delete_pallet(pallet_id)
    return jsonify({"success": True})
