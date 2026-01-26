# ============================================================================
# LiteLLM Production Dockerfile
# ============================================================================
# Multi-stage build for optimal image size and security.
#
# BUILD:
#   docker build -t litellm-custom:latest .
#
# RUN (standalone):
#   docker run -p 4000:4000 -v $(pwd)/config.yaml:/app/config.yaml litellm-custom:latest
#
# WITH COMPOSE:
#   docker-compose build litellm
#   docker-compose up -d litellm
# ============================================================================

# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:3.12-slim AS builder

# Set build arguments for version pinning
ARG LITELLM_VERSION=latest-main

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install LiteLLM - this pulls all core dependencies
# Using the official image as base, but adding custom components
COPY requirements.txt* /tmp/

# Install LiteLLM - this pulls all core dependencies
RUN pip install --upgrade pip && \
    pip install "litellm[proxy]" && \
    pip install prisma && \
    pip freeze > /tmp/requirements.txt

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.12-slim AS runtime

# Metadata
LABEL maintainer="litellm-ops" \
      description="LiteLLM Proxy - Production Build" \
      version="1.0.0"

# Security: Run as non-root user
RUN groupadd -r litellm && useradd -r -g litellm -u 1000 litellm

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    ca-certificates \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app:$PYTHONPATH" \
    LITELLM_MODE=PRODUCTION

# Create application directory structure
WORKDIR /app
RUN mkdir -p /app/state/files /app/logs /app/migrations && \
    chown -R litellm:litellm /app

# Copy application files
COPY --chown=litellm:litellm config.yaml schema.prisma ./
COPY --chown=litellm:litellm migrations/ ./migrations/
COPY --chown=litellm:litellm model_cost_map.local.json* ./

# Copy custom scripts/bin if they exist
COPY --chown=litellm:litellm bin/ ./bin/

# Set Prisma environment variables
ENV PRISMA_PYTHON_BINARIES_CACHE_DIR=/home/litellm/.cache/prisma-python
ENV PRISMA_BINARY_CACHE_DIR=/home/litellm/.cache/prisma-python

# Generate Prisma client and ensure home directory permissions
RUN mkdir -p /home/litellm/.cache/prisma-python && \
    prisma generate && \
    chown -R litellm:litellm /home/litellm

# Switch to non-root user
USER litellm

# Expose LiteLLM port
EXPOSE 4000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:4000/healthz || exit 1

# Default entrypoint
ENTRYPOINT ["litellm"]

# Default arguments - can be overridden in docker-compose
CMD ["--port", "4000", "--config", "/app/config.yaml", "--num_workers", "4", "--run_gunicorn", "--max_requests_before_restart", "10000", "--host", "0.0.0.0"]
