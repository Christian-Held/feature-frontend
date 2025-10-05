#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[setup] %s\n' "$1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
log "Arbeitsverzeichnis: $REPO_ROOT"

log 'Empfohlene Python-Versionen: 3.12 oder 3.13 (3.11/3.14 Best-Effort).'

PREFERRED_MIN_MINOR=12
PREFERRED_MAX_MINOR=14
PYTHON_VERSION_OUTPUT=""

find_python_in_range() {
  local candidate="$1"
  if [[ -z "$candidate" ]]; then
    return 1
  fi
  local version_output
  if ! version_output="$("$candidate" --version 2>&1)"; then
    return 1
  fi
  local version_str="${version_output#Python }"
  local major minor patch
  IFS='.' read -r major minor patch <<<"$version_str"
  if [[ -z "$major" || -z "$minor" ]]; then
    return 1
  fi
  if (( major == 3 && minor >= PREFERRED_MIN_MINOR && minor < PREFERRED_MAX_MINOR )); then
    PYTHON_VERSION_OUTPUT="$version_output"
    printf '%s\n' "$candidate"
    return 0
  fi
  return 1
}

ACTIVE_PYTHON=""
if command -v python3 >/dev/null 2>&1; then
  ACTIVE_PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  ACTIVE_PYTHON="$(command -v python)"
fi

if [[ -z "$ACTIVE_PYTHON" ]]; then
  log 'Python wurde nicht gefunden. Bitte installiere mindestens Python 3.12.'
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  log "Installiere uv über $ACTIVE_PYTHON ..."
  "$ACTIVE_PYTHON" -m pip install --upgrade uv >/dev/null
fi

PYTHON_PATH=""
PYTHON_MODE=""
if candidate_path="$(find_python_in_range "$ACTIVE_PYTHON" 2>/dev/null)"; then
  if [[ -n "$candidate_path" ]]; then
    PYTHON_PATH="$candidate_path"
    PYTHON_MODE="active"
  fi
fi

if [[ -z "$PYTHON_PATH" ]]; then
  FIND_OUTPUT="$(uv python find 'cpython>=3.12,<3.14' 2>/dev/null || true)"
  if [[ -n "$FIND_OUTPUT" ]]; then
    PYTHON_PATH="$(printf '%s\n' "$FIND_OUTPUT" | head -n1 | tr -d '\r')"
    if [[ -n "$PYTHON_PATH" ]]; then
      PYTHON_VERSION_OUTPUT="$("$PYTHON_PATH" --version 2>&1)"
      PYTHON_MODE="uv-find"
    fi
  fi
fi

if [[ -z "$PYTHON_PATH" ]]; then
  PYTHON_PATH="$ACTIVE_PYTHON"
  PYTHON_VERSION_OUTPUT="$("$PYTHON_PATH" --version 2>&1)"
  PYTHON_MODE="best-effort"
  log "Hinweis: Kein Interpreter innerhalb >=3.12,<3.14 gefunden. Fahre im Best-Effort-Modus mit $PYTHON_VERSION_OUTPUT fort."
fi

if [[ -z "$PYTHON_VERSION_OUTPUT" ]]; then
  PYTHON_VERSION_OUTPUT="$("$PYTHON_PATH" --version 2>&1)"
fi

if [[ -z "$PYTHON_MODE" && "$PYTHON_PATH" == "$ACTIVE_PYTHON" ]]; then
  PYTHON_MODE="active"
fi
if [[ -z "$PYTHON_MODE" ]]; then
  PYTHON_MODE="uv-find"
fi

log "Nutze Python Interpreter ($PYTHON_MODE): $PYTHON_PATH [$PYTHON_VERSION_OUTPUT]"

export UV_PROJECT_ENVIRONMENT="$REPO_ROOT/.venv"
log "uv Projektumgebung: $UV_PROJECT_ENVIRONMENT"

log 'Synchronisiere Abhängigkeiten mit uv ...'
if [[ "$PYTHON_MODE" == 'best-effort' ]]; then
  log 'Best-Effort: uv sync nutzt den aktiven Interpreter und kann bei inkompatibler Version fehlschlagen. Empfohlen ist Python 3.12 oder 3.13.'
fi
uv sync --extra tests --python "$PYTHON_PATH"

log 'Stelle Datenverzeichnis bereit ...'
mkdir -p data

log 'Prüfe Docker Installation ...'
if ! docker info >/dev/null 2>&1; then
  log 'Docker scheint nicht zu laufen. Bitte starte Docker und versuche es erneut.'
  exit 1
fi

log 'Starte Redis via Docker Compose ...'
docker compose up -d orchestrator-redis

log 'Warte auf Redis (Port 6379) ...'
START_TIME=$(date +%s)
TIMEOUT=60
while true; do
  if "$PYTHON_PATH" - <<'PY' >/dev/null 2>&1; then
import socket
with socket.create_connection(("127.0.0.1", 6379), timeout=0.5):
    pass
PY
  then
    break
  fi
  if (( $(date +%s) - START_TIME > TIMEOUT )); then
    log 'Redis ist nicht erreichbar (Port 6379).'
    exit 1
  fi
  sleep 1
done

log 'Redis erreichbar. Setup abgeschlossen.'
