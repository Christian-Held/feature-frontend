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
Write-SeedLog "Job ID: $jobId"

Write-SeedLog 'Verfolge Job-Status ...'
do {
    Start-Sleep -Seconds 5
    $job = Invoke-RestMethod -Method Get -Uri "$baseUrl/jobs/$jobId"
    $progress = if ($job.progress) { $job.progress } else { 'n/a' }
    Write-SeedLog "Status: $($job.status) | Fortschritt: $progress | Kosten USD: $($job.cost_usd)"
} while ($job.status -in @('pending', 'running'))

if ($job.pr_links) {
    Write-SeedLog "PR Links: $($job.pr_links -join ', ')"
} elseif ($job.pr_urls) {
    Write-SeedLog "PR Links: $($job.pr_urls -join ', ')"
} else {
    Write-SeedLog 'Keine PR erstellt.'
}
