"""
Configuracao central do SoundBox Pallet Optimizer.

Concentra em um unico lugar os valores importantes (IP do robo, porta, faixa de
variaveis P, orientacao da garra, etc.), evitando edita-los espalhados pelo
codigo.

Cada valor pode ser sobrescrito por variavel de ambiente, mas os defaults aqui
sao os usados em operacao. Para trocar o IP do robo, por exemplo, basta editar
ROBOT_IP abaixo ou definir a variavel de ambiente ROBOT_IP.
"""
import os


def _env_str(name, default):
    val = os.environ.get(name)
    return val if val is not None else default


def _env_int(name, default):
    val = os.environ.get(name)
    return int(val) if val is not None else default


def _env_float(name, default):
    val = os.environ.get(name)
    return float(val) if val is not None else default


def _env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Servidor Flask
# ---------------------------------------------------------------------------
FLASK_DEBUG = _env_bool("FLASK_DEBUG", default=False)
HOST = _env_str("HOST", "0.0.0.0")
PORT = _env_int("PORT", 5000)

# Origens permitidas para CORS (lista). Vazio = CORS desabilitado.
# O frontend e servido pelo proprio Flask (mesma origem), entao por padrao
# nao precisamos de CORS.
_cors_raw = os.environ.get("CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# Robo Yaskawa YRC1000
# ---------------------------------------------------------------------------
# Rede
ROBOT_IP = _env_str("ROBOT_IP", "192.168.0.80")
ROBOT_PORT = _env_int("ROBOT_PORT", 10040)          # porta HSES (robot control)
ROBOT_TIMEOUT = _env_float("ROBOT_TIMEOUT", 2.0)    # timeout de resposta (s)

# Variaveis de posicao (P)
# A primeira variavel P usada no envio das coordenadas. Com inicio em P110,
# cabem ate 18 caixas (P110 a P127).
ROBOT_START_PVAR = _env_int("ROBOT_START_PVAR", 110)
ROBOT_MAX_PVAR = _env_int("ROBOT_MAX_PVAR", 127)

# Sistema de coordenadas: 16=base, 17=robo, 18=usuario, 19=ferramenta
ROBOT_COORD_SYSTEM = _env_int("ROBOT_COORD_SYSTEM", 17)

# Numero da ferramenta (0 a 63)
ROBOT_TOOL_NO = _env_int("ROBOT_TOOL_NO", 0)

# Orientacao padrao da garra (graus). O robo pega por cima, entao a garra
# aponta para baixo -> Rx = 180.
ROBOT_RX = _env_float("ROBOT_RX", 180.0)
ROBOT_RY = _env_float("ROBOT_RY", 0.0)
ROBOT_RZ = _env_float("ROBOT_RZ", 0.0)
