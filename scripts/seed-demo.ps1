$ErrorActionPreference = 'Stop'

$baseUrl = "http://localhost:${env:APP_PORT}".TrimEnd('/')
$taskBody = @{
    task = "Erstelle ein Web Jump&Run Spiel"
    repo_owner = $env:GITHUB_OWNER
    repo_name = $env:GITHUB_REPO
    branch_base = "main"
    budgetUsd = 1.0
    maxRequests = 50
    maxMinutes = 30
} | ConvertTo-Json

Write-Host "[seed] Posting demo task..."
$response = Invoke-RestMethod -Method Post -Uri "$baseUrl/tasks" -ContentType 'application/json' -Body $taskBody
$jobId = $response.job_id
Write-Host "[seed] Job ID: $jobId"

Write-Host "[seed] Polling job status..."
do {
    Start-Sleep -Seconds 5
    $job = Invoke-RestMethod -Method Get -Uri "$baseUrl/jobs/$jobId"
    Write-Host "[seed] Status: $($job.status) | Fortschritt: $($job.progress) | Kosten: $($job.cost_usd)"
} while ($job.status -in @('pending', 'running'))

if ($job.pr_links) {
    Write-Host "[seed] PRs: $($job.pr_links -join ', ')"
} else {
    Write-Host "[seed] Keine PR erstellt."
}
