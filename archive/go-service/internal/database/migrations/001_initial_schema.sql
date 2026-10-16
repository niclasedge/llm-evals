-- Initial database schema for LLM evaluation results
-- Matches the Python EvaluationResult format exactly

CREATE TABLE IF NOT EXISTS evaluation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    test_name TEXT NOT NULL,
    test_type TEXT NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    expected_response TEXT,
    metrics TEXT, -- JSON blob
    score REAL DEFAULT 0.0,
    passed BOOLEAN DEFAULT 0,
    execution_time REAL DEFAULT 0.0,
    error_message TEXT,
    metadata TEXT -- JSON blob
);

-- Evaluation sessions for tracking long-running evaluations
CREATE TABLE IF NOT EXISTS evaluation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    status TEXT DEFAULT 'running', -- running, completed, failed
    total_tests INTEGER DEFAULT 0,
    completed_tests INTEGER DEFAULT 0,
    metadata TEXT -- JSON blob
);

-- Performance metrics tracking
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_name TEXT NOT NULL,
    test_type TEXT NOT NULL,
    avg_execution_time REAL,
    success_rate REAL,
    total_requests INTEGER,
    metadata TEXT -- JSON blob
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_timestamp ON evaluation_results(timestamp);
CREATE INDEX IF NOT EXISTS idx_model ON evaluation_results(model_provider, model_name);
CREATE INDEX IF NOT EXISTS idx_test_type ON evaluation_results(test_type);
CREATE INDEX IF NOT EXISTS idx_session_id ON evaluation_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_performance_model ON performance_metrics(model_name, test_type);