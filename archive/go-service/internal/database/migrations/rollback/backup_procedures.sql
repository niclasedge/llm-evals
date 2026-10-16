-- Backup procedures for database rollback operations
-- Contains reusable backup procedures for different migration scenarios

-- Create migration_log table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Backup table creation template
-- Usage: Replace {TABLE_NAME} with actual table name
-- CREATE TABLE IF NOT EXISTS {TABLE_NAME}_backup AS 
-- SELECT *, CURRENT_TIMESTAMP as backup_timestamp FROM {TABLE_NAME};

-- Common backup procedures for all test-related tables

-- Backup test_executions table
-- This procedure creates a timestamped backup of the test_executions table
-- including all data and adding a backup_timestamp column
CREATE VIEW IF NOT EXISTS backup_test_executions_procedure AS
SELECT 
    'CREATE TABLE IF NOT EXISTS test_executions_backup AS ' ||
    'SELECT *, CURRENT_TIMESTAMP as backup_timestamp FROM test_executions;' as backup_sql;

-- Backup test_results table  
CREATE VIEW IF NOT EXISTS backup_test_results_procedure AS
SELECT 
    'CREATE TABLE IF NOT EXISTS test_results_backup AS ' ||
    'SELECT *, CURRENT_TIMESTAMP as backup_timestamp FROM test_results;' as backup_sql;

-- Backup test_categories table
CREATE VIEW IF NOT EXISTS backup_test_categories_procedure AS
SELECT 
    'CREATE TABLE IF NOT EXISTS test_categories_backup AS ' ||
    'SELECT *, CURRENT_TIMESTAMP as backup_timestamp FROM test_categories;' as backup_sql;

-- Comprehensive backup procedure for all test tables
-- This creates a backup of all test-related tables in a single operation
CREATE VIEW IF NOT EXISTS backup_all_test_tables_procedure AS
SELECT 
    'BEGIN TRANSACTION; ' ||
    'CREATE TABLE IF NOT EXISTS test_executions_backup AS SELECT *, CURRENT_TIMESTAMP as backup_timestamp FROM test_executions; ' ||
    'CREATE TABLE IF NOT EXISTS test_results_backup AS SELECT *, CURRENT_TIMESTAMP as backup_timestamp FROM test_results; ' ||
    'CREATE TABLE IF NOT EXISTS test_categories_backup AS SELECT *, CURRENT_TIMESTAMP as backup_timestamp FROM test_categories; ' ||
    'INSERT INTO migration_log (migration_name, action, details) VALUES (''bulk_backup'', ''backup_complete'', ' ||
    '''Backed up '' || (SELECT COUNT(*) FROM test_executions) || '' executions, '' || ' ||
    '(SELECT COUNT(*) FROM test_results) || '' results, '' || ' ||
    '(SELECT COUNT(*) FROM test_categories) || '' categories''); ' ||
    'COMMIT;' as backup_sql;

-- Backup verification queries
-- These check that backup tables exist and contain data

CREATE VIEW IF NOT EXISTS verify_test_executions_backup AS
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions_backup')
        THEN 'SUCCESS: test_executions_backup exists with ' || (SELECT COUNT(*) FROM test_executions_backup) || ' records'
        ELSE 'ERROR: test_executions_backup table not found'
    END as backup_status;

CREATE VIEW IF NOT EXISTS verify_test_results_backup AS
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_results_backup')
        THEN 'SUCCESS: test_results_backup exists with ' || (SELECT COUNT(*) FROM test_results_backup) || ' records'
        ELSE 'ERROR: test_results_backup table not found'
    END as backup_status;

CREATE VIEW IF NOT EXISTS verify_test_categories_backup AS
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_categories_backup')
        THEN 'SUCCESS: test_categories_backup exists with ' || (SELECT COUNT(*) FROM test_categories_backup) || ' records'
        ELSE 'ERROR: test_categories_backup table not found'
    END as backup_status;

-- Clean up old backup tables (optional, use with caution)
CREATE VIEW IF NOT EXISTS cleanup_backup_tables_procedure AS
SELECT 
    'DROP TABLE IF EXISTS test_executions_backup; ' ||
    'DROP TABLE IF EXISTS test_results_backup; ' ||
    'DROP TABLE IF EXISTS test_categories_backup; ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''cleanup'', ''backup_cleanup'', CURRENT_TIMESTAMP);' as cleanup_sql;

-- Log backup operation
CREATE VIEW IF NOT EXISTS log_backup_operation AS
SELECT 
    'INSERT INTO migration_log (migration_name, action, details, timestamp) VALUES ' ||
    '(''backup_operation'', ''backup_start'', ''Starting backup of test tables'', CURRENT_TIMESTAMP);' as log_sql;