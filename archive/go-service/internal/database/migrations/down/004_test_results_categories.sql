-- Rollback test_results and test_categories tables
-- Data preservation strategy for existing test data

-- Create migration_log table if it doesn't exist for detailed tracking
CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Log rollback start
INSERT INTO migration_log (migration_name, action, timestamp) 
VALUES ('004_test_results_categories', 'rollback_start', CURRENT_TIMESTAMP);

-- Backup existing data before rollback (if any exists)
CREATE TABLE IF NOT EXISTS test_results_backup AS 
SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
FROM test_results;

CREATE TABLE IF NOT EXISTS test_categories_backup AS 
SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
FROM test_categories;

-- Log data backup
INSERT INTO migration_log (migration_name, action, details) 
VALUES ('004_test_results_categories', 'data_backup', 
        'Backed up ' || (SELECT COUNT(*) FROM test_results) || ' results and ' ||
        (SELECT COUNT(*) FROM test_categories) || ' categories');

-- Remove foreign key constraint from test_executions
DROP INDEX IF EXISTS idx_test_executions_category_id;

-- Use ALTER TABLE DROP COLUMN for SQLite (SQLite doesn't support DROP COLUMN in older versions)
-- For newer SQLite versions, this will work. For older versions, we need a workaround.
-- First try the direct approach
-- Note: SQLite 3.35.0+ supports DROP COLUMN, fallback to recreation if needed
PRAGMA table_info(test_executions);

-- For compatibility, we'll create a new table without the category_id column
CREATE TABLE test_executions_temp AS 
SELECT id, test_type, test_category, test_name, model_name, 
       model_provider, model_version, prompt, parameters, expected_output,
       status, started_at, completed_at, execution_time_ms, raw_response,
       score, score_breakdown, correlation_id, user_id, session_id, 
       environment, error_message, retry_count, created_at, updated_at
FROM test_executions;

-- Drop the original table and rename temp table
DROP TABLE test_executions;
ALTER TABLE test_executions_temp RENAME TO test_executions;

-- Recreate indexes for test_executions (without category_id index)
CREATE INDEX idx_test_executions_session_id ON test_executions(session_id);
CREATE INDEX idx_test_executions_correlation_id ON test_executions(correlation_id);
CREATE INDEX idx_test_executions_status_created ON test_executions(status, created_at);
CREATE INDEX idx_test_executions_model_type ON test_executions(model_name, test_type);
CREATE INDEX idx_test_executions_completed_at ON test_executions(completed_at) WHERE completed_at IS NOT NULL;
CREATE INDEX idx_test_executions_score ON test_executions(score) WHERE score IS NOT NULL;
CREATE INDEX idx_test_executions_model_date ON test_executions(model_name, created_at);
CREATE INDEX idx_test_executions_type_status_date ON test_executions(test_type, status, created_at);

-- Drop indexes for test_results
DROP INDEX IF EXISTS idx_test_results_execution_type;
DROP INDEX IF EXISTS idx_test_results_created_at;
DROP INDEX IF EXISTS idx_test_results_score;
DROP INDEX IF EXISTS idx_test_results_type_score;
DROP INDEX IF EXISTS idx_test_results_execution_id;

-- Drop indexes for test_categories
DROP INDEX IF EXISTS idx_test_categories_parent_order;
DROP INDEX IF EXISTS idx_test_categories_status;
DROP INDEX IF EXISTS idx_test_categories_path;
DROP INDEX IF EXISTS idx_test_categories_parent;
DROP INDEX IF EXISTS idx_test_categories_name;

-- Drop tables (results first due to foreign key)
DROP TABLE IF EXISTS test_results;
DROP TABLE IF EXISTS test_categories;

-- Verify rollback
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM sqlite_master WHERE name IN ('test_results', 'test_categories'))
        THEN 'SUCCESS: Tables removed successfully'
        ELSE 'ERROR: Tables still exist'
    END as rollback_status;

-- Verify test_executions table doesn't have category_id column
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM pragma_table_info('test_executions') WHERE name = 'category_id')
        THEN 'SUCCESS: category_id column removed from test_executions'
        ELSE 'ERROR: category_id column still exists in test_executions'
    END as column_removal_status;

-- Log completion
INSERT INTO migration_log (migration_name, action, timestamp) 
VALUES ('004_test_results_categories', 'rollback_complete', CURRENT_TIMESTAMP);