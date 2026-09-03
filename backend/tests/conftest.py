"""
Configuracao do pytest.

Adiciona a pasta backend/ ao sys.path para que os testes possam importar
os modulos da aplicacao (models, algorithms, robot, etc.) sem instalar o
projeto como pacote.
"""
import os
import sys

# backend/ e o diretorio pai de tests/
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
