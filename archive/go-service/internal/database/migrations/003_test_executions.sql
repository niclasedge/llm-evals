-- Test execution tracking migration
-- Adds comprehensive test execution tracking with enhanced metadata

CREATE TABLE test_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Test identification and type
    test_type VARCHAR(50) NOT NULL,                    -- coding, reasoning, creative, tool-calling
    test_category VARCHAR(100),                        -- subcategory within test type
    test_name VARCHAR(200),                           -- specific test or problem name
    
    -- Model and configuration
    model_name VARCHAR(100) NOT NULL,                 -- LLM model used
    model_provider VARCHAR(50),                       -- ollama, openrouter, openai
    model_version VARCHAR(50),                        -- model version if available
    
    -- Test content and parameters
    prompt TEXT NOT NULL,                             -- test prompt/question
    parameters TEXT,                                  -- JSON: model parameters (temperature, max_tokens, etc.)
    expected_output TEXT,                             -- expected result for validation
    
    -- Execution tracking
    status VARCHAR(20) DEFAULT 'pending',             -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time_ms INTEGER,                        -- execution duration in milliseconds
    
    -- Results and scoring
    raw_response TEXT,                                -- complete model response
    score REAL,                                       -- calculated score (0.0 - 1.0)
    score_breakdown TEXT,                            -- JSON: detailed scoring information
    
    -- Context and metadata
    correlation_id VARCHAR(50),                       -- request correlation ID
    user_id VARCHAR(100),                            -- user who initiated test (if applicable)
    session_id VARCHAR(100),                         -- test session grouping
    environment VARCHAR(50) DEFAULT 'development',    -- development, staging, production
    
    -- Error handling
    error_message TEXT,                               -- error details if execution failed
    retry_count INTEGER DEFAULT 0,                   -- number of retry attempts
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX idx_test_executions_model_type ON test_executions(model_name, test_type);
CREATE INDEX idx_test_executions_status_created ON test_executions(status, created_at);
CREATE INDEX idx_test_executions_correlation_id ON test_executions(correlation_id);
CREATE INDEX idx_test_executions_session_id ON test_executions(session_id);
CREATE INDEX idx_test_executions_completed_at ON test_executions(completed_at);
CREATE INDEX idx_test_executions_score ON test_executions(score) WHERE score IS NOT NULL;

-- Composite indexes for complex queries
CREATE INDEX idx_test_executions_model_date ON test_executions(model_name, DATE(created_at));
CREATE INDEX idx_test_executions_type_status_date ON test_executions(test_type, status, created_at);

-- Foreign key relationship to evaluation_sessions if session_id is provided
-- Note: SQLite foreign keys are enforced only if PRAGMA foreign_keys = ON
-- The session_id can link to evaluation_sessions.session_id for session tracking