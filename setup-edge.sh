#!/bin/bash
# setup-edge.sh - Automated Setup for Edge Collector on Linux

EDGE_HOME="/opt/edge"
LOGS_DIR="$EDGE_HOME/logs"
ENV_FILE="$EDGE_HOME/.env"
AUTH_FILE="$(pwd)/watchtower-auth.json"

log_info() { echo -e "\033[0;36m[INFO] $1\033[0m"; }
log_success() { echo -e "\033[0;32m[SUCCESS] $1\033[0m"; }
log_error() { echo -e "\033[0;31m[ERROR] $1\033[0m"; }

# 1. Ensure Directories
log_info "Ensuring directories exist in $EDGE_HOME..."
sudo mkdir -p "$LOGS_DIR"
sudo chown -R $USER:$USER "$EDGE_HOME"

# 2. Create .env if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    log_info "Creating default .env file..."
    cat <<EOF > "$ENV_FILE"
# Cloud Configuration
CLOUD_URL=
API_KEY=
SOCKETIO_PATH=socket.io
SOCKETIO_NAMESPACE=

# Edge Configuration
EDGE_NAME=My-Edge-Collector
EDGE_ID=edge_$((1000 + RANDOM % 9000))
LOCATION=Unknown

# Application Settings
WEB_UI_HOST=0.0.0.0
WEB_UI_PORT=5001
LOG_LEVEL=INFO

# Update Preferences
IS_MANUAL_UPDATE=0
EOF
    log_success "Created default .env at $ENV_FILE. Please update it with your credentials."
fi

# 3. Check for Docker
install_docker() {
    log_info "Docker not found. Attempting to install Docker..."
    if command -v apt-get &> /dev/null; then
        log_info "Using official Docker install script..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        log_success "Docker installed! Please log out and back in, then run this script again."
        rm get-docker.sh
        exit 0
    else
        log_error "Automatic install only supported on Debian/Ubuntu. Please install Docker manually."
        exit 1
    fi
}

log_info "Checking for Docker..."
if ! command -v docker &> /dev/null; then
    read -p "Docker not found. Install it now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_docker
    else
        log_error "Docker is required. Exiting."
        exit 1
    fi
fi

# 4. GitHub Setup (Watchtower Auth)
log_info "Configuring GitHub Authentication for updates..."
USER_GH="${GHCR_USER:-Teampresence-production}"
TOKEN_GH="${GHCR_TOKEN:-}"
if [ -z "$TOKEN_GH" ]; then
    log_error "GHCR_TOKEN environment variable is required for GHCR authentication."
    exit 1
fi
AUTH=$(echo -n "${USER_GH}:${TOKEN_GH}" | base64)

cat <<EOF > "$AUTH_FILE"
{
  "auths": {
    "ghcr.io": {
      "auth": "$AUTH"
    }
  }
}
EOF
log_success "Authentication configured in $AUTH_FILE"

# 4.5 Login to GHCR for the host
log_info "Logging into GHCR for host Docker daemon..."
echo "$TOKEN_GH" | docker login ghcr.io -u "$USER_GH" --password-stdin

# 4. Start Docker Compose
log_info "Starting Edge application via Docker Compose..."
export LOGS_DIR="$LOGS_DIR"
export ENV_FILE="$ENV_FILE"
export IS_MANUAL_UPDATE=0

if command -v docker-compose &> /dev/null; then
    docker-compose up -d
elif docker compose version &> /dev/null; then
    docker compose up -d
else
    log_error "Docker Compose not found! Please install docker-compose."
    exit 1
fi

log_success "Edge application is starting!"
log_info "Opening browser at http://localhost:3000..."
sleep 5
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:3000"
elif command -v open &> /dev/null; then
    open "http://localhost:3000"
else
    log_info "Please visit http://localhost:3000 to complete setup."
fi
