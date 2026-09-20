# ========================================================
# ChainSentinel — Multi-Stage Production Dockerfile
# NTRO SIH26146: AI-Powered Bitcoin Transaction Monitoring
# Strict Offline / Air-Gapped Single-Port Container
# ========================================================

# --- Stage 1: Build Frontend Assets ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python Backend Runtime ---
FROM python:3.11-slim AS runtime

# System runtime dependencies for scientific computing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/pyproject.toml backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./backend

# Copy application backend source
COPY backend/ /app/backend/
COPY eval/ /app/eval/
COPY data/ /app/data/
COPY scripts/ /app/scripts/

# Copy built frontend static bundle from Stage 1 into frontend/out
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Ensure data and audit directories exist
RUN mkdir -p /app/data/audit /app/data/uploads /app/data/models /app/data/geoip

# Air-gapped single-workstation environment defaults
ENV PYTHONUNBUFFERED=1 \
    CS_AIR_GAPPED=true \
    CS_HOST=0.0.0.0 \
    CS_PORT=8000 \
    CS_FRONTEND_DIR=/app/frontend/out \
    CS_DATA_DIR=/app/data \
    CS_DB_PATH=/app/data/chainsentinel.duckdb \
    CS_GEOIP_DB_PATH=/app/data/geoip/dbip-country-asn-lite.mmdb

EXPOSE 8000

# Healthcheck targeting offline health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Launch unified ASGI application serving API and Static Frontend on port 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
