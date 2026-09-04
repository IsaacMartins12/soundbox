# Imagem do SoundBox Pallet Optimizer (backend Flask + frontend estatico)
FROM python:3.12-slim

# Evita .pyc e garante logs sem buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependencias primeiro (aproveita cache de camadas)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copia o codigo (backend + frontend)
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# O app roda a partir de backend/ (imports relativos: config, routes, etc.)
WORKDIR /app/backend

# O banco SQLite fica aqui; monte um volume para persistir entre execucoes
VOLUME ["/app/backend/data"]
ENV DB_PATH=/app/backend/data/soundbox.db

EXPOSE 5000

# Servidor WSGI de producao. 'app:app' = objeto Flask 'app' no modulo app.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
