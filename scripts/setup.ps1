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

function Get-RepoRoot {
    param(
        [string]$ScriptPath
    )
    $scriptsDir = Split-Path -Path $ScriptPath -Parent
    return Resolve-Path -Path (Join-Path $scriptsDir '..')
}

function Ensure-UvInstalled {
    param(
        [string]$PythonPath
    )

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        return
    }

    if (-not $PythonPath) {
        throw 'Kein Python Interpreter gefunden, um uv zu installieren.'
    }

    Write-SetupLog "Installiere uv über $PythonPath ..."
    & $PythonPath -m pip install --upgrade uv | Out-Null
}

function Test-VersionInRange {
    param(
        [Version]$Version,
        [Version]$Min,
        [Version]$MaxExclusive
    )

    if ($null -eq $Version) {
        return $false
    }

    return ($Version -ge $Min) -and ($Version -lt $MaxExclusive)
}

function Get-CompatiblePython {
    param(
        [string]$ActivePythonPath
    )

    $preferredMin = [Version]'3.12.0'
    $preferredMax = [Version]'3.14.0'

    $candidate = $null
    $versionOutput = $null
    $parsedVersion = $null

    if ($ActivePythonPath) {
        $versionOutput = & $ActivePythonPath --version 2>&1
        $match = [regex]::Match($versionOutput, 'Python\s+(?<ver>\d+\.\d+\.\d+)')
        if ($match.Success) {
            $parsedVersion = [Version]$match.Groups['ver'].Value
            if (Test-VersionInRange -Version $parsedVersion -Min $preferredMin -MaxExclusive $preferredMax) {
                return [pscustomobject]@{
                    Path    = $ActivePythonPath
                    Version = $parsedVersion
                    Output  = $versionOutput
                    Mode    = 'active'
                }
            }
        }
    }

    $findOutput = @()
    try {
        $findOutput = uv python find 'cpython>=3.12,<3.14'
    } catch {
        $findOutput = @()
    }

    if ($findOutput.Count -gt 0) {
        $candidatePath = $findOutput[0].Trim()
        if ($candidatePath) {
            $candidateVersionOutput = & $candidatePath --version 2>&1
            $candidateMatch = [regex]::Match($candidateVersionOutput, 'Python\s+(?<ver>\d+\.\d+\.\d+)')
            if ($candidateMatch.Success) {
                $candidateVersion = [Version]$candidateMatch.Groups['ver'].Value
                if (Test-VersionInRange -Version $candidateVersion -Min $preferredMin -MaxExclusive $preferredMax) {
                    return [pscustomobject]@{
                        Path    = $candidatePath
                        Version = $candidateVersion
                        Output  = $candidateVersionOutput
                        Mode    = 'uv-find'
                    }
                }
            }
        }
    }

    if ($ActivePythonPath -and $parsedVersion) {
        return [pscustomobject]@{
            Path    = $ActivePythonPath
            Version = $parsedVersion
            Output  = $versionOutput
            Mode    = 'best-effort'
        }
    }

    return $null
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

$repoRoot = Get-RepoRoot -ScriptPath $PSCommandPath
Set-Location -Path $repoRoot
Write-SetupLog "Arbeitsverzeichnis: $repoRoot"

Write-SetupLog 'Prüfe Python Installation ...'
$preferredRangeMessage = 'Empfohlene Python-Versionen: 3.12 oder 3.13 (3.11/3.14 Best-Effort).'
Write-SetupLog $preferredRangeMessage
if ($Force) {
    Write-SetupLog 'Hinweis: Der Parameter -Force wird nicht mehr benötigt und wird ignoriert.'
}
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw 'Python wurde nicht gefunden. Bitte installieren Sie mindestens Python 3.12.'
}

Ensure-UvInstalled -PythonPath $pythonCommand.Path

$pythonInfo = Get-CompatiblePython -ActivePythonPath $pythonCommand.Path
if (-not $pythonInfo) {
    throw 'Kein kompatibler Python Interpreter (>=3.12,<3.14) gefunden. Bitte installieren Sie Python 3.12 oder 3.13.'
}

if ($pythonInfo.Mode -eq 'best-effort') {
    Write-SetupLog "Hinweis: Aktiver Interpreter $($pythonInfo.Output) liegt außerhalb der empfohlenen Spanne >=3.12,<3.14. Setup läuft im Best-Effort-Modus weiter."
} else {
    Write-SetupLog "Nutze Python Interpreter ($($pythonInfo.Mode)): $($pythonInfo.Path) [$($pythonInfo.Output)]"
}

$env:UV_PROJECT_ENVIRONMENT = (Join-Path $repoRoot '.venv')
Write-SetupLog "uv Projektumgebung: $env:UV_PROJECT_ENVIRONMENT"

Write-SetupLog 'Synchronisiere Abhängigkeiten mit uv ...'
if ($pythonInfo.Mode -eq 'best-effort') {
    Write-SetupLog 'Best-Effort: uv sync nutzt den aktiven Interpreter und kann bei inkompatibler Version fehlschlagen. Empfohlen ist Python 3.12 oder 3.13.'
}
if ($pythonInfo.Mode -eq 'uv-find' -or $pythonInfo.Mode -eq 'active' -or $pythonInfo.Mode -eq 'best-effort') {
    uv sync --extra tests --python $pythonInfo.Path
} else {
    uv sync --extra tests
}

Write-SetupLog 'Stelle Datenverzeichnis bereit ...'
New-Item -ItemType Directory -Path 'data' -Force | Out-Null

Write-SetupLog 'Prüfe Docker Desktop ...'
try {
    docker info | Out-Null
}
catch {
    throw 'Docker Desktop scheint nicht zu laufen. Bitte starten und erneut versuchen.'
}

Write-SetupLog 'Starte Redis via Docker Compose ...'
docker compose up -d orchestrator-redis

Write-SetupLog 'Warte auf Redis (Port 6379) ...'
$deadline = (Get-Date).AddSeconds(60)
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
