[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-SetupLog {
    param(
        [string]$Message
    )
    Write-Host "[setup] $Message"
}

function Ensure-UvInstalled {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-SetupLog 'Installiere uv via pip ...'
        python -m pip install --upgrade uv | Out-Null
    }
}

function Test-TcpPort {
    param(
        [string]$Host,
        [int]$Port
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect($Host, $Port, $null, $null)
        $wait = $async.AsyncWaitHandle.WaitOne([TimeSpan]::FromMilliseconds(500))
        if (-not $wait) {
            $client.Close()
            return $false
        }
        $client.EndConnect($async)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

Write-SetupLog 'Prüfe Python Installation ...'
$pythonVersion = (python --version 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw 'Python 3.12 wird benötigt.'
}
Write-SetupLog "Gefundene Python Version: $pythonVersion"

Ensure-UvInstalled

Write-SetupLog 'Synchronisiere Abhängigkeiten mit uv ...'
uv sync

Write-SetupLog 'Prüfe uv Python Pin ...'
$pythonShow = ''
try {
    $pythonShow = (uv python show 2>&1)
}
catch {
    $pythonShow = ''
}
if ($Force -or ($pythonShow -notmatch '3\.12')) {
    Write-SetupLog 'Pinne uv python auf Version 3.12 ...'
    uv python pin 3.12
} else {
    Write-SetupLog 'uv python ist bereits auf 3.12 gepinnt.'
}

Write-SetupLog 'Stelle Datenverzeichnis bereit ...'
New-Item -ItemType Directory -Path 'data' -Force | Out-Null

Write-SetupLog 'Starte Redis via Docker Compose ...'
docker compose up -d orchestrator-redis

Write-SetupLog 'Warte auf Redis (Port 6379) ...'
$deadline = (Get-Date).AddSeconds(30)
$redisReady = $false
while ((Get-Date) -lt $deadline) {
    if (Test-TcpPort -Host '127.0.0.1' -Port 6379) {
        $redisReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $redisReady) {
    throw 'Redis ist nicht erreichbar (Port 6379).' 
}

Write-SetupLog 'Redis erreichbar. Setup abgeschlossen.'
