"""
Testes do envio de coordenadas ao robo (pallet_sender).

Usa um cliente HSES "fake" (monkeypatch) para capturar as chamadas de escrita
sem precisar de rede nem do robo real. Foco: conversao cm->mm, sequencia de
variaveis P e limite de P.
"""
import config
from robot import pallet_sender


class FakeHSESClient:
    """Substitui o HSESClient real: registra as posicoes escritas."""

    def __init__(self, ip, timeout=None, port=None):
        self.ip = ip
        self.errno = 0
        self.escritas = []

    def write_position(self, num, x_mm, y_mm, z_mm, tx_deg, ty_deg, tz_deg,
                       data_type, tool_no):
        self.escritas.append({
            "pvar": num, "x_mm": x_mm, "y_mm": y_mm, "z_mm": z_mm,
            "tx": tx_deg, "ty": ty_deg, "tz": tz_deg,
            "data_type": data_type, "tool_no": tool_no,
        })
        return True


def install_fake(monkeypatch):
    """Instala o cliente fake e devolve a instancia usada."""
    instancias = []

    def factory(ip, timeout=None, port=None):
        c = FakeHSESClient(ip, timeout, port)
        instancias.append(c)
        return c

    monkeypatch.setattr(pallet_sender, "HSESClient", factory)
    return instancias


def test_converte_cm_para_mm(monkeypatch):
    instancias = install_fake(monkeypatch)
    cases = [{"index": 1, "code": "A", "place_x": 80.0, "place_y": -30.0, "place_z": 52.0}]

    result = pallet_sender.send_pallet_to_robot(cases)

    assert result["success"] is True
    assert result["enviadas"] == 1
    escrita = instancias[0].escritas[0]
    # cm * 10 = mm
    assert escrita["x_mm"] == 800.0
    assert escrita["y_mm"] == -300.0
    assert escrita["z_mm"] == 520.0


def test_sequencia_de_pvars_comeca_no_config(monkeypatch):
    instancias = install_fake(monkeypatch)
    cases = [
        {"index": 1, "place_x": 10, "place_y": 10, "place_z": 5},
        {"index": 2, "place_x": 20, "place_y": 10, "place_z": 5},
        {"index": 3, "place_x": 30, "place_y": 10, "place_z": 5},
    ]

    result = pallet_sender.send_pallet_to_robot(cases)

    pvars = [e["pvar"] for e in instancias[0].escritas]
    esperado = [config.ROBOT_START_PVAR + i for i in range(3)]
    assert pvars == esperado
    assert result["start_pvar"] == config.ROBOT_START_PVAR
    assert result["end_pvar"] == config.ROBOT_START_PVAR + 2


def test_ordena_por_index(monkeypatch):
    instancias = install_fake(monkeypatch)
    # entrada fora de ordem
    cases = [
        {"index": 3, "place_x": 30, "place_y": 0, "place_z": 0},
        {"index": 1, "place_x": 10, "place_y": 0, "place_z": 0},
        {"index": 2, "place_x": 20, "place_y": 0, "place_z": 0},
    ]

    pallet_sender.send_pallet_to_robot(cases)

    xs = [e["x_mm"] for e in instancias[0].escritas]
    # deve escrever na ordem do index: 10, 20, 30 cm -> 100, 200, 300 mm
    assert xs == [100.0, 200.0, 300.0]


def test_excede_limite_de_pvar_marca_falha(monkeypatch):
    install_fake(monkeypatch)
    # start default (110) + muitas caixas ultrapassa ROBOT_MAX_PVAR (127)
    n = (config.ROBOT_MAX_PVAR - config.ROBOT_START_PVAR) + 3  # 3 alem do limite
    cases = [{"index": i + 1, "place_x": 1, "place_y": 1, "place_z": 1} for i in range(n)]

    result = pallet_sender.send_pallet_to_robot(cases)

    # as que passaram do limite contam como falha
    assert result["falhas"] >= 1
    assert result["success"] is False
