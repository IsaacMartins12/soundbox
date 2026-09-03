"""
Blueprints das rotas da API do SoundBox Pallet Optimizer.

Cada dominio tem seu proprio modulo/blueprint:
    - packing   : calculo de empacotamento (retangular e L)
    - boxes     : CRUD de modelos de caixa
    - pallets   : CRUD de modelos de pallet
    - presets   : CRUD de presets (modelos salvos em JSON)
    - robot     : envio de coordenadas ao robo (variaveis P)
    - export    : exportacao de coordenadas em CSV
"""
from .packing import packing_bp
from .boxes import boxes_bp
from .pallets import pallets_bp
from .presets import presets_bp
from .robot import robot_bp
from .export import export_bp

ALL_BLUEPRINTS = [
    packing_bp,
    boxes_bp,
    pallets_bp,
    presets_bp,
    robot_bp,
    export_bp,
]


def register_blueprints(app):
    """Registra todos os blueprints na aplicacao Flask."""
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
