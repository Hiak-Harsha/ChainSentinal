# ChainSentinel — Forensic Intelligence Platform (NTRO SIH26146)
# Windows Run Script
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

$VenvDir = Join-Path $RootDir "backend\.venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment not found. Please run .\install.ps1 first."
    exit 1
}

$HostAddr = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$PortNum = if ($env:PORT) { $env:PORT } else { "8000" }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      ChainSentinel — Forensic Intelligence Platform      " -ForegroundColor Cyan
Write-Host "  AI-Powered Monitoring of Bitcoin Transaction Traffic    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Starting ChainSentinel unified service..." -ForegroundColor Green
Write-Host "[*] API Endpoint:       http://${HostAddr}:${PortNum}/api/health" -ForegroundColor Yellow
Write-Host "[*] Web Dashboard:      http://${HostAddr}:${PortNum}/" -ForegroundColor Yellow
Write-Host "[*] Interactive Docs:   http://${HostAddr}:${PortNum}/docs" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"
Write-Host "[+] Press Ctrl+C to stop the service.`n"

Set-Location (Join-Path $RootDir "backend")
& $PythonExe -m uvicorn app.main:app --host $HostAddr --port [int]$PortNum
