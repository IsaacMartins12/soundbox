"""
Envio das coordenadas de paletizacao para as variaveis de posicao (P) do YRC1000.

Pega o resultado do calculo (caixas com place_x, place_y, place_z em cm) e
escreve cada caixa em uma variavel P sequencial, comecando em P110 (default).

    caixa 1 (index 1) -> P110
    caixa 2 (index 2) -> P111
    caixa 3 (index 3) -> P112
    ...

Com inicio em P110, cabem ate 18 caixas (P110 a P127).

Os valores default (IP, porta, faixa de P, orientacao) vem de config.py.

Conversao de unidades:
    - O calculo esta em CENTIMETROS. O robo trabalha em MILIMETROS.
    - Multiplicamos por 10 (cm -> mm). O hses_client converte mm -> μm.

Uso programatico:
    from robot.pallet_sender import send_pallet_to_robot
    resultado = send_pallet_to_robot(cases)
"""
import config
from .hses_client import HSESClient


def send_pallet_to_robot(cases, ip=None, start_pvar=None,
                         coord_system=None, tool_no=None,
                         rx=None, ry=None, rz=None):
    """Escreve as coordenadas de cada caixa em variaveis P sequenciais.

    Os parametros default vem de config.py; passe valores explicitos apenas
    para sobrescrever pontualmente.

    :param cases: lista de caixas (dicts com place_x, place_y, place_z em cm)
    :param ip: IP do controlador YRC1000
    :param start_pvar: numero da primeira variavel P
    :param coord_system: 16=base, 17=robo, 18=usuario
    :param tool_no: numero da ferramenta
    :param rx, ry, rz: orientacao da garra em graus
    :return: dict com resumo do envio (enviadas, falhas, detalhes)
    """
    # Aplica defaults do config quando nao especificado
    ip = ip if ip is not None else config.ROBOT_IP
    start_pvar = start_pvar if start_pvar is not None else config.ROBOT_START_PVAR
    coord_system = coord_system if coord_system is not None else config.ROBOT_COORD_SYSTEM
    tool_no = tool_no if tool_no is not None else config.ROBOT_TOOL_NO
    rx = rx if rx is not None else config.ROBOT_RX
    ry = ry if ry is not None else config.ROBOT_RY
    rz = rz if rz is not None else config.ROBOT_RZ

    robot = HSESClient(ip, timeout=config.ROBOT_TIMEOUT, port=config.ROBOT_PORT)

    enviadas = 0
    falhas = 0
    detalhes = []

    # Ordena por index para garantir a sequencia P110, P111, ...
    cases_ordenadas = sorted(cases, key=lambda c: c.get("index", 0))

    for i, case in enumerate(cases_ordenadas):
        pvar = start_pvar + i

        if pvar > config.ROBOT_MAX_PVAR:
            detalhes.append({
                "index": case.get("index"),
                "pvar": pvar,
                "ok": False,
                "motivo": f"Numero de P excede o limite ({config.ROBOT_MAX_PVAR})",
            })
            falhas += 1
            continue

        # cm -> mm
        x_mm = case["place_x"] * 10.0
        y_mm = case["place_y"] * 10.0
        z_mm = case["place_z"] * 10.0

        ok = robot.write_position(
            pvar,
            x_mm=x_mm, y_mm=y_mm, z_mm=z_mm,
            tx_deg=rx, ty_deg=ry, tz_deg=rz,
            data_type=coord_system, tool_no=tool_no,
        )

        detalhes.append({
            "index": case.get("index"),
            "code": case.get("code"),
            "pvar": pvar,
            "x_mm": round(x_mm, 1),
            "y_mm": round(y_mm, 1),
            "z_mm": round(z_mm, 1),
            "ok": ok,
            "errno": hex(robot.errno) if not ok else None,
        })

        if ok:
            enviadas += 1
        else:
            falhas += 1

    return {
        "success": falhas == 0,
        "total": len(cases_ordenadas),
        "enviadas": enviadas,
        "falhas": falhas,
        "start_pvar": start_pvar,
        "end_pvar": start_pvar + len(cases_ordenadas) - 1,
        "detalhes": detalhes,
    }
