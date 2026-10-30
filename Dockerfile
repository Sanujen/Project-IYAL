FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    HF_HOME=/app/model_cache \
    DATA_DIR=/app/data \
    LOG_DIR=/app/logs

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-optimized PyTorch first to keep the image lightweight on university servers
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -c "import nltk; nltk.download('words', quiet=True)"

# Copy project source code
COPY iyal_quality_analyzer ./iyal_quality_analyzer
COPY server ./server
COPY setup.py README.md ./

# Create persistent directories for SQLite DB, logs, and HuggingFace model cache
RUN mkdir -p /app/data /app/logs /app/model_cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${SERVER_PORT:-8000}/api/v1/health || exit 1

CMD ["sh", "-c", "uvicorn server.server:app --host 0.0.0.0 --port ${SERVER_PORT:-8000}"]
