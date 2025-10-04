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

## Quickstart
1. Kopiere `.env.example` zu `.env` und passe die Werte an.
2. Führe `scripts/setup.ps1` in einer PowerShell (Windows) oder `pwsh` Shell aus.
3. Starte die Dienste mit `scripts/run.ps1`.
4. Optional: Test-Job via `scripts/seed-demo.ps1`.

## Tests
```powershell
uv run pytest
```

## Architektur
Siehe `AGENTS.md` für Richtlinien der Agents. Die Anwendung speichert den Hash der Datei in der Datenbank und referenziert ihn in Pull-Requests.
