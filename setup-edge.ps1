# setup-edge.ps1 - Automated Setup for Edge Collector on Windows
 
$EdgeHome = "C:\edge"
$LogsDir = Join-Path $EdgeHome "logs"
$EnvFile = Join-Path $EdgeHome ".env"
$AuthFile = Join-Path $PSScriptRoot "watchtower-auth.json"
 
function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}
 
function Write-Success([string]$Message) {
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}
 
# 1. Set Execution Policy
Write-Info "Setting Execution Policy..."
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue
} catch {
    # Ignore errors if policy is already bypassed or restricted by GPO
}
 
# 2. Ensure Directories
Write-Info "Ensuring directories exist in $EdgeHome..."
if (-not (Test-Path $EdgeHome)) {
    New-Item -ItemType Directory -Path $EdgeHome | Out-Null
}
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}
 
# 3. Create .env if it doesn't exist
if (-not (Test-Path $EnvFile)) {
    Write-Info "Creating default .env file..."
    $DefaultEnv = @(
        "# Cloud Configuration",
        "CLOUD_URL=",
        "API_KEY=",
        "SOCKETIO_PATH=socket.io",
        "SOCKETIO_NAMESPACE=",
        "",
        "# Edge Configuration",
        "EDGE_NAME=My-Edge-Collector",
        "EDGE_ID=edge_$(Get-Random -Minimum 1000 -Maximum 9999)",
        "LOCATION=Unknown",
        "",
        "# Application Settings",
        "WEB_UI_HOST=0.0.0.0",
        "WEB_UI_PORT=5001",
        "LOG_LEVEL=INFO",
        "",
        "# Update Preferences",
        "IS_MANUAL_UPDATE=0"
    )
    $DefaultEnv | Out-File -FilePath $EnvFile -Encoding ascii
    Write-Success "Created default .env at $EnvFile. Please update it with your credentials."
}
 
# 4. GitHub Setup (Watchtower Auth)
Write-Info "Configuring GitHub Authentication for updates..."
$User = "Teampresence-production"
$Token = $env:GHCR_TOKEN
if (-not $Token) {
    $SecureToken = Read-Host "Enter GHCR token" -AsSecureString
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken))
}
$Auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${User}:${Token}"))
$Config = @{ auths = @{ "ghcr.io" = @{ auth = $Auth } } }
$Config | ConvertTo-Json | Out-File -FilePath $AuthFile -Encoding ascii
Write-Success "Authentication configured in $AuthFile"
 
# 4.5 Login to GHCR for the host
Write-Info "Logging into GHCR for host Docker daemon..."
echo $Token | docker login ghcr.io -u $User --password-stdin | Out-Null
 
# 5. Check for Docker
function Install-Docker {
    Write-Host "[WARNING] Docker not found on this system!" -ForegroundColor Yellow
    $choice = Read-Host "Would you like to attempt to install Docker Desktop automatically and restart? (y/n)"
    if ($choice -eq 'y') {
        # Ensure WSL is updated (common cause of Docker failure)
        Write-Info "Ensuring WSL is up to date..."
        wsl --update
       
        Write-Info "Attempting to install Docker Desktop via winget..."
        if (Get-Command "winget" -ErrorAction SilentlyContinue) {
            # Run winget and wait for it to finish
            Start-Process winget -ArgumentList "install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements" -Wait
           
            Write-Success "Docker Desktop installation finished."
           
            # Setup auto-resume after restart
            $batPath = Join-Path $PSScriptRoot "run-edge.bat"
            Write-Info "Setting up auto-resume for: $batPath"
           
            # Use a more robust registry command for paths with spaces
            $registryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
            $resumeCommand = "cmd.exe /c `"$batPath`""
            Set-ItemProperty -Path $registryPath -Name "EdgeSetupResume" -Value $resumeCommand
           
            Write-Host "`n[IMPORTANT] The computer will RESTART in 10 seconds." -ForegroundColor Red
            Write-Host "After you log back in, the setup will continue automatically.`n" -ForegroundColor Cyan
           
            for ($i = 10; $i -gt 0; $i--) {
                Write-Host "Restarting in $i... " -NoNewline
                Start-Sleep -Seconds 1
            }
           
            Restart-Computer -Force
            exit 0
        } else {
            Write-Error "Winget not found. Please install Docker Desktop manually."
        }
    } else {
        Write-Error "Docker is required. Please install it and try again."
    }
    exit 1
}
 
