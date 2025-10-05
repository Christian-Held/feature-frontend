#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[seed] %s\n' "$1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

load_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 0
  log "Lade Umgebungsvariablen aus $env_file ..."
  eval "$(
    python - "$env_file" <<'PY'
import pathlib
import re
import shlex
import sys

path = pathlib.Path(sys.argv[1])
pattern = re.compile(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')
exports = []
for raw_line in path.read_text(encoding='utf-8').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#'):
        continue
    match = pattern.match(line)
    if not match:
        continue
    key, value = match.groups()
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = bytes(value[1:-1], 'utf-8').decode('unicode_escape')
    elif value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    else:
        if ' #' in value:
            value = value.split('#', 1)[0].rstrip()
        value = value.strip()
    exports.append(f"export {key}={shlex.quote(value)}")

print('\n'.join(exports))
PY
  )"
}

load_env_file "$REPO_ROOT/.env"

: "${APP_PORT:=3000}"
BASE_URL="http://localhost:${APP_PORT%/}"
HEALTH_URL="$BASE_URL/health"
TASK_URL="$BASE_URL/tasks"

log "Warte auf Health Endpoint unter $HEALTH_URL ..."
START_TIME=$(date +%s)
TIMEOUT=60
while true; do
  if RESPONSE="$(curl -sS --max-time 5 "$HEALTH_URL" || true)"; then
    if [[ -n "$RESPONSE" ]]; then
      if python - <<'PY' "$RESPONSE" >/dev/null 2>&1; then
import json
import sys
payload = json.loads(sys.argv[1])
if payload.get('ok'):
    sys.exit(0)
sys.exit(1)
PY
      then
        break
      else
        log "Health Status: $RESPONSE"
      fi
    fi
  fi
  if (( $(date +%s) - START_TIME > TIMEOUT )); then
    log 'Health-Check fehlgeschlagen. API nicht bereit.'
    exit 1
  fi
  sleep 2
done

log 'Health-Check erfolgreich. Erstelle Demo-Task ...'
TASK_BODY=$(python - <<'PY'
import json
import os
payload = {
    "task": "Erstelle ein Web Jump&Run Spiel",
    "repo_owner": os.environ.get("GITHUB_OWNER"),
    "repo_name": os.environ.get("GITHUB_REPO"),
    "branch_base": "main",
    "budgetUsd": 1.0,
    "maxRequests": 50,
    "maxMinutes": 30,
}
print(json.dumps(payload))
PY
)

RESPONSE=$(curl -sS -X POST "$TASK_URL" -H 'Content-Type: application/json' -d "$TASK_BODY")
JOB_ID=$(python - <<'PY' "$RESPONSE"
import json
import sys
try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    sys.exit(1)
job_id = data.get('job_id')
if not job_id:
    sys.exit(1)
print(job_id)
PY
)

if [[ -z "$JOB_ID" ]]; then
  log 'API Response enthielt keine job_id.'
  exit 1
fi

log "Job ID: $JOB_ID"

log 'Verfolge Job-Status ...'
while true; do
  sleep 5
  JOB_RESPONSE=$(curl -sS "$BASE_URL/jobs/$JOB_ID")
  if [[ -z "$JOB_RESPONSE" ]]; then
    log 'Leere Antwort vom Job-Endpunkt.'
    continue
  fi
  python - "$JOB_RESPONSE" <<'PY'
import json
import sys
job = json.loads(sys.argv[1])
status = job.get('status')
progress = job.get('progress', 'n/a')
cost = job.get('cost_usd')
if cost is None:
    cost_display = 'n/a'
else:
    cost_display = f"{float(cost):.2f}"
last_action = job.get('last_action') or 'n/a'
print(f"[seed] Status: {status} | Fortschritt: {progress} | Kosten USD: {cost_display} | Letzte Aktion: {last_action}")
if status not in {'pending', 'running'}:
    if job.get('pr_links'):
        for idx, link in enumerate(job['pr_links'], start=1):
            print(f"[seed] PR #{idx}: {link}")
    elif job.get('pr_urls'):
        for idx, link in enumerate(job['pr_urls'], start=1):
            print(f"[seed] PR #{idx}: {link}")
    sys.exit(0)
PY
  STATUS_EXIT=$?
  if [[ $STATUS_EXIT -eq 0 ]]; then
    break
  fi
  if (( $STATUS_EXIT != 0 && $STATUS_EXIT != 1 )); then
    log "Unerwarteter Fehler beim Lesen des Job-Status ($STATUS_EXIT)."
    break
  fi
  # STATUS_EXIT==1 bedeutet, dass der Job noch läuft und die Schleife weitergehen soll.
done
