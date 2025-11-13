# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set environment variables for production
ENV TOKENIZERS_PARALLELISM=false
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY app/ ./app/
COPY .env.example .env

# Copy message backup for cold starts (when API is down)
COPY data/messages_backup.json ./data/messages_backup.json

# Create data directory for ChromaDB (ephemeral on Railway)
RUN mkdir -p /app/data/chromadb

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Health check (using Railway's $PORT if available)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests, os; requests.get(f'http://localhost:{os.getenv(\"PORT\", \"8000\")}/health', timeout=5)"

# Run the application (Railway will set $PORT, default to 8000)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