Write-Info "Checking for Docker..."
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Install-Docker
}
 
Write-Info "Checking if Docker daemon is running..."
$dockerRunning = $false
try {
    & docker version --format '{{.Server.Version}}' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch { }
 
if (-not $dockerRunning) {
    Write-Host "[WARNING] Docker daemon is not running!" -ForegroundColor Yellow
    Write-Info "Attempting to start Docker Desktop..."
    $dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Start-Process $dockerPath
        Write-Info "Waiting for Docker daemon to initialize (this may take a minute)..."
        $retryCount = 0
        while (-not $dockerRunning -and $retryCount -lt 20) {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 5
            try {
                & docker version --format '{{.Server.Version}}' 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
            } catch { }
            $retryCount++
        }
        Write-Host ""
    } else {
        Write-Error "Docker Desktop not found at $dockerPath. Please start it manually."
        exit 1
    }
}
 
if (-not $dockerRunning) {
    Write-Error "Docker daemon failed to start in time. Please start Docker Desktop manually and run this script again."
    exit 1
}
 
# 6. Start Docker Compose
Write-Info "Starting Edge application via Docker Compose..."
$env:LOGS_DIR = $LogsDir
$env:ENV_FILE = $EnvFile
$env:IS_MANUAL_UPDATE = 0
 
if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
    docker-compose up -d
} else {
    docker compose up -d
}
 
Write-Success "Edge application is starting!"
Write-Info "Opening browser at http://localhost:3000..."
Start-Sleep -Seconds 5
Start-Process "http://localhost:3000"
 
 # setup-edge.ps1 - Automated Setup for Edge Collector on Windows
 
$EdgeHome = "C:\edge"
$LogsDir = Join-Path $EdgeHome "logs"
$EnvFile = Join-Path $EdgeHome ".env"
$AuthFile = Join-Path $PSScriptRoot "watchtower-auth.json"
 
function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}
 
function Write-Success([string]$Message) {
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}
 
# 1. Set Execution Policy
Write-Info "Setting Execution Policy..."
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue
} catch {
    # Ignore errors if policy is already bypassed or restricted by GPO
}
 
# 2. Ensure Directories
Write-Info "Ensuring directories exist in $EdgeHome..."
if (-not (Test-Path $EdgeHome)) {
    New-Item -ItemType Directory -Path $EdgeHome | Out-Null
}
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}
 
# 3. Create .env if it doesn't exist
if (-not (Test-Path $EnvFile)) {
    Write-Info "Creating default .env file..."
    $DefaultEnv = @(
        "# Cloud Configuration",
        "CLOUD_URL=",
        "API_KEY=",
        "SOCKETIO_PATH=socket.io",
        "SOCKETIO_NAMESPACE=",
        "",
        "# Edge Configuration",
        "EDGE_NAME=My-Edge-Collector",
        "EDGE_ID=edge_$(Get-Random -Minimum 1000 -Maximum 9999)",
        "LOCATION=Unknown",
        "",
        "# Application Settings",
        "WEB_UI_HOST=0.0.0.0",
        "WEB_UI_PORT=5001",
        "LOG_LEVEL=INFO",
        "",
        "# Update Preferences",
        "IS_MANUAL_UPDATE=0"
    )
    $DefaultEnv | Out-File -FilePath $EnvFile -Encoding ascii
    Write-Success "Created default .env at $EnvFile. Please update it with your credentials."
}
 
