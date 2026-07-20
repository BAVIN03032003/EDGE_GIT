$Username = Read-Host "Enter GitHub Username"
$SecureToken = Read-Host "Enter GitHub Personal Access Token (PAT)" -AsSecureString
$Ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
$Token = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($Ptr)

try {
    Write-Host "[INFO] Attempting to log into ghcr.io..." -ForegroundColor Cyan
    $Token | docker login ghcr.io -u $Username --password-stdin
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Authentication stored in Docker credential store." -ForegroundColor Green
    }
} finally {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Ptr)
    $Token = $null
    $SecureToken = $null
    [System.GC]::Collect()
}
