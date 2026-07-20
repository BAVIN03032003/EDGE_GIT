# syntax=docker/dockerfile:1.7

# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY my-app/package*.json ./
RUN npm install --quiet
COPY my-app/ ./
RUN npm run build

# --- Stage 2: Compile Backend ---
FROM python:3.11-slim-bookworm AS backend-builder

# Install build dependencies for Nuitka
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    patchelf \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python requirements first for better caching
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "nuitka[onefile]" zstandard

# Copy backend source
COPY backend/ ./

# Compile into a standalone onefile binary
# Optimized with --jobs for parallel compilation
RUN python -m nuitka \
    --standalone \
    --onefile \
    --include-package=plugin \
    --include-package=services \
    --include-package=utils \
    --include-package=routes \
    --include-package=executors \
    --output-filename=edge-app-binary \
    --remove-output \
    --jobs=$(nproc) \
    main.py

# --- Stage 3: Final Runtime ---
FROM debian:bookworm-slim AS runtime

# Install minimal runtime dependencies (ca-certificates for HTTPS and nginx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    iputils-ping \
    net-tools \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --uid 1000 --create-home --shell /bin/bash edgeuser

WORKDIR /app

# Copy only the compiled binary
COPY --from=backend-builder --chown=edgeuser:edgeuser /build/edge-app-binary /app/edge-app-binary

# Copy frontend build assets
COPY --from=frontend-builder --chown=edgeuser:edgeuser /frontend/build /usr/share/nginx/html

# Copy Nginx config and entrypoint
COPY nginx.conf /etc/nginx/nginx.conf
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && chown edgeuser:edgeuser /app/docker-entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs && chown -R edgeuser:edgeuser /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV WEB_UI_PORT=5001
ENV DOCKER_CONTAINER=true

USER edgeuser

EXPOSE 3000 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["/app/edge-app-binary", "--health"]

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
