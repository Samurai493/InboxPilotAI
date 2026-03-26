FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run sets PORT (default 8080). Local/docker-compose leaves it unset → 8000.
EXPOSE 8080

# Shell form so ${PORT:-8000} is expanded
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
