param(
    [switch]$NoBrowser,
    [switch]$SkipInstall,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'

function Require-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $InstallHint"
    }
}

function Wait-Http([string]$Url, [int]$Attempts = 30) {
    for ($Index = 0; $Index -lt $Attempts; $Index++) {
        try {
            $Response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

Require-Command 'python' 'Install Python 3.9+ and add it to PATH.'
Require-Command 'node' 'Install Node.js 18+.'
Require-Command 'npm.cmd' 'Add the Node.js installation directory to PATH.'

if (-not $SkipInstall) {
    Write-Host '[1/4] Checking backend dependencies...' -ForegroundColor Cyan
    & python -m pip install -e "$Backend[test]"
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }

    Write-Host '[2/4] Checking frontend dependencies...' -ForegroundColor Cyan
    Push-Location $Frontend
    try {
        if (Test-Path (Join-Path $Frontend 'node_modules')) {
            & npm.cmd install --no-audit --no-fund
        } else {
            & npm.cmd ci --no-audit --no-fund
        }
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    } finally {
        Pop-Location
    }
}

Write-Host '[3/4] Starting FastAPI and Vite...' -ForegroundColor Cyan
$BackendProcess = Start-Process -FilePath 'python' -ArgumentList @(
    '-m', 'uvicorn', 'app.main:app', '--app-dir', $Backend,
    '--host', '127.0.0.1', '--port', "$BackendPort"
) -WorkingDirectory $Root -WindowStyle Hidden -PassThru

$PreviousProxy = $env:VITE_API_PROXY
$env:VITE_API_PROXY = "http://127.0.0.1:$BackendPort"
$FrontendProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList @(
    'run', 'dev', '--', '--port', "$FrontendPort"
) -WorkingDirectory $Frontend -WindowStyle Hidden -PassThru
$env:VITE_API_PROXY = $PreviousProxy

Write-Host '[4/4] Waiting for service health checks...' -ForegroundColor Cyan
$BackendReady = Wait-Http "http://127.0.0.1:$BackendPort/api/health"
$FrontendReady = Wait-Http "http://127.0.0.1:$FrontendPort"

if (-not $BackendReady -or -not $FrontendReady) {
    if (-not $BackendProcess.HasExited) { Stop-Process -Id $BackendProcess.Id -Force }
    if (-not $FrontendProcess.HasExited) { Stop-Process -Id $FrontendProcess.Id -Force }
    throw "Services did not become ready in 30 seconds. Check ports $BackendPort/$FrontendPort and runtime versions."
}

Write-Host "Demo ready: http://127.0.0.1:$FrontendPort" -ForegroundColor Green
Write-Host "Backend health: http://127.0.0.1:$BackendPort/api/health" -ForegroundColor Green
Write-Host "Process IDs: backend=$($BackendProcess.Id), frontend=$($FrontendProcess.Id)"

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort"
}
