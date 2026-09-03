"""
SoundBox Pallet Optimizer - Backend API

Ponto de entrada da aplicacao Flask. As rotas estao organizadas em blueprints
por dominio, dentro do pacote `routes`. As configuracoes (porta, IP do robo,
etc.) ficam centralizadas em `config.py`.
"""
from flask import Flask, send_from_directory
from flask_cors import CORS

import config
from database import init_db
from routes import register_blueprints

app = Flask(__name__, static_folder="../frontend", static_url_path="")

# CORS so e habilitado se CORS_ORIGINS estiver definida (ver config.py).
if config.CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})

# Inicializa banco de dados
init_db()

# Registra os blueprints de todas as rotas da API
register_blueprints(app)


@app.route("/")
def index():
    """Serve a página principal."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """Serve arquivos estáticos do frontend."""
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG, host=config.HOST, port=config.PORT)
