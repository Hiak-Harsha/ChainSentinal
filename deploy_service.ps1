# ChainSentinel -- Forensic Intelligence Platform (NTRO SIH26146)
# Windows Production Service Deployer
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

$VenvDir = Join-Path $RootDir "backend\.venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$LogDir = Join-Path $RootDir "data\logs"
$LogFileOut = Join-Path $LogDir "chainsentinel_stdout.log"
$LogFileErr = Join-Path $LogDir "chainsentinel_stderr.log"
$PidFile = Join-Path $RootDir "data\chainsentinel.pid"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment not found at $PythonExe. Please run .\install.ps1 first."
    exit 1
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "data\audit") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "data\uploads") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "data\models") | Out-Null

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      ChainSentinel - Production Workstation Deployment   " -ForegroundColor Cyan
Write-Host "  AI-Powered Monitoring of Bitcoin Transaction Traffic    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Stop existing service if running
if (Test-Path $PidFile) {
    $OldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($OldPid) {
        $OldProc = Get-Process -Id ([int]$OldPid) -ErrorAction SilentlyContinue
        if ($OldProc) {
            Write-Host "Stopping existing ChainSentinel process (PID: $OldPid)..." -ForegroundColor Yellow
            Stop-Process -Id ([int]$OldPid) -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# 2. Check and stop any rogue process on port 8000
$PortOccupied = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($PortOccupied) {
    foreach ($conn in $PortOccupied) {
        $RoguePid = $conn.OwningProcess
        if ($RoguePid -gt 4) {
            Write-Host "Freeing port 8000 occupied by PID $RoguePid..." -ForegroundColor Yellow
            Stop-Process -Id $RoguePid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
}

# 3. Ensure frontend production bundle exists
$FrontendOut = Join-Path $RootDir "frontend\out"
$IndexHtml = Join-Path $FrontendOut "index.html"
if (-not (Test-Path $IndexHtml)) {
    Write-Host "Compiling frontend production bundle..." -ForegroundColor Yellow
    Set-Location (Join-Path $RootDir "frontend")
    npm run build
    Set-Location $RootDir
}

# 4. Launch unified background production daemon
Write-Host "Launching production daemon (FastAPI + Embedded Production UI)..." -ForegroundColor Green

$HostAddr = if ($env:CS_HOST) { $env:CS_HOST } else { "0.0.0.0" }
$PortNum = if ($env:CS_PORT) { $env:CS_PORT } else { "8000" }

$BackendDir = Join-Path $RootDir "backend"
$ProcessArgs = "-m uvicorn app.main:app --host " + $HostAddr + " --port " + $PortNum

$startParams = @{
    FilePath = $PythonExe
    ArgumentList = $ProcessArgs
    WorkingDirectory = $BackendDir
    RedirectStandardOutput = $LogFileOut
    RedirectStandardError = $LogFileErr
    WindowStyle = "Hidden"
    PassThru = $true
}

$Proc = Start-Process @startParams
$ProcId = $Proc.Id
$ProcId | Out-File -FilePath $PidFile -Encoding ascii

Write-Host "Background process started with PID: $ProcId" -ForegroundColor Green
Write-Host "Service output redirected to: $LogFileErr" -ForegroundColor DarkGray

# 5. Health verification probe
Write-Host "Verifying service health..." -ForegroundColor Yellow
$HealthUrl = "http://127.0.0.1:" + $PortNum + "/api/health"
$RootUrl = "http://127.0.0.1:" + $PortNum + "/"
$Healthy = $false

for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $Response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($Response.StatusCode -eq 200) {
            $Healthy = $true
            break
        }
    } catch {
        # Retry until timeout
    }
}

if ($Healthy) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  DEPLOYMENT SUCCESSFUL -- SERVICE IS HEALTHY AND ONLINE  " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  Web Dashboard:      $RootUrl" -ForegroundColor Cyan
    Write-Host "  REST API Health:    $HealthUrl" -ForegroundColor Cyan
    Write-Host "  OpenAPI Docs:       http://127.0.0.1:8000/api/docs" -ForegroundColor Cyan
    Write-Host "  WebSocket Stream:   ws://127.0.0.1:8000/api/ws/telemetry" -ForegroundColor Cyan
    Write-Host "  Daemon PID:         $ProcId" -ForegroundColor Yellow
    Write-Host "  Service Log:        $LogFileErr" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------"
    Write-Host "  To check status:    .\status_service.ps1" -ForegroundColor White
    Write-Host "  To stop service:    .\stop_service.ps1" -ForegroundColor White
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Error "Deployment failed: Health probe timed out. Check logs at: $LogFileErr"
    exit 1
}
