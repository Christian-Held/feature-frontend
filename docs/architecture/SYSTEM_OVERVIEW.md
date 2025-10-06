# System Overview

## Context Diagram (C4 Level 1)

```mermaid
C4Context
    title Auto Dev Orchestrator – Context Diagram
    Person(client, "Delivery Engineer", "Plant Jobs, beobachtet Fortschritt und verwaltet Modelle")
    Person(github, "GitHub", "Quelle für Repositories und Pull-Requests")
    System_Boundary(system, "Auto Dev Orchestrator Platform") {
        System(back_api, "FastAPI Backend", "Plant, überwacht und orchestriert Jobs")
        System(frontend, "React Dashboard", "Visualisiert Jobs, Einstellungen und Dateibrowser")
        System(gradio, "Gradio UI", "Alternative UI für interaktive Steuerung")
    }
    System_Ext(redis, "Redis", "Message Broker für Celery und Job-Events")
    System_Ext(sqlite, "SQL Database", "Persistente Ablage für Jobs, Kosten, Memory und Kontext")
    System_Ext(llm, "LLM Provider", "OpenAI/Ollama für CTO-, Coder- und Custom-Agenten")
    Rel(client, frontend, "Verwaltet Jobs & Einstellungen")
    Rel(client, gradio, "Startet Jobs & überwacht Ergebnisse")
    Rel(frontend, back_api, "REST & WebSocket Requests")
    Rel(gradio, back_api, "REST API Calls")
    Rel(back_api, redis, "Celery Tasks & Pub/Sub Events")
    Rel(back_api, sqlite, "ORM Persistenz über SQLAlchemy")
    Rel(back_api, llm, "LLM Prompts & Kosten-Tracking")
    Rel(back_api, github, "Repo- und PR-Operations")
```

## Container Diagram (C4 Level 2)

```mermaid
C4Container
    title Auto Dev Orchestrator – Container Diagram
    Person(client, "Delivery Engineer")
    System_Boundary(system, "Auto Dev Orchestrator Platform") {
        Container(api, "FastAPI Service", "Python/FastAPI", "REST API, WebSocket, Settings, Task-Enqueue")
        Container(worker, "Celery Worker", "Python/Celery", "Führt CTO-, Coder- und Integrationsschritte aus")
        Container(frontend, "React Dashboard", "TypeScript/Vite", "Job Monitoring, Settings, File Browser")
        Container(gradio, "Gradio UI", "Python/Gradio", "Alternative UI für Rapid Demos")
        ContainerDb(sqlite, "SQL Database", "SQLite", "Jobs, Steps, Kosten, Memory, Context Metrics")
        Container(redis, "Redis", "Redis", "Broker für Celery & Pub/Sub für Job Events")
    }
    System_Ext(llm, "LLM Provider APIs", "OpenAI, Claude, kundenspezifische Modelle")
    System_Ext(github, "GitHub API", "Repos & Pull Requests")

    Rel(client, frontend, "HTTP/WebSocket")
    Rel(client, gradio, "HTTP")
    Rel(frontend, api, "REST/JSON, WebSocket Events")
    Rel(gradio, api, "REST/JSON")
    Rel(api, worker, "Celery Queue über Redis")
    Rel(api, sqlite, "SQLAlchemy ORM")
    Rel(worker, sqlite, "SQLAlchemy ORM")
    Rel(api, redis, "Pub/Sub job-events")
    Rel(worker, redis, "Publish job events")
    Rel(worker, llm, "LLM Prompting & Kostenmessung")
    Rel(worker, github, "Repo Sync, Branches, PRs")
```

## Architektur-Hauptpunkte

- **Domänenorientierung:** Die Plattform folgt einem Domain-Driven-Design-Ansatz mit Kernfokus auf der *Orchestration*-Domäne. Erweiterbare Domänen für Authentifizierung und Billing sind bereits vorgesehen.
- **Multi-Agent-Orchestrierung:** Die CTO-, Coder-, CustomCoder-, ClaudeCode- und Codex-Agenten koordinieren sich über den Agent Router. Informationen zur Agentenlandschaft stammen aus `AGENTS.md` und werden beim Start eingelesen.
- **Event-getriebene Transparenz:** Jobstatus und Kostenupdates werden über Redis Pub/Sub verteilt und über WebSockets in Frontends angezeigt.
- **Konfigurierbarkeit & Guardrails:** Settings-API und Environment-Management stellen sicher, dass Model- und Budgetgrenzen dynamisch angepasst werden können. Budget Guards sind zentral im Healthcheck einsehbar.

## Laufzeitfluss (High-Level)

1. **Task-Anlage:** Ein:e Engineer:in oder die UI erstellt über `/tasks` einen neuen Job. Der Backend-Service persistiert den Job, legt Budgetlimits fest und übergibt die Arbeit an den Celery-Worker.
2. **Planning:** Der CTO-Agent erzeugt Step-Pläne, wobei `AGENTS.md` als Policies dient. Ergebnisse werden in der Datenbank gespeichert.
3. **Execution:** Der Agent Router weist Schritte geeigneten Agents zu. Der Coder-Agent erstellt Diffs, führt Tests aus und aktualisiert Jobkosten.
4. **Events & Monitoring:** Fortschritt, Kosten und Kontextmetriken werden kontinuierlich in der Datenbank protokolliert und über Redis `job-events` an verbundene Clients gestreamt.
5. **Completion:** Sobald alle Steps abgeschlossen sind, aktualisiert das System den Jobstatus, erstellt optional Pull Requests und signalisiert Abschlussereignisse.

## Nicht-funktionale Anforderungen

- **Stabilität:** Start-up Hooks bauen Datenbankschemata automatisch auf und verhindern fehlende Agentenspezifikationen.
- **Transparenz:** Kosten-Tracking pro Agent und Rolling-Averages für Performance (siehe `AGENTS.md`).
- **Skalierbarkeit:** API- und Worker-Container können unabhängig horizontal skaliert werden; Redis dient als shared broker.
- **Compliance & Sicherheit:** Secrets werden über Settings-API verwaltet, Dateibrowser hat Pfad-Sandboxing und Memory Store erzwingt Limits.

## Schnittstellen

- **REST API:** Siehe `docs/integration/API_CONTRACTS.yaml` für formale Contracts.
- **WebSocket:** Echtzeit-Events unter `ws://<host>/ws/jobs`.
- **Dateisystem:** Sandbox unter `./data` für temporäre Artefakte.

## Offene Fragen & Erweiterungen

- **Auth-System:** Zukünftige Integration eines dedizierten AuthN/AuthZ-Services (siehe Domain-Placeholder & Playbook).
- **Billing-Integration:** Erweiterung der Kostenmodelle um provider-spezifische Abrechnung und Export nach externen Systemen.
- **Model Governance:** Ausbau der Settings-API um Modellparameter, Rate Limits und Audit Trails.
