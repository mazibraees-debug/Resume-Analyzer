FROM python:3.11-slim

WORKDIR /app

# System deps needed by chromadb / sentence-transformers / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY frontend /app/static

ENV PYTHONUNBUFFERED=1 \
    CHROMA_DB_PATH=/app/data/chroma_db \
    UPLOAD_DIR=/app/data/uploads

RUN mkdir -p /app/data/chroma_db /app/data/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
