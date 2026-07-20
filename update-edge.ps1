# update-edge.ps1 - Manual Update for Edge Collector on Windows

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Success([string]$Message) {
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

Write-Info "Checking for Edge application updates..."

# Pull latest images
if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
    docker-compose pull
    docker-compose up -d --remove-orphans
} else {
    docker compose pull
    docker compose up -d --remove-orphans
}

Write-Success "Update process completed. Checking container status..."
docker ps --filter "name=edge-app" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
