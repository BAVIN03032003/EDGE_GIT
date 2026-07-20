#!/bin/bash
set -e

VERSION="${VERSION:-latest}"
REGISTRY="${REGISTRY:-ghcr.io}"
ORG="${ORG:-teampresence-production}"
IMAGE_NAME="${IMAGE_NAME:-gitaction-edge}"
CONTAINER_NAME="${CONTAINER_NAME:-edge-app}"
ENV_FILE="${ENV_FILE:-/opt/edge/.env}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-5001}"

pull_image() {
    echo "[INFO] Pulling image: ${REGISTRY}/${ORG}/${IMAGE_NAME}:${VERSION}"
    docker pull "${REGISTRY}/${ORG}/${IMAGE_NAME}:${VERSION}"
}

stop_container() {
    echo "[INFO] Stopping existing container..."
    docker stop "${CONTAINER_NAME}" 2>/dev/null || true
    docker rm "${CONTAINER_NAME}" 2>/dev/null || true
}

start_container() {
    echo "[INFO] Starting container with image: ${REGISTRY}/${ORG}/${IMAGE_NAME}:${VERSION}"

    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        --env-file "${ENV_FILE}" \
        -v "${ENV_FILE}:/app/.env" \
        -v "${ENV_FILE}:/app/backend/.env" \
        -p "${FRONTEND_PORT}:3000" \
        -p "${BACKEND_PORT}:5001" \
        -v /opt/edge/logs:/app/logs \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        --label "edge.version=${VERSION}" \
        --label "edge.updated=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        "${REGISTRY}/${ORG}/${IMAGE_NAME}:${VERSION}"
}

verify_container() {
    echo "[INFO] Verifying container is running..."
    sleep 5

    if docker ps | grep -q "${CONTAINER_NAME}"; then
        echo "[SUCCESS] Container is running"
        docker logs "${CONTAINER_NAME}" | tail -20
        return 0
    else
        echo "[ERROR] Container failed to start"
        docker logs "${CONTAINER_NAME}" | tail -50
        return 1
    fi
}

rollback_container() {
    echo "[INFO] Rolling back to previous version..."
    docker logs "${CONTAINER_NAME}" > /opt/edge/logs/rollback-$(date +%Y%m%d_%H%M%S).log 2>&1 || true
    stop_container
}

case "${1:-start}" in
    start)
        pull_image
        stop_container
        start_container
        verify_container
        ;;
    stop)
        stop_container
        echo "[INFO] Container stopped"
        ;;
    restart)
        stop_container
        pull_image
        start_container
        verify_container
        ;;
    pull)
        pull_image
        ;;
    logs)
        docker logs -f "${CONTAINER_NAME}"
        ;;
    status)
        docker ps -a | grep "${CONTAINER_NAME}" || echo "Container not found"
        ;;
    rollback)
        if [ -z "${2}" ]; then
            echo "[ERROR] Please specify version to rollback to: $0 rollback <version>"
            exit 1
        fi
        VERSION="${2}" pull_image
        rollback_container
        start_container
        verify_container
        ;;
    update)
        pull_image
        stop_container
        start_container
        verify_container
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|pull|logs|status|rollback <version>|update}"
        exit 1
        ;;
esac
