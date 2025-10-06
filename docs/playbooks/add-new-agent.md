# Playbook: Add a new agent

## Preconditions
- Neues Agentenprofil (Use-Case, Budget, Modell) ist abgestimmt.
- Zugang zu LLM-Provider oder Custom-Backend vorhanden.
- Test- und Observability-Plan definiert.

## Steps
1. **Agent Skeleton erstellen**
   - Lege Datei `app/agents/<agent_name>.py` an.
   - Implementiere Klasse, die `BaseAgent` erfüllt (`plan`, `execute`, `estimate_cost`).
2. **Router registrieren**
   - Ergänze `AGENT_TYPES` in `app/agents/__init__.py`.
   - Aktualisiere `app/router/agent_router.py` mit Dispatch-Regeln (Komplexität, Budget, Profile).
3. **Settings & Policies**
   - Ergänze `AGENTS.md` um Beschreibung, Kostencharakteristik und Fallbacks.
   - Optional: Settings-API um Modellvarianten erweitern (`_MODEL_DEFINITIONS`).
4. **Tests schreiben**
   - Unit Tests in `tests/agents/test_<agent_name>.py`.
   - Routing-Test in `tests/router/test_routing.py` (neue Branches).
   - Führt `uv run pytest` aus.
5. **Worker überprüfen**
   - Dry-Run via `scripts/run_agent.py --agent <agent_name> --job <job_id>`.
   - Logging-Level temporär auf Debug setzen (`LOG_LEVEL=DEBUG`).
6. **Deployment**
   - Rollout in Staging, verifiziere WebSocket-Events (`job.updated`).
   - Update `docs/architecture/SYSTEM_OVERVIEW.md` falls neue Container benötigt werden.

## Rollback
- Entferne den Agenten aus Router und Settings.
- Lösche Klassendatei und Tests.
- Re-deploy Worker, prüfe, ob Standard-Routing funktioniert.
