# Backend do Radar Leilão — FastAPI + Alembic (PostgreSQL/pgvector)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências de sistema: curl (health check) e OCR local (Tesseract + idioma
# português + Poppler para converter PDF em imagem). O OCR só é usado quando
# OCR_ENABLED=true; as libs ficam disponíveis para tornar ocr_available()=True.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        tesseract-ocr \
        tesseract-ocr-por \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências primeiro (cache de camada)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Código do backend
COPY backend /app/backend
COPY docker/backend-entrypoint.sh /app/docker/backend-entrypoint.sh
RUN chmod +x /app/docker/backend-entrypoint.sh

# O app é importado como pacote `app` a partir de /app/backend
WORKDIR /app/backend

EXPOSE 8000

ENTRYPOINT ["/app/docker/backend-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
