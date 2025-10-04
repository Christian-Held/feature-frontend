[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-RunLog {
    param(
        [string]$Scope,
        [string]$Message
    )
    Write-Host ("[$Scope] $Message")
}

function Get-RepoRoot {
    param(
        [string]$ScriptPath
    )

    if (-not $ScriptPath) {
        throw 'ScriptPath darf nicht leer sein.'
    }

    $scriptsDir = Split-Path -Path $ScriptPath -Parent
    $rootCandidate = Resolve-Path -Path (Join-Path $scriptsDir '..')
    return $rootCandidate
}

function Import-DotEnv {
    param(
        [string]$Path = '.env'
    )

    if (-not (Test-Path -Path $Path)) {
        Write-RunLog 'run' "Keine .env gefunden – es werden nur vorhandene Environment Variablen genutzt."
        return
    }

    Write-RunLog 'run' "Lade Umgebungsvariablen aus $Path ..."
    $regex = '^(?:export\s+)?(?<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?<value>.*)$'
    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {
            return
        }

        $match = [regex]::Match($line, $regex)
        if (-not $match.Success) {
            return
        }

        $name = $match.Groups['key'].Value
        $value = $match.Groups['value'].Value.Trim()

        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2).Replace('\\"', '"')
        } elseif ($value.StartsWith("'") -and $value.EndsWith("'")) {
            $value = $value.Substring(1, $value.Length - 2)
        } else {
            $hashIndex = $value.IndexOf('#')
            if ($hashIndex -ge 0) {
                $value = $value.Substring(0, $hashIndex)
            }
            $value = $value.Trim()
        }

        Set-Item -Path ("Env:{0}" -f $name) -Value $value
    }
}

function Start-UvJob {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    Start-Job -Name $Name -ScriptBlock {
        param($InnerName, $InnerArgs, $InnerWorkingDirectory)
        $ErrorActionPreference = 'Stop'
        Set-StrictMode -Version Latest
        Set-Location -Path $InnerWorkingDirectory

        & uv @InnerArgs 2>&1 | ForEach-Object { $_ }
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            throw "Process '$InnerName' exited with code $code"
        }
    } -ArgumentList @($Name, $Arguments, $WorkingDirectory)
}

$repoRoot = Get-RepoRoot -ScriptPath $PSCommandPath
Set-Location -Path $repoRoot
Write-RunLog 'run' "Arbeitsverzeichnis: $repoRoot"

$jobs = @()

try {
    Import-DotEnv -Path (Join-Path $repoRoot '.env')

    if (-not $env:APP_PORT -or [string]::IsNullOrWhiteSpace($env:APP_PORT)) {
        $env:APP_PORT = '3000'
    }

    $port = [int]$env:APP_PORT
    Write-RunLog 'run' "API Port: $port"

    $apiArgs = @('run', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', $port.ToString())
    $workerArgs = @('run', 'celery', '-A', 'app.workers.celery_app', 'worker', '-l', 'info')

    Write-RunLog 'run' 'Starte API und Worker (Ctrl+C zum Beenden)...'
    $jobs = @(
        [pscustomobject]@{
            Name = 'api'
            Job  = Start-UvJob -Name 'api' -Arguments $apiArgs -WorkingDirectory $repoRoot
        },
        [pscustomobject]@{
            Name = 'celery'
            Job  = Start-UvJob -Name 'celery' -Arguments $workerArgs -WorkingDirectory $repoRoot
        }
    )

    $exitCode = 0
    while ($true) {
        $anyRunning = $false
        foreach ($entry in $jobs) {
            $job = $entry.Job
            $name = $entry.Name
            $output = Receive-Job -Job $job -Keep -ErrorAction SilentlyContinue
            foreach ($line in $output) {
                if ($null -eq $line) { continue }
                if ($line -is [System.Management.Automation.ErrorRecord]) {
                    Write-RunLog $name ("ERR: " + $line.ToString())
                } else {
                    Write-RunLog $name ($line.ToString())
                }
            }

            switch ($job.State) {
                'Running' { $anyRunning = $true }
                'Failed' {
                    $anyRunning = $false
                    $exitCode = 1
                }
                'Stopped' { }
                'Completed' { }
            }
        }

        if ($exitCode -ne 0 -or -not $anyRunning) {
            break
        }

        Start-Sleep -Seconds 1
    }

    foreach ($entry in $jobs) {
        $job = $entry.Job
        $name = $entry.Name
        if ($job.State -eq 'Running') {
            continue
        }
        $output = Receive-Job -Job $job -Keep -ErrorAction SilentlyContinue
        foreach ($line in $output) {
            if ($null -eq $line) { continue }
            Write-RunLog $name ($line.ToString())
        }

        if ($job.State -eq 'Failed') {
            $reason = $job.JobStateInfo.Reason
            if ($reason) {
                Write-RunLog $name ("Fehler: " + $reason.Message)
            }
            $exitCode = 1
        }
    }
}
catch {
    Write-RunLog 'run' ("Abbruch: " + $_.Exception.Message)
    $exitCode = 1
}
finally {
    foreach ($entry in $jobs) {
        if ($null -eq $entry) { continue }
        $job = $entry.Job
        if ($job.State -eq 'Running') {
            Stop-Job -Job $job -Force | Out-Null
        }
        Receive-Job -Job $job -Wait -AutoRemoveJob -ErrorAction SilentlyContinue | ForEach-Object {
            if ($null -eq $_) { continue }
            Write-RunLog $entry.Name ($_.ToString())
        }
        if (Get-Job -Id $job.Id -ErrorAction SilentlyContinue) {
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}
