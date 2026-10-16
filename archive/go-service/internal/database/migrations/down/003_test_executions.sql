-- Rollback test_executions table
-- Comprehensive data preservation and validation

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
VALUES ('003_test_executions', 'rollback_start', CURRENT_TIMESTAMP);

-- Create backup table with all data
CREATE TABLE IF NOT EXISTS test_executions_backup AS 
SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
FROM test_executions;

-- Log data counts for validation
INSERT INTO migration_log (migration_name, action, details) 
VALUES ('003_test_executions', 'data_backup', 
        'Backed up ' || (SELECT COUNT(*) FROM test_executions) || ' test executions');

-- Export critical data to JSON for recovery (if needed)
-- This would be handled by the backup manager in Go code

-- Drop all indexes
DROP INDEX IF EXISTS idx_test_executions_type_status_date;
DROP INDEX IF EXISTS idx_test_executions_model_date;
DROP INDEX IF EXISTS idx_test_executions_score;
DROP INDEX IF EXISTS idx_test_executions_completed_at;
DROP INDEX IF EXISTS idx_test_executions_session_id;
DROP INDEX IF EXISTS idx_test_executions_correlation_id;
DROP INDEX IF EXISTS idx_test_executions_status_created;
DROP INDEX IF EXISTS idx_test_executions_model_type;

-- Drop the table
DROP TABLE IF EXISTS test_executions;

-- Verify rollback
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions')
        THEN 'SUCCESS: test_executions table removed'
        ELSE 'ERROR: test_executions table still exists'
    END as rollback_status;

-- Verify backup exists
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions_backup')
        THEN 'SUCCESS: Backup table created with ' || (SELECT COUNT(*) FROM test_executions_backup) || ' records'
        ELSE 'ERROR: Backup table not found'
    END as backup_status;

-- Log completion
INSERT INTO migration_log (migration_name, action, timestamp) 
VALUES ('003_test_executions', 'rollback_complete', CURRENT_TIMESTAMP);