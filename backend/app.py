"""
SoundBox Pallet Optimizer - Backend API

Ponto de entrada da aplicacao Flask. As rotas estao organizadas em blueprints
por dominio, dentro do pacote `routes`.
"""
from flask import Flask, send_from_directory
from flask_cors import CORS

from database import init_db
from routes import register_blueprints

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

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
    app.run(debug=True, host="0.0.0.0", port=5000)
