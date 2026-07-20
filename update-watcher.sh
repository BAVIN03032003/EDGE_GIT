#!/bin/bash
set -e

CONTAINER_NAME="${CONTAINER_NAME:-edge-app}"
UPDATE_PENDING_FILE="/opt/edge/update-pending"
ROLLBACK_PENDING_FILE="/opt/edge/rollback-pending"
UPDATE_LOG="/opt/edge/logs/update-watcher.log"
CHECK_INTERVAL=10

log() {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [WATCHER] $1" | tee -a "${UPDATE_LOG}"
}

wait_for_container_stable() {
    log "Waiting for current container to stabilize..."
    local max_wait=30
    local waited=0

    while [ $waited -lt $max_wait ]; do
        local status=$(docker inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "not_found")

        if [ "$status" == "running" ]; then
            local restart_count=$(docker inspect -f '{{.RestartCount}}' "${CONTAINER_NAME}" 2>/dev/null || echo "0")
            if [ "$restart_count" -eq 0 ]; then
                log "Container is stable"
                return 0
            fi
        fi

        sleep 2
        waited=$((waited + 2))
    done

    log "Warning: Container did not stabilize within ${max_wait}s"
    return 1
}

apply_update() {
    local new_version="$1"
    local new_image="$2"

    log "Applying update to version: ${new_version}"

    wait_for_container_stable || true

    log "Pulling new image..."
    docker pull "${new_image}" || {
        log "ERROR: Failed to pull image"
        return 1
    }

    log "Stopping current container..."
    docker stop "${CONTAINER_NAME}" || true

    log "Starting new container with version: ${new_version}"
    /opt/edge/start.sh update || {
        log "ERROR: Failed to start new container, initiating rollback"
        apply_rollback "${new_version}"
        return 1
    }

    sleep 10

    local new_status=$(docker inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "not_found")
    if [ "$new_status" == "running" ]; then
        log "SUCCESS: Container updated to version ${new_version}"

        curl -X POST "${CLOUD_URL}/api/edge/update-confirm" \
            -H "Content-Type: application/json" \
            -d "{\"version\": \"${new_version}\", \"edge_id\": \"${EDGE_ID}\"}" || true

        rm -f "${UPDATE_PENDING_FILE}"
        return 0
    else
        log "ERROR: Container failed to start properly"
        apply_rollback "${new_version}"
        return 1
    fi
}

apply_rollback() {
    local failed_version="$1"
    local previous_version="$2"

    log "Initiating rollback from version: ${failed_version}"

    if [ -z "${previous_version}" ]; then
        previous_version=$(docker images --format '{{.Tag}}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | head -1)
        log "Detected previous version: ${previous_version}"
    fi

    if [ -z "${previous_version}" ]; then
        log "ERROR: No previous version found for rollback"
        return 1
    fi

    docker logs "${CONTAINER_NAME}" > /opt/edge/logs/failed-$(date +%Y%m%d_%H%M%S).log 2>&1 || true

    docker stop "${CONTAINER_NAME}" 2>/dev/null || true
    docker rm "${CONTAINER_NAME}" 2>/dev/null || true

    log "Rolling back to version: ${previous_version}"
    VERSION="${previous_version}" /opt/edge/start.sh start || {
        log "CRITICAL: Rollback failed"
        return 1
    }

    sleep 10

    local status=$(docker inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "not_found")
    if [ "$status" == "running" ]; then
        log "SUCCESS: Rolled back to version ${previous_version}"

        curl -X POST "${CLOUD_URL}/api/edge/update-failed" \
            -H "Content-Type: application/json" \
            -d "{\"attempted_version\": \"${failed_version}\", \"reason\": \"Container failed to start\", \"edge_id\": \"${EDGE_ID}\"}" || true

        rm -f "${UPDATE_PENDING_FILE}"
        rm -f "${ROLLBACK_PENDING_FILE}"
        return 0
    else
        log "CRITICAL: Both update and rollback failed"
        return 1
    fi
}

main() {
    log "Update watcher started (PID: $$)"
    log "Watching for update files in /opt/edge/"

    while true; do
        if [ -f "${UPDATE_PENDING_FILE}" ]; then
            log "Update pending file detected"

            local version=$(cat "${UPDATE_PENDING_FILE}" | jq -r '.version // empty')
            local image=$(cat "${UPDATE_PENDING_FILE}" | jq -r '.image // empty')

            if [ -n "${version}" ] && [ -n "${image}" ]; then
                apply_update "${version}" "${image}"
            else
                log "ERROR: Invalid update-pending file format"
                rm -f "${UPDATE_PENDING_FILE}"
            fi
        fi

        if [ -f "${ROLLBACK_PENDING_FILE}" ]; then
            log "Rollback pending file detected"

            local current_version=$(cat "${ROLLBACK_PENDING_FILE}" | jq -r '.current_version // empty')
            local previous_version=$(cat "${ROLLBACK_PENDING_FILE}" | jq -r '.previous_version // empty')

            if [ -n "${previous_version}" ]; then
                apply_rollback "${current_version}" "${previous_version}"
            else
                log "ERROR: Invalid rollback-pending file format"
                rm -f "${ROLLBACK_PENDING_FILE}"
            fi
        fi

        sleep "${CHECK_INTERVAL}"
    done
}

trap 'log "Watcher stopped"; exit 0' INT TERM

main
