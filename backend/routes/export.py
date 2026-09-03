"""
Rota de exportacao das coordenadas das caixas posicionadas em CSV.
"""
import csv
import io

from flask import Blueprint, request, jsonify

export_bp = Blueprint("export", __name__, url_prefix="/api")


@export_bp.route("/export-csv", methods=["POST"])
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

    return jsonify({"csv": output.getvalue()})
