$ErrorActionPreference = 'Stop'

Write-Host "[run] Loading environment..."
if (Test-Path .env) {
    foreach ($line in Get-Content .env) {
        if (-not [string]::IsNullOrWhiteSpace($line) -and -not $line.Trim().StartsWith('#')) {
            $name, $value = $line.Split('=', 2)
            $env:$name = $value
        }
    }
}

Write-Host "[run] Starting FastAPI (uvicorn) and Celery worker..."
$api = Start-Process -FilePath "uv" -ArgumentList @('run', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', $env:APP_PORT) -PassThru
$worker = Start-Process -FilePath "uv" -ArgumentList @('run', 'celery', '-A', 'app.workers.celery_app', 'worker', '-l', 'info') -PassThru

Write-Host "[run] Press Ctrl+C to stop."
Wait-Process -Id @($api.Id, $worker.Id)
