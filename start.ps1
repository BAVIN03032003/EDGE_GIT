Param(
    [ValidateSet("start", "stop", "restart", "pull", "logs", "status", "rollback", "update")]
    [string]$Action = "start",

    [string]$Version = $env:VERSION,
    [string]$Registry = $env:REGISTRY,
    [string]$Org = $env:ORG,
    [string]$ImageName = $env:IMAGE_NAME,
    [string]$ContainerName = $env:CONTAINER_NAME,
    [string]$EdgeHome = $env:EDGE_HOME,
    [string]$EnvFile = $env:ENV_FILE,
    [string]$BackendPort = $env:BACKEND_PORT,
    [string]$GhcrUsername = $env:GHCR_USERNAME,
    [string]$GhcrToken = $env:GHCR_TOKEN,
    [string]$RollbackVersion
)

$ErrorActionPreference = "Stop"

if (-not $Version) { $Version = "latest" }
if (-not $Registry) { $Registry = "ghcr.io" }
if (-not $Org) { $Org = "teampresence-production" }
if (-not $ImageName) { $ImageName = "gitaction-edge" }
if (-not $ContainerName) { $ContainerName = "edge-app" }
if (-not $EdgeHome) { $EdgeHome = "C:\edge" }
if (-not $EnvFile) {
    $preferredEnv = Join-Path $EdgeHome "env"
    $fallbackEnv = Join-Path $EdgeHome ".env"
    if (Test-Path $preferredEnv) {
        $EnvFile = $preferredEnv
    } else {
        $EnvFile = $fallbackEnv
    }
}
if (-not $BackendPort) { $BackendPort = "5001" }

$Registry = $Registry.ToLowerInvariant()
$Org = $Org.ToLowerInvariant()
$ImageName = $ImageName.ToLowerInvariant()

$ImageRef = "${Registry}/${Org}/${ImageName}:$Version"
$LogsDir = Join-Path $EdgeHome "logs"

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function Write-ErrorLine([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Ensure-Dirs {
    if (-not (Test-Path $EdgeHome)) {
        New-Item -ItemType Directory -Path $EdgeHome | Out-Null
    }

    if (-not (Test-Path $LogsDir)) {
        New-Item -ItemType Directory -Path $LogsDir | Out-Null
    }
}

function Ensure-GhcrLogin {
    if ($env:GHCR_USERNAME -and $env:GHCR_TOKEN) {
        Write-Info "Logging into GHCR as $($env:GHCR_USERNAME)..."
        echo $env:GHCR_TOKEN | docker login ghcr.io -u $env:GHCR_USERNAME --password-stdin | Out-Null
    }
}

function Pull-Image {
    Write-Info "Pulling image: $ImageRef"
    Ensure-GhcrLogin
    docker pull $ImageRef
}

function Stop-Container {
    Write-Info "Stopping existing container..."
    $exists = docker ps -a --format "{{.Names}}" | Select-String -SimpleMatch $ContainerName
    if (-not $exists) {
        Write-Info "Container does not exist yet"
        return
    }

    docker stop $ContainerName 2>$null | Out-Null
    docker rm $ContainerName 2>$null | Out-Null
}

function Start-Container {
    Ensure-Dirs

    if (-not (Test-Path $EnvFile)) {
        throw "Env file not found: $EnvFile"
    }

    Write-Info "Starting container with image: $ImageRef"

    $logsMount = ($LogsDir -replace '\\', '/')
    $envFilePath = ($EnvFile -replace '\\', '/')

    docker run -d `
        --name $ContainerName `
        --restart unless-stopped `
        --env-file $envFilePath `
        -v "${envFilePath}:/app/.env" `
        -p "${BackendPort}:5001" `
        -v "${logsMount}:/app/logs" `
        --label "edge.version=$Version" `
        --label "edge.updated=$([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))" `
        $ImageRef
}

function Verify-Container {
    Write-Info "Verifying container is running..."
    Start-Sleep -Seconds 5

    $running = docker ps --format "{{.Names}}" | Select-String -SimpleMatch $ContainerName
    if ($running) {
        Write-Host "[SUCCESS] Container is running"
        docker logs $ContainerName | Select-Object -Last 20
        return
    }

    Write-ErrorLine "Container failed to start"
    docker logs $ContainerName | Select-Object -Last 50
    exit 1
}

function Rollback-Container {
    Write-Info "Rolling back to previous version..."
    Ensure-Dirs
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    docker logs $ContainerName 2>$null | Out-File -FilePath (Join-Path $LogsDir "rollback-$stamp.log") -Encoding utf8
    Stop-Container
}

switch ($Action) {
    "start" {
        Pull-Image
        Stop-Container
        Start-Container
        Verify-Container
    }
    "stop" {
        Stop-Container
        Write-Host "[INFO] Container stopped"
    }
    "restart" {
        Stop-Container
        Pull-Image
        Start-Container
        Verify-Container
    }
    "pull" {
        Pull-Image
    }
    "logs" {
        docker logs -f $ContainerName
    }
    "status" {
        docker ps -a --format "{{.Names}}`t{{.Status}}" | Select-String -SimpleMatch $ContainerName
    }
    "rollback" {
        if (-not $RollbackVersion) {
            throw "Please specify -RollbackVersion <version>"
        }

        $Version = $RollbackVersion
        $ImageRef = "${Registry}/${Org}/${ImageName}:$Version"
        Pull-Image
        Rollback-Container
        Start-Container
        Verify-Container
    }
    "update" {
        Pull-Image
        Stop-Container
        Start-Container
        Verify-Container
    }
}
