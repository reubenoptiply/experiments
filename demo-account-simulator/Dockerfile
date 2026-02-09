FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Use shell so Cloud Run's PORT env var is respected (default 8080)
CMD ["/bin/sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
