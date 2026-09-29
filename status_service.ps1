# ChainSentinel -- Status Check for Production Daemon
$ErrorActionPreference = "Continue"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

$PidFile = Join-Path $RootDir "data\chainsentinel.pid"
$LogFile = Join-Path $RootDir "data\logs\chainsentinel_stderr.log"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      ChainSentinel - Production Service Status           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$IsRunning = $false
$DaemonPid = $null

if (Test-Path $PidFile) {
    $DaemonPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($DaemonPid) {
        $Proc = Get-Process -Id ([int]$DaemonPid) -ErrorAction SilentlyContinue
        if ($Proc) {
            $IsRunning = $true
            $MemMB = [math]::Round($Proc.WorkingSet64 / 1MB, 1)
            Write-Host "Daemon Status:       ONLINE" -ForegroundColor Green
            Write-Host "Process ID:          $DaemonPid" -ForegroundColor White
            Write-Host "Memory (WorkingSet): $MemMB MB" -ForegroundColor White
        }
    }
}

if (-not $IsRunning) {
    $PortCheck = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($PortCheck) {
        $IsRunning = $true
        $PortPid = $PortCheck[0].OwningProcess
        Write-Host "Daemon Status:       ONLINE (listening on port 8000, PID: $PortPid)" -ForegroundColor Green
    } else {
        Write-Host "Daemon Status:       STOPPED / OFFLINE" -ForegroundColor Red
    }
}

if ($IsRunning) {
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "Health Check:        PASS (status: $($Health.status), version: $($Health.version))" -ForegroundColor Green
    } catch {
        Write-Host "Health Check:        FAILED" -ForegroundColor Yellow
    }
}

Write-Host "Log File:            $LogFile" -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Cyan
