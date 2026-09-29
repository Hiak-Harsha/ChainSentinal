# ChainSentinel -- Stop Production Daemon
$ErrorActionPreference = "SilentlyContinue"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

$PidFile = Join-Path $RootDir "data\chainsentinel.pid"

if (Test-Path $PidFile) {
    $DaemonPid = Get-Content $PidFile
    if ($DaemonPid) {
        $Proc = Get-Process -Id ([int]$DaemonPid) -ErrorAction SilentlyContinue
        if ($Proc) {
            Write-Host "Stopping ChainSentinel daemon (PID: $DaemonPid)..." -ForegroundColor Yellow
            Stop-Process -Id ([int]$DaemonPid) -Force
            Start-Sleep -Seconds 1
            Write-Host "ChainSentinel daemon stopped." -ForegroundColor Green
        } else {
            Write-Host "Process PID $DaemonPid was not running." -ForegroundColor Yellow
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# Ensure port 8000 is clean
$PortOccupied = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($PortOccupied) {
    foreach ($conn in $PortOccupied) {
        if ($conn.OwningProcess -gt 4) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}
Write-Host "Service stopped successfully." -ForegroundColor Green
