# ChainSentinel — Forensic Intelligence Platform (NTRO SIH26146)
# Windows Offline / Local Installer
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      ChainSentinel — Forensic Intelligence Platform      " -ForegroundColor Cyan
Write-Host "  AI-Powered Monitoring of Bitcoin Transaction Traffic    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$VenvDir = Join-Path $RootDir "backend\.venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$PipExe = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[+] Creating virtual environment in $VenvDir..." -ForegroundColor Yellow
    python -m venv $VenvDir
} else {
    Write-Host "[*] Using existing virtual environment in $VenvDir" -ForegroundColor Green
}

Write-Host "[+] Installing backend Python dependencies..." -ForegroundColor Yellow
& $PipExe install -e (Join-Path $RootDir "backend")

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "[+] Building frontend application..." -ForegroundColor Yellow
    Set-Location (Join-Path $RootDir "frontend")
    if (-not (Test-Path "node_modules")) {
        npm install --prefer-offline --no-audit
    }
    npm run build
    Set-Location $RootDir
    Write-Host "[+] Frontend build output written to frontend\out" -ForegroundColor Green
} else {
    Write-Host "[*] npm not found in PATH. Checking for pre-compiled frontend\out..." -ForegroundColor Yellow
    if (-not (Test-Path (Join-Path $RootDir "frontend\out"))) {
        Write-Warning "frontend\out does not exist and npm is not installed. Please build frontend manually."
    }
}

New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "docs") | Out-Null

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[+] ChainSentinel installation completed successfully!" -ForegroundColor Green
Write-Host "    To run the platform:" -ForegroundColor White
Write-Host "    .\run.ps1" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
