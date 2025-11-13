# Optimized Dockerfile for Railway (CPU-only PyTorch for smaller size)

FROM python:3.11-slim

WORKDIR /app

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies with CPU-only PyTorch (much smaller!)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.0.0+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html && \
    pip install --no-cache-dir \
    fastapi==0.115.5 \
    uvicorn[standard]==0.32.1 \
    pydantic==2.10.2 \
    pydantic-settings==2.6.1 \
    groq>=0.9.0 \
    sentence-transformers==3.3.1 \
    chromadb==0.5.23 \
    rank-bm25==0.2.2 \
    httpx==0.28.0 \
    python-dotenv==1.0.1 \
    python-multipart==0.0.19 \
    structlog==24.4.0 && \
    pip cache purge

# Set environment variables
ENV TOKENIZERS_PARALLELISM=false \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# Copy application code
COPY app/ ./app/
COPY .env.example .env
COPY data/messages_backup.json ./data/messages_backup.json

# Create data directory
RUN mkdir -p /app/data/chromadb

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests, os; requests.get(f'http://localhost:{os.getenv(\"PORT\", \"8000\")}/health', timeout=5)" || exit 1

# Run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

