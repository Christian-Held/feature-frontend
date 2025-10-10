param(
    [string]$BaseUrl = "http://localhost:8000"
)

function Invoke-JsonPost {
    param(
        [string]$Url,
        [hashtable]$Body
    )
    $json = $Body | ConvertTo-Json -Depth 6
    return Invoke-RestMethod -Method Post -Uri $Url -Body $json -ContentType "application/json"
}

Write-Host "Seeding external context docs..."
Invoke-JsonPost -Url "$BaseUrl/context/docs" -Body @{ title = "Architecture Overview"; text = "Monorepo layout, job orchestrator, celery workers." }
Invoke-JsonPost -Url "$BaseUrl/context/docs" -Body @{ title = "Coding Standards"; text = "Use unified diff, respect AGENTS.md, avoid destructive commands." }

Write-Host "Seeding memory notes..."
Invoke-JsonPost -Url "$BaseUrl/memory/demo-job/notes" -Body @{ type = "Decision"; title = "Use Context Engine"; body = "Enable curated context per step."; tags = @("context", "engine") }
Invoke-JsonPost -Url "$BaseUrl/memory/demo-job/notes" -Body @{ type = "Constraint"; title = "Token Budget"; body = "Keep prompts under 64k tokens with 8k reserve."; tags = @("budget") }

Write-Host "Starting demo task..."
$task = Invoke-JsonPost -Url "$BaseUrl/tasks" -Body @{ task = "Demonstrate context engine"; repo_owner = "demo"; repo_name = "demo-repo"; branch_base = "main"; budgetUsd = 5; maxRequests = 50; maxMinutes = 60 }
$jobId = $task.job_id
Write-Host "Job queued:" $jobId

Start-Sleep -Seconds 2
try {
    $context = Invoke-RestMethod -Method Get -Uri "$BaseUrl/jobs/$jobId/context"
    Write-Host "Context diagnostics:" ($context | ConvertTo-Json -Depth 6)
} catch {
    Write-Warning "Context diagnostics not yet available."
}

try {
    $job = Invoke-RestMethod -Method Get -Uri "$BaseUrl/jobs/$jobId"
    if ($job.pr_links) {
        Write-Host "PR Links:"
        $job.pr_links | ForEach-Object { Write-Host " - $_" }
    }
} catch {
    Write-Warning "Job status unavailable."
}
