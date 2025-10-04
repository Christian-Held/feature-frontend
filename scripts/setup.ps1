param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

Write-Host "[setup] Checking Python version..."
$pythonVersion = (python --version 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11+ is required."
}
if (-not ($pythonVersion -match '3\.(1[1-9]|[2-9]\d)')) {
    throw "Python 3.11 or newer is required. Found: $pythonVersion"
}

Write-Host "[setup] Ensuring uv is installed..."
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    python -m pip install --upgrade uv
}

Write-Host "[setup] Syncing dependencies via uv..."
uv sync

Write-Host "[setup] Ensuring data directory exists..."
New-Item -ItemType Directory -Path "data" -Force | Out-Null

Write-Host "[setup] Starting Redis via docker compose..."
docker compose up -d redis

Write-Host "[setup] Complete."
