"""
Rotas de calculo de empacotamento (caixas retangulares e formato L).
"""
from flask import Blueprint, request, jsonify

from models.pallet import Pallet
from algorithms.packer import pack_pallet
from algorithms.packer_L import pack_pallet_L
from ._helpers import parse_pallet, parse_cases, ValidationError

packing_bp = Blueprint("packing", __name__, url_prefix="/api")


@packing_bp.route("/calculate", methods=["POST"])
def calculate():
    """Endpoint principal de calculo (caixas retangulares)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON é obrigatório"}), 400

    try:
        pallet_size, max_weight = parse_pallet(data.get("pallet"))
        validated_cases = parse_cases(data.get("cases"))
    except ValidationError as e:
        return jsonify({"error": e.message}), 400

    overhang = float(data.get("overhang", 5.0))

    pallet = Pallet(pallet_size, max_weight)
    result = pack_pallet(pallet, validated_cases, overhang=overhang)

    response = result.to_dict()
    response["requested_cases"] = sum(c["quantity"] for c in validated_cases)

    return jsonify(response)


@packing_bp.route("/calculate-l", methods=["POST"])
def calculate_l():
    """Endpoint para calculo com caixas em formato L."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON é obrigatório"}), 400

    l_box_data = data.get("l_box")
    regular_box_data = data.get("regular_box")

    if not l_box_data:
        return jsonify({"error": "Campo 'l_box' é obrigatório"}), 400

    try:
        pallet_size, max_weight = parse_pallet(data.get("pallet"), default_max_weight=99999)
    except ValidationError as e:
        return jsonify({"error": e.message}), 400

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

    overhang = float(data.get("overhang", 0))
    result_l = pack_pallet_L(
        pallet_size=pallet_size,
        l_dims=l_dims,
        quantidade=l_quantity,
        peso_caixa=l_weight,
        max_weight=max_weight,
        overhang=overhang,
    )

    # Caixa retangular opcional
    result_regular = None
    if regular_box_data and int(regular_box_data.get("quantity", 0)) > 0:
        overhang_reg = float(data.get("overhang", 5.0))
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
        pallet_result = pack_pallet(pallet_obj, cases_input, overhang=overhang_reg)
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
