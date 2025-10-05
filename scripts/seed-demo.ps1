[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-SeedLog {
    param(
        [string]$Message
    )
    Write-Host "[seed] $Message"
}

function Get-RepoRoot {
    param(
        [string]$ScriptPath
    )
    $scriptsDir = Split-Path -Path $ScriptPath -Parent
    return Resolve-Path -Path (Join-Path $scriptsDir '..')
}

function Import-DotEnv {
    param(
        [string]$Path
    )

    if (-not (Test-Path -Path $Path)) {
        return
    }

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
        $value = $match.Groups['value'].Value
        $trimmedValue = $value.Trim()

        if ($trimmedValue.StartsWith('"') -and $trimmedValue.EndsWith('"')) {
            $value = $trimmedValue.Substring(1, $trimmedValue.Length - 2).Replace('\\"', '"')
        } elseif ($trimmedValue.StartsWith("'") -and $trimmedValue.EndsWith("'")) {
            $value = $trimmedValue.Substring(1, $trimmedValue.Length - 2)
        } else {
            $commentIndex = -1
            for ($i = 0; $i -lt $value.Length; $i++) {
                if ($value[$i] -eq '#') {
                    if ($i -gt 0 -and [char]::IsWhiteSpace($value[$i - 1])) {
                        $commentIndex = $i
                        break
                    }
                }
            }
            if ($commentIndex -ge 0) {
                $value = $value.Substring(0, $commentIndex)
            }
            $value = $value.Trim()
        }

        Set-Item -Path ("Env:{0}" -f $name) -Value $value
    }
}

$repoRoot = Get-RepoRoot -ScriptPath $PSCommandPath
Set-Location -Path $repoRoot
Import-DotEnv -Path (Join-Path $repoRoot '.env')

if (-not $env:APP_PORT -or [string]::IsNullOrWhiteSpace($env:APP_PORT)) {
    $env:APP_PORT = '3000'
}

$baseUrl = "http://localhost:$($env:APP_PORT)".TrimEnd('/')
$healthUrl = "$baseUrl/health"
$taskUrl = "$baseUrl/tasks"

Write-SeedLog "Warte auf Health Endpoint unter $healthUrl ..."
$deadline = (Get-Date).AddSeconds(60)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 5
        if ($response -and $response.ok) {
            $healthy = $true
            break
        }
        Write-SeedLog "Health Status: $($response | ConvertTo-Json -Compress)"
    }
    catch {
        Write-SeedLog "Health Check fehlgeschlagen: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    throw 'Health-Check fehlgeschlagen. API nicht bereit.'
}

Write-SeedLog 'Health-Check erfolgreich. Erstelle Demo-Task ...'
$taskBody = @{
    task = 'Erstelle ein Web Jump&Run Spiel'
    repo_owner = $env:GITHUB_OWNER
    repo_name = $env:GITHUB_REPO
    branch_base = 'main'
    budgetUsd = 1.0
    maxRequests = 50
    maxMinutes = 30
} | ConvertTo-Json -Depth 4

$response = Invoke-RestMethod -Method Post -Uri $taskUrl -ContentType 'application/json' -Body $taskBody
$jobId = $response.job_id
if (-not $jobId) {
    throw 'API Response enthielt keine job_id.'
}
Write-SeedLog "Job ID: $jobId"

Write-SeedLog 'Verfolge Job-Status ...'
do {
    Start-Sleep -Seconds 5
    $job = Invoke-RestMethod -Method Get -Uri "$baseUrl/jobs/$jobId"
    $progress = if ($job.progress -ne $null) { $job.progress } else { 'n/a' }
    $cost = if ($job.cost_usd -ne $null) { '{0:N2}' -f [double]$job.cost_usd } else { 'n/a' }
    $lastAction = if ($job.last_action) { $job.last_action } else { 'n/a' }
    Write-SeedLog "Status: $($job.status) | Fortschritt: $progress | Kosten USD: $cost | Letzte Aktion: $lastAction"
} while ($job.status -in @('pending', 'running'))

$links = @()
if ($job.pr_links) {
    $links = $job.pr_links
} elseif ($job.pr_urls) {
    $links = $job.pr_urls
}

if ($links.Count -gt 0) {
    $index = 1
    foreach ($link in $links) {
        Write-SeedLog ("PR #{0}: {1}" -f $index, $link)
        $index++
    }
} else {
    Write-SeedLog 'Keine PR erstellt.'
}
