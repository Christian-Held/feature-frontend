-- Context engine schema additions
CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_files (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    path TEXT NOT NULL,
    bytes BLOB NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS message_summaries (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    step_id TEXT,
    role TEXT NOT NULL,
    summary TEXT NOT NULL,
    tokens INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS embedding_index (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    text TEXT NOT NULL,
    vector JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS context_metrics (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    step_id TEXT,
    tokens_final INTEGER DEFAULT 0,
    tokens_clipped INTEGER DEFAULT 0,
    compact_ops INTEGER DEFAULT 0,
    details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
