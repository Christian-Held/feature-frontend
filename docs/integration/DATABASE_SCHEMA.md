# Database Schema

Die Plattform nutzt SQLAlchemy mit SQLite (Standard) bzw. kompatiblen RDBMS. Das Schema wird bei Start von `app.main` automatisch erzeugt.

```mermaid
erDiagram
    JOBS ||--o{ JOB_STEPS : contains
    JOBS ||--o{ COST_ENTRIES : tracks
    JOBS ||--o{ MEMORY_ITEMS : stores
    JOBS ||--o{ MEMORY_FILES : stores
    JOBS ||--o{ MESSAGE_SUMMARIES : summarizes
    JOBS ||--o{ CONTEXT_METRICS : records
    JOBS {
        string id PK
        string task
        string repo_owner
        string repo_name
        string branch_base
        string status
        float budget_usd
        int max_requests
        int max_minutes
        string model_cto
        string model_coder
        float cost_usd
        int tokens_in
        int tokens_out
        int requests_made
        datetime started_at
        datetime finished_at
        boolean cancelled
        string last_action
        json pr_links
        string agents_hash
        datetime created_at
        datetime updated_at
    }
    JOB_STEPS {
        string id PK
        string job_id FK
        string name
        string step_type
        string status
        text details
        datetime started_at
        datetime finished_at
        datetime created_at
    }
    COST_ENTRIES {
        string id PK
        string job_id FK
        string provider
        string model
        int tokens_in
        int tokens_out
        float cost_usd
        datetime created_at
    }
    MEMORY_ITEMS {
        string id PK
        string job_id FK
        string kind
        string key
        text content
        datetime created_at
        datetime updated_at
    }
    MEMORY_FILES {
        string id PK
        string job_id FK
        string path
        binary bytes
        datetime created_at
    }
    MESSAGE_SUMMARIES {
        string id PK
        string job_id FK
        string step_id
        string role
        text summary
        int tokens
        datetime created_at
    }
    EMBEDDING_INDEX {
        string id PK
        string scope
        string ref_id
        text text
        json vector
        datetime created_at
    }
    CONTEXT_METRICS {
        string id PK
        string job_id FK
        string step_id
        int tokens_final
        int tokens_clipped
        int compact_ops
        json details
        datetime created_at
    }
```

## Table Details

### jobs
- Persistiert Job-Metadaten und Budgetgrenzen (Quelle: `app/db/models.py`).
- `agents_hash` verknüpft Jobs mit der verwendeten `AGENTS.md`-Version.
- `pr_links` enthält generierte Pull-Request-URLs.

### job_steps
- Speichert die Einzelschritte eines Jobs und deren Status (`planned`, `running`, `completed`, etc.).
- Dient als Grundlage für Fortschrittsberechnung und Event-Emission.

### cost_entries
- Trackt Token- und Kostenwerte pro Agent-Aufruf.
- Grundlage für spätere Billing-Aggregationen.

### memory_items
- JSON-basierte Notizen (`notes`) für Structured Memory.
- Unterstützt Guardrails via `MemoryStore` (Limits, Tags).

### memory_files
- Binäre Artefakte, die Uploads aus `/memory/{job_id}/files` ablegen.
- Pfade referenzieren Sandbox-Verzeichnis `./data`.

### message_summaries
- Persistiert agentenseitige Nachrichten-Zusammenfassungen für Auditing.

### embedding_index
- Speichert Embeddings für Kontextdokumente (Scope `doc`, `memory`, ...).
- Interagiert mit `EmbeddingStore` und OpenAI-Provider.

### context_metrics
- Bewahrt Kontextdiagnosen (Tokens, Kompressionsoperationen) für die UI.
