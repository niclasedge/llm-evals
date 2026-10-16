-- Performance metrics enhancement
-- Add additional performance tracking tables

CREATE TABLE IF NOT EXISTS model_performance_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    test_type TEXT NOT NULL,
    period_start DATETIME NOT NULL,
    period_end DATETIME NOT NULL,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    avg_score REAL DEFAULT 0.0,
    avg_execution_time REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_provider, model_name, test_type, period_start, period_end)
);

-- Add additional indexes
CREATE INDEX IF NOT EXISTS idx_performance_summary_model ON model_performance_summary(model_provider, model_name);
CREATE INDEX IF NOT EXISTS idx_performance_summary_period ON model_performance_summary(period_start, period_end);