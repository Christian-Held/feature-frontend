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
2. Starte eine PowerShell und führe `scripts/setup.ps1` aus. Das Skript ruft `uv sync`, pinnt `uv python` auf 3.12, startet Redis via Docker Compose und wartet, bis Port 6379 erreichbar ist.
3. Dienste starten mit `scripts/run.ps1`. Das Skript lädt `.env`, setzt die Variablen per `Set-Item`, startet `uvicorn` (API) und den Celery-Worker parallel und zeigt kompakte Logs.
4. Optional kannst du nach erfolgreichem Health-Check `scripts/seed-demo.ps1` ausführen. Das Skript wartet bis `/health` "ok" liefert und legt anschließend einen Demojob an.

## Tests
```powershell
uv run pytest
```

## Gradio Web UI
Die Weboberfläche befindet sich in `webui/app_gradio.py`. Sie nutzt Gradio Blocks mit separaten Accordions für Secrets und Settings, kann `.env` lokal speichern und interagiert mit dem Backend über die REST-Endpunkte (`/health`, `/tasks`, `/jobs/{id}`).

```powershell
python webui/app_gradio.py
```

## Architektur
Siehe `AGENTS.md` für Richtlinien der Agents. Die Anwendung speichert den Hash der Datei in der Datenbank und referenziert ihn in Pull-Requests.
