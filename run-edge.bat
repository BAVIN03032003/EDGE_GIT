@echo off
SETLOCAL
cd /d %~dp0

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] Running with Administrator privileges.
) else (
    echo [WARNING] Not running as Administrator. Some features may fail.
    echo [INFO] Attempting to elevate...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Run the setup script
powershell -ExecutionPolicy Bypass -File "setup-edge.ps1"

pause
