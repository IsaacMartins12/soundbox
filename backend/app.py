"""
SoundBox Pallet Optimizer - Backend API

Ponto de entrada da aplicacao Flask. As rotas estao organizadas em blueprints
por dominio, dentro do pacote `routes`.

Configuracao por variaveis de ambiente:
    FLASK_DEBUG      : "1"/"true" para ligar o modo debug (default: desligado)
    HOST             : host de bind (default: 0.0.0.0)
    PORT             : porta (default: 5000)
    CORS_ORIGINS     : origens permitidas separadas por virgula.
                       Se nao definida, o CORS nao e habilitado (o frontend e
                       servido pelo proprio Flask, na mesma origem).
"""
import os

from flask import Flask, send_from_directory
from flask_cors import CORS

from database import init_db
from routes import register_blueprints


def _env_bool(name, default=False):
    """Le uma variavel de ambiente como booleano."""
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


app = Flask(__name__, static_folder="../frontend", static_url_path="")

# CORS so e habilitado se CORS_ORIGINS for definida. Como o frontend e servido
# pelo proprio Flask (mesma origem), por padrao nao precisamos de CORS aberto.
_cors_origins = os.environ.get("CORS_ORIGINS")
if _cors_origins:
    origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}})

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
    debug = _env_bool("FLASK_DEBUG", default=False)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, host=host, port=port)
