-- Hermes Multi-Agent Orchestrator — SQLite Schema
-- Version: 1.0 (MVP-001)

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Task lifecycle: inbox → planning → planned → ready → claimed → running → review → done
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,                    -- T-{6hex}
    parent_id TEXT,                         -- for subtask trees
    title TEXT NOT NULL,
    user_request TEXT,                      -- original user input
    status TEXT NOT NULL DEFAULT 'inbox',   -- see state machine
    owner_agent TEXT,                       -- current responsible agent
    priority TEXT DEFAULT 'medium',         -- low|medium|high|critical
    risk_level TEXT DEFAULT 'low',          -- low|medium|high
    plan_yaml TEXT,                         -- serialized plan (JSON or YAML)
    version INTEGER NOT NULL DEFAULT 1,     -- optimistic lock counter
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES tasks(id)
);

-- Event sourcing: every state change, claim, failure logged here
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent TEXT,
    event_type TEXT NOT NULL,               -- created|status_change|assigned|claimed|...
    message TEXT,
    metadata TEXT,                          -- JSON blob for structured data
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Agent registry
CREATE TABLE IF NOT EXISTS agents (
    name TEXT PRIMARY KEY,
    role TEXT,
    capabilities TEXT,                      -- JSON array
    status TEXT NOT NULL DEFAULT 'unknown', -- available|limited|exhausted|unavailable|unknown
    last_success_at TEXT,
    last_failure_at TEXT,
    last_error TEXT,
    cooldown_until TEXT,
    cost_tier TEXT,
    planner_priority INTEGER,               -- higher = preferred as planner
    worker_priority INTEGER                 -- higher = preferred as worker
);

-- Worker outputs
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent TEXT,
    kind TEXT NOT NULL,                     -- patch|summary|test_log|file
    path TEXT,                              -- file path (if external)
    content TEXT,                           -- inline content (if small)
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Decision audit trail
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    title TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    impact TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Agent resource tracking
CREATE TABLE IF NOT EXISTS resource_status (
    agent TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'unknown',
    reason TEXT,
    last_checked_at TEXT,
    last_error TEXT,
    cooldown_until TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_agent);
CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
CREATE INDEX IF NOT EXISTS idx_decisions_task ON decisions(task_id);
