# Orchestration Domain

## Purpose
- Automatisiert Planung, Ausführung und Überwachung von Software-Lieferjobs.
- Koordiniert CTO-, Coder- und Spezial-Agenten entlang von Budget- und Policy-Vorgaben.
- Stellt REST- und Event-Schnittstellen für Frontends und externe Integrationen bereit.

## Boundaries
- Umfasst Job- und Step-Management (`jobs`, `job_steps`, `cost_entries`).
- Verwaltet Memory, Kontextdokumente und Dateiuploads für laufende Jobs.
- Exkludiert Benutzeridentität (Auth) und abrechnungsrelevante Aggregationen (Billing).

## API
- `POST /tasks` legt neue Jobs inkl. Budgetgrenzen an.
- `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel`, `GET /jobs/{id}/context` zur Laufzeitsteuerung.
- `POST /context/docs` importiert Wissensdokumente.
- `GET/POST /memory/{job_id}` Endpunkte für Notizen und Files.
- `GET /api/env`, `PUT /api/env/{key}`, `GET /api/models`, `PUT /api/models/{model}` zur Konfiguration.

## Dependencies
- **LLM Providers:** OpenAI und weitere über `app/llm` (Modellauswahl aus Settings).
- **Celery & Redis:** Queueing für Planungs-/Ausführungsschritte und Event-Streaming.
- **SQL Database:** Persistenz der Job- und Kosten-Entities.
- **Git Integrationen:** GitHub-API via `app/git` für Repo-Operationen.

## Integration Points
- React Dashboard (`frontend/`) konsumiert REST- und WebSocket-Endpunkte.
- Gradio UI (`webui/`) nutzt dieselben APIs für manuelle Steuerung.
- Externe Systeme können über WebSocket `ws://<host>/ws/jobs` den Jobstatus abonnieren.
- Settings-API erlaubt Automatisierungstools, Modelle und Secrets zentral zu pflegen.

## Extension Points
- Neue Agents implementieren `BaseAgent` und werden im Router registriert.
- Zusatz-Router können via FastAPI hinzugefügt werden (`app/routers`).
- Kontext-Provider (Embeddings) lassen sich über `app/embeddings` austauschen.
- Job-Lifecycle Hooks über Celery Tasks oder Signals erweiterbar.
