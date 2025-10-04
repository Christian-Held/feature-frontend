# Auto Dev Orchestrator (Python)

Auto Dev Orchestrator ist ein FastAPI- und Celery-basiertes Grundgerüst, das automatisierte Softwarelieferung orchestriert. Das System liest zur Laufzeit **AGENTS.md**, um CTO- und Coder-Agenten anzuleiten, überwacht Budget- und Request-Limits und erstellt Pull Requests mit GitHub-Integration.

## Features
- FastAPI REST-API (`/tasks`, `/jobs/{id}`, `/jobs/{id}/cancel`, `/health`).
- Celery Worker mit Redis-Broker für die schrittweise Ausführung (`plan → code → verify → pr`).
- SQLite-Datenbank (SQLAlchemy) zur Nachverfolgung von Jobs, Steps und Kosten.
- Strukturierte JSON-Logs über structlog.
- LLM-Provider-Abstraktion (OpenAI, Ollama optional) mit Kosten-Tracking.
- GitHub-Integration über PyGithub und GitPython.
- Windows-freundliche PowerShell-Skripte (`scripts/`).
- Tests mit pytest (Unit & E2E-Dry-Run).

## Voraussetzungen
- Windows 11 mit [Docker Desktop](https://www.docker.com/products/docker-desktop/) (muss vor dem Setup laufen).
- Python 3.12 (CPython) und [uv](https://docs.astral.sh/uv/).
- PowerShell 7+ (oder `pwsh` auf anderen Plattformen).

## Quickstart
1. Kopiere `.env.example` zu `.env` und fülle die benötigten Schlüssel (`OPENAI_API_KEY`, `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, `REDIS_URL`, `DB_PATH`, Limits usw.).
2. Öffne PowerShell (`pwsh`) im Repo und führe `pwsh -File scripts/setup.ps1` aus. Das Skript synchronisiert alle Abhängigkeiten via `uv sync`, pinnt `uv python` auf CPython 3.12, legt `data/` an, prüft Docker Desktop und startet Redis über Docker Compose.
3. Starte API und Worker mit `pwsh -File scripts/run.ps1`. Das Skript setzt das Arbeitsverzeichnis auf das Repo-Root, lädt `.env` zuverlässig über das `Env:`-Drive und startet `uv run uvicorn app.main:app` sowie `uv run celery -A app.workers.celery_app worker`.
4. Öffne für die Weboberfläche ein neues Terminal und starte `uv run python -m webui.app_gradio`. Die UI läuft unabhängig vom Backend und nutzt dieselben REST-Endpunkte.
5. Optional kannst du nach erfolgreichem Health-Check `pwsh -File scripts/seed-demo.ps1` ausführen. Das Skript pollt `/health` bis zu 60s, legt einen Demo-Task an und verfolgt den Job inkl. Kosten und PR-Links.

## Tests
```powershell
uv run pytest
```

## Gradio Web UI
Die Weboberfläche befindet sich in `webui/app_gradio.py` und bleibt vom Python-Paket `app` getrennt. Sie nutzt Gradio Blocks mit separaten Accordions für Secrets und Settings, kann `.env` lokal speichern und interagiert mit dem Backend über die REST-Endpunkte (`/health`, `/tasks`, `/jobs/{id}`).

```powershell
uv run python -m webui.app_gradio
```

## Architektur
Siehe `AGENTS.md` für Richtlinien der Agents. Die Anwendung speichert den Hash der Datei in der Datenbank und referenziert ihn in Pull-Requests.
