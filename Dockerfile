# Build context is the repo root. docker-compose uses backend/Dockerfile instead.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Cloud Run sets PORT (default 8080). Local leaves unset → 8000.
EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
