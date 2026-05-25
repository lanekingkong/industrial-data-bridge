# Dockerfile for Industrial Data Bridge
# Multi-stage build for optimized image size

# ---- Base stage ----
FROM python:3.11-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libsnappy-dev \
    && rm -rf /var/lib/apt/lists/*

# ---- Builder stage ----
FROM base AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --user -r requirements.txt

# ---- Production stage ----
FROM base AS production

WORKDIR /app

# Create non-root user
RUN groupadd -r idb && useradd -r -g idb -s /bin/false idb

# Copy Python packages from builder
COPY --from=builder /root/.local /home/idb/.local
ENV PATH=/home/idb/.local/bin:$PATH

# Copy application code
COPY --chown=idb:idb . .

RUN chmod +x scripts/*.sh

USER idb

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["python", "-m", "src.main"]

# ---- Development stage ----
FROM base AS development

WORKDIR /app

RUN pip install debugpy pytest pytest-asyncio

COPY requirements.txt requirements-dev.txt ./

RUN pip install -r requirements.txt -r requirements-dev.txt

EXPOSE 8000 5678

CMD ["python", "-m", "src.main", "--debug"]