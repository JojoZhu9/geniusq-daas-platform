param(
    [switch]$NoBrowser,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'

function Require-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "未找到 $Name。$InstallHint"
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

Require-Command 'python' '请安装 Python 3.9+ 并勾选 Add Python to PATH。'
Require-Command 'node' '请安装 Node.js 18+。'
Require-Command 'npm.cmd' '请确认 Node.js 安装目录已加入 PATH。'

if (-not $SkipInstall) {
    Write-Host '[1/4] 检查并安装后端依赖…' -ForegroundColor Cyan
    & python -m pip install -e "$Backend[test]"
    if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败。' }

    Write-Host '[2/4] 检查并安装前端依赖…' -ForegroundColor Cyan
    Push-Location $Frontend
    try {
        if (Test-Path (Join-Path $Frontend 'node_modules')) {
            & npm.cmd install --no-audit --no-fund
        } else {
            & npm.cmd ci --no-audit --no-fund
        }
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败。' }
    } finally {
        Pop-Location
    }
}

Write-Host '[3/4] 启动 FastAPI 与 Vite…' -ForegroundColor Cyan
$BackendProcess = Start-Process -FilePath 'python' -ArgumentList @(
    '-m', 'uvicorn', 'app.main:app', '--app-dir', $Backend,
    '--host', '127.0.0.1', '--port', '8000'
) -WorkingDirectory $Root -WindowStyle Hidden -PassThru

$FrontendProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList @(
    'run', 'dev', '--', '--port', '5173'
) -WorkingDirectory $Frontend -WindowStyle Hidden -PassThru

Write-Host '[4/4] 等待服务健康检查…' -ForegroundColor Cyan
$BackendReady = Wait-Http 'http://127.0.0.1:8000/api/health'
$FrontendReady = Wait-Http 'http://127.0.0.1:5173'

if (-not $BackendReady -or -not $FrontendReady) {
    if (-not $BackendProcess.HasExited) { Stop-Process -Id $BackendProcess.Id -Force }
    if (-not $FrontendProcess.HasExited) { Stop-Process -Id $FrontendProcess.Id -Force }
    throw '服务未在 30 秒内就绪。请检查 8000/5173 端口占用和运行时版本。'
}

Write-Host "Demo 已启动： http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "后端健康检查： http://127.0.0.1:8000/api/health" -ForegroundColor Green
Write-Host "进程 ID：backend=$($BackendProcess.Id), frontend=$($FrontendProcess.Id)"

if (-not $NoBrowser) {
    Start-Process 'http://127.0.0.1:5173'
}