# 4. GitHub Setup (Watchtower Auth)
Write-Info "Configuring GitHub Authentication for updates..."
$User = "Teampresence-production"
$Token = $env:GHCR_TOKEN
if (-not $Token) {
    $SecureToken = Read-Host "Enter GHCR token" -AsSecureString
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken))
}
$Auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${User}:${Token}"))
$Config = @{ auths = @{ "ghcr.io" = @{ auth = $Auth } } }
$Config | ConvertTo-Json | Out-File -FilePath $AuthFile -Encoding ascii
Write-Success "Authentication configured in $AuthFile"
 
# 4.5 Login to GHCR for the host
Write-Info "Logging into GHCR for host Docker daemon..."
echo $Token | docker login ghcr.io -u $User --password-stdin | Out-Null
 
# 5. Check for Docker
function Install-Docker {
    Write-Host "[WARNING] Docker not found on this system!" -ForegroundColor Yellow
    $choice = Read-Host "Would you like to attempt to install Docker Desktop automatically and restart? (y/n)"
    if ($choice -eq 'y') {
        # Ensure WSL is updated (common cause of Docker failure)
        Write-Info "Ensuring WSL is up to date..."
        wsl --update
       
        Write-Info "Attempting to install Docker Desktop via winget..."
        if (Get-Command "winget" -ErrorAction SilentlyContinue) {
            # Run winget and wait for it to finish
            Start-Process winget -ArgumentList "install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements" -Wait
           
            Write-Success "Docker Desktop installation finished."
           
            # Setup auto-resume after restart
            $batPath = Join-Path $PSScriptRoot "run-edge.bat"
            Write-Info "Setting up auto-resume for: $batPath"
           
            # Use a more robust registry command for paths with spaces
            $registryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
            $resumeCommand = "cmd.exe /c `"$batPath`""
            Set-ItemProperty -Path $registryPath -Name "EdgeSetupResume" -Value $resumeCommand
           
            Write-Host "`n[IMPORTANT] The computer will RESTART in 10 seconds." -ForegroundColor Red
            Write-Host "After you log back in, the setup will continue automatically.`n" -ForegroundColor Cyan
           
            for ($i = 10; $i -gt 0; $i--) {
                Write-Host "Restarting in $i... " -NoNewline
                Start-Sleep -Seconds 1
            }
           
            Restart-Computer -Force
            exit 0
        } else {
            Write-Error "Winget not found. Please install Docker Desktop manually."
        }
    } else {
        Write-Error "Docker is required. Please install it and try again."
    }
    exit 1
}
 
Write-Info "Checking for Docker..."
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Install-Docker
}
 
Write-Info "Checking if Docker daemon is running..."
$dockerRunning = $false
try {
    & docker version --format '{{.Server.Version}}' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch { }
 
if (-not $dockerRunning) {
    Write-Host "[WARNING] Docker daemon is not running!" -ForegroundColor Yellow
    Write-Info "Attempting to start Docker Desktop..."
    $dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Start-Process $dockerPath
        Write-Info "Waiting for Docker daemon to initialize (this may take a minute)..."
        $retryCount = 0
        while (-not $dockerRunning -and $retryCount -lt 20) {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 5
            try {
                & docker version --format '{{.Server.Version}}' 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
            } catch { }
            $retryCount++
        }
        Write-Host ""
    } else {
        Write-Error "Docker Desktop not found at $dockerPath. Please start it manually."
        exit 1
    }
}
 
if (-not $dockerRunning) {
    Write-Error "Docker daemon failed to start in time. Please start Docker Desktop manually and run this script again."
    exit 1
}
 
# 6. Start Docker Compose
Write-Info "Starting Edge application via Docker Compose..."
$env:LOGS_DIR = $LogsDir
$env:ENV_FILE = $EnvFile
$env:IS_MANUAL_UPDATE = 0
 
if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
    docker-compose up -d
} else {
    docker compose up -d
}
 
Write-Success "Edge application is starting!"
Write-Info "Opening browser at http://localhost:3000..."
Start-Sleep -Seconds 5
Start-Process "http://localhost:3000"
 
 
