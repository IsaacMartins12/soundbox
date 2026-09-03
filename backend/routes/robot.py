"""
Rota de envio das coordenadas de paletizacao para o robo (variaveis P via HSES).
"""
from flask import Blueprint, request, jsonify

from robot.pallet_sender import send_pallet_to_robot, DEFAULT_START_PVAR

robot_bp = Blueprint("robot", __name__, url_prefix="/api")


@robot_bp.route("/send-to-robot", methods=["POST"])
def send_to_robot():
    """
    Envia as coordenadas das caixas calculadas para as variaveis P do robo.

    Escreve caixa 1 -> P110, caixa 2 -> P111, ... (sequencial).

    Body JSON esperado:
    {
        "cases": [ { "index": 1, "place_x": ..., "place_y": ..., "place_z": ... }, ... ],
        "ip": "192.168.0.80",        // opcional
        "start_pvar": 110,           // opcional
        "coord_system": 17,          // opcional (16=base 17=robo 18=usuario)
        "tool_no": 0,                // opcional
        "rx": 180, "ry": 0, "rz": 0  // opcional (orientacao da garra)
    }
    """
    data = request.get_json()
    if not data or "cases" not in data:
        return jsonify({"error": "Campo 'cases' é obrigatório"}), 400

    cases = data["cases"]
    if not cases:
        return jsonify({"error": "Nenhuma caixa para enviar"}), 400

    # Valida que as caixas tem as coordenadas de place
    for c in cases:
        if "place_x" not in c or "place_y" not in c or "place_z" not in c:
            return jsonify({"error": "Caixas sem coordenadas de place (place_x/y/z)"}), 400

    ip = data.get("ip", "192.168.0.80")
    start_pvar = int(data.get("start_pvar", DEFAULT_START_PVAR))
    coord_system = int(data.get("coord_system", 17))
    tool_no = int(data.get("tool_no", 0))
    rx = float(data.get("rx", 180.0))
    ry = float(data.get("ry", 0.0))
    rz = float(data.get("rz", 0.0))

    try:
        resultado = send_pallet_to_robot(
            cases, ip=ip, start_pvar=start_pvar,
            coord_system=coord_system, tool_no=tool_no,
            rx=rx, ry=ry, rz=rz,
        )
    except OSError as e:
        return jsonify({
            "success": False,
            "error": f"Falha de comunicação com o robô ({ip}): {str(e)}",
        }), 502

    return jsonify(resultado)
