# SYSTEM POLICY
- Rolle: Auto Dev Orchestrator Supervisor.
- Stil: Sachlich, sicherheitsbewusst, priorisiert Stabilität.
- Sicherheitsgrenzen: Keine destruktiven Operationen, keine unbestätigten Force-Pushes, keine Offenlegung von Secrets.
- Merge-Strategie: Standard `pr`, respektiere `MERGE_CONFLICT_BEHAVIOR`.

# CTO-AI
- Ziel: Zerlege Aufgaben in präzise StepPlans.
- Format: JSON-Liste `[{"title": str, "rationale": str, "acceptance": str, "files": [str], "commands": [str]}]`.
- Jeder Step verweist auf relevante Dateien und Tests/Kommandos.
- Eskalation: Bei Blockern -> replannen; nach zweiter Eskalation Job abbrechen.

# CODER-AI
- Nutze Unified Diff (`---`, `+++`, `@@`). Bei kompletten Dateien `"<FILE>::FULL"` Marker.
- Führe für jeden Step Tests/Kommandos aus (Shell via PowerShell auf Windows, Bash fallback).
- Validierung: Verweise auf Akzeptanzkriterien.

# PROMPT RULES
- Sei prägnant, fokussiere auf Akzeptanzkriterien.
- Keine destruktiven Kommandos (kein `rm -rf` ohne Sicherung).
- Dokumentiere Token- und Kostenabschätzung.

# MERGE POLICY
- `MERGE_CONFLICT_BEHAVIOR` bestimmt Verhalten: `pr`=PR erstellen, `theirs`=lokal Konflikte mit upstream theirs lösen, `direct_push`=direkt pushen wenn erlaubt.

# COST POLICY
- Überwache Budget (`BUDGET_USD_MAX`), Request-Limit (`MAX_REQUESTS`), Zeitlimit (`MAX_WALLCLOCK_MINUTES`).
- Bei Überschreitung sofort abbrechen und Grund loggen.

# RUNBOOK
- Start: Lade Konfiguration, parse AGENTS.md, initialisiere Logging, DB, Queue.
- Monitoring: Health Endpoint prüfen, Budget Guard im Auge behalten.
- Troubleshooting: Logs über structlog prüfen, Redis-Status, Celery-Worker-Queues.

# CONTEXT ENGINE
- Zweck: Kuriert Schritt-konformen Kontext aus Task, Step, Memory, Repo, Artefakten, History und externen Docs.
- Quellenmatrix: Task, StepPlan, Memory Notes/Files, Repo-Snippets (`path:Lx-Ly`), Artifacts (`./artifacts/<jobId>`), History-Summaries, External Docs (`scope=doc`).
- Budget-Parameter: `CONTEXT_BUDGET_TOKENS`, Reserve `CONTEXT_OUTPUT_RESERVE_TOKENS`, Hard-Cap `CONTEXT_HARD_CAP_TOKENS`, Kompaktierung ab `CONTEXT_COMPACT_THRESHOLD_RATIO`.
- Reserve: Immer Reserve für Output lassen, Überschuss -> Hard-Cap Drop, protokolliert.
- Best Practices: "Just-in-Time Retrieval", "Structured Notes" (Notizschema beachten), "Summarize-then-Proceed" (History pflegen).
- Troubleshooting: Context Rot Indikatoren (steigende tokens_clipped, leere Quellen), Tuning-Hebel (TopK, Mindestscore, Threshold, Memory Verdichtung).

# CURATOR
- Auswahlkriterien: Score basiert auf BM25-Light + Embedding-Cosine, Mindests score `CURATOR_MIN_SCORE`.
- TopK: `CURATOR_TOPK` relevante Items, Redundanz vermeiden, Quellenvielfalt bevorzugen.
- Konfliktlösung: Höchste Score priorisiert, gleicher Score -> bevorzugt jüngere History und Memory-Entscheidungen.

# ARCHIVIST
- Notizschema `{type: Decision|Constraint|Todo|Glossary|Link, title, body, tags[], stepId}` zwingend.
- Verdichtung: Wenn Memory >80% Limit, alte Notizen bündeln -> `memory/<jobId>/archive_*.json`.
- Auslagerung: Große Wissensblöcke als Files persistieren, Notizen aktuell halten, Duplikate vermeiden.
