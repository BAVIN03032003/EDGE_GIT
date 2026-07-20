#!/bin/bash
# update-edge.sh - Manual Update for Edge Collector on Linux

log_info() { echo -e "\033[0;36m[INFO] $1\033[0m"; }
log_success() { echo -e "\033[0;32m[SUCCESS] $1\033[0m"; }

log_info "Checking for Edge application updates..."

# Pull latest images
if command -v docker-compose &> /dev/null; then
    docker-compose pull
    docker-compose up -d --remove-orphans
else
    docker compose pull
    docker compose up -d --remove-orphans
fi

log_success "Update process completed. Checking container status..."
docker ps --filter "name=edge-app" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
