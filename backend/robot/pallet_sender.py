"""
Envio das coordenadas de paletizacao para as variaveis de posicao (P) do YRC1000.

Pega o resultado do calculo (caixas com place_x, place_y, place_z em cm) e
escreve cada caixa em uma variavel P sequencial, comecando em P110.

    caixa 1 (index 1) -> P110
    caixa 2 (index 2) -> P111
    caixa 3 (index 3) -> P112
    ...

Com inicio em P110, cabem ate 18 caixas (P110 a P127).

Conversao de unidades:
    - O calculo esta em CENTIMETROS. O robo trabalha em MILIMETROS.
    - Multiplicamos por 10 (cm -> mm). O hses_client converte mm -> μm.

Uso programatico:
    from robot.pallet_sender import send_pallet_to_robot
    resultado = send_pallet_to_robot(cases, ip="192.168.0.80", start_pvar=120)
"""
from .hses_client import HSESClient


# Numero da primeira variavel P a ser usada
DEFAULT_START_PVAR = 110

# Orientacao padrao da ferramenta (graus). O robo pega por cima, entao a
# garra aponta para baixo -> Rx = 180. Ajustavel conforme calibracao.
DEFAULT_RX = 180.0
DEFAULT_RY = 0.0
DEFAULT_RZ = 0.0


def send_pallet_to_robot(cases, ip="192.168.0.80", start_pvar=DEFAULT_START_PVAR,
                         coord_system=HSESClient.COORD_ROBOT, tool_no=0,
                         rx=DEFAULT_RX, ry=DEFAULT_RY, rz=DEFAULT_RZ):
    """Escreve as coordenadas de cada caixa em variaveis P sequenciais.

    :param cases: lista de caixas (dicts com place_x, place_y, place_z em cm)
    :param ip: IP do controlador YRC1000
    :param start_pvar: numero da primeira variavel P (default 110)
    :param coord_system: 16=base, 17=robo, 18=usuario
    :param tool_no: numero da ferramenta
    :param rx, ry, rz: orientacao da garra em graus
    :return: dict com resumo do envio (enviadas, falhas, detalhes)
    """
    robot = HSESClient(ip)

    enviadas = 0
    falhas = 0
    detalhes = []

    # Ordena por index para garantir a sequencia P120, P121, ...
    cases_ordenadas = sorted(cases, key=lambda c: c.get("index", 0))

    if len(cases_ordenadas) > 128:
        return {
            "success": False,
            "error": f"{len(cases_ordenadas)} caixas excede o limite de variaveis P (128).",
        }

    for i, case in enumerate(cases_ordenadas):
        pvar = start_pvar + i

        if pvar > 127:
            detalhes.append({
                "index": case.get("index"),
                "pvar": pvar,
                "ok": False,
                "motivo": "Numero de P excede 127",
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
