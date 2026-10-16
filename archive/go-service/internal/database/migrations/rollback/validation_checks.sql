-- Validation checks for database rollback operations
-- Contains SQL queries to verify rollback completion and data integrity

-- Create migration_log table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Table existence validation checks
-- These verify that tables were properly removed during rollback

CREATE VIEW IF NOT EXISTS validate_test_executions_rollback AS
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions')
        THEN 'SUCCESS: test_executions table removed'
        ELSE 'ERROR: test_executions table still exists'
    END as rollback_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions_backup')
        THEN 'SUCCESS: test_executions_backup table exists'
        ELSE 'WARNING: test_executions_backup table not found'
    END as backup_status;

CREATE VIEW IF NOT EXISTS validate_test_results_rollback AS
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_results')
        THEN 'SUCCESS: test_results table removed'
        ELSE 'ERROR: test_results table still exists'
    END as rollback_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_results_backup')
        THEN 'SUCCESS: test_results_backup table exists'
        ELSE 'WARNING: test_results_backup table not found'
    END as backup_status;

CREATE VIEW IF NOT EXISTS validate_test_categories_rollback AS
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_categories')
        THEN 'SUCCESS: test_categories table removed'
        ELSE 'ERROR: test_categories table still exists'
    END as rollback_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_categories_backup')
        THEN 'SUCCESS: test_categories_backup table exists'
        ELSE 'WARNING: test_categories_backup table not found'
    END as backup_status;

-- Index validation checks
-- These verify that indexes were properly removed during rollback

CREATE VIEW IF NOT EXISTS validate_indexes_removed AS
SELECT 
    'test_executions indexes' as index_category,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM sqlite_master 
            WHERE type = 'index' 
            AND name IN (
                'idx_test_executions_type_status_date',
                'idx_test_executions_model_date',
                'idx_test_executions_score',
                'idx_test_executions_completed_at',
                'idx_test_executions_session_id',
                'idx_test_executions_correlation_id',
                'idx_test_executions_status_created',
                'idx_test_executions_model_type',
                'idx_test_executions_category_id'
            )
        )
        THEN 'SUCCESS: All test_executions indexes removed'
        ELSE 'ERROR: Some test_executions indexes still exist'
    END as validation_status

UNION ALL

SELECT 
    'test_results indexes' as index_category,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM sqlite_master 
            WHERE type = 'index' 
            AND name IN (
                'idx_test_results_execution_id',
                'idx_test_results_type_score',
                'idx_test_results_score',
                'idx_test_results_created_at',
                'idx_test_results_execution_type'
            )
        )
        THEN 'SUCCESS: All test_results indexes removed'
        ELSE 'ERROR: Some test_results indexes still exist'
    END as validation_status

UNION ALL

SELECT 
    'test_categories indexes' as index_category,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM sqlite_master 
            WHERE type = 'index' 
            AND name IN (
                'idx_test_categories_name',
                'idx_test_categories_parent',
                'idx_test_categories_path',
                'idx_test_categories_status',
                'idx_test_categories_parent_order'
            )
        )
        THEN 'SUCCESS: All test_categories indexes removed'
        ELSE 'ERROR: Some test_categories indexes still exist'
    END as validation_status;

-- Column removal validation (for test_executions.category_id)
CREATE VIEW IF NOT EXISTS validate_column_removal AS
SELECT 
    'category_id column removal' as validation_type,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM pragma_table_info('test_executions') 
            WHERE name = 'category_id'
        )
        THEN 'SUCCESS: category_id column removed from test_executions'
        ELSE 'ERROR: category_id column still exists in test_executions'
    END as validation_status;

-- Data preservation validation
-- These check that backup tables contain the expected data

CREATE VIEW IF NOT EXISTS validate_data_preservation AS
SELECT 
    'test_executions_backup' as backup_table,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions_backup')
        THEN 'Records: ' || (SELECT COUNT(*) FROM test_executions_backup) || ', Backup timestamp exists: ' ||
             CASE WHEN EXISTS (SELECT 1 FROM pragma_table_info('test_executions_backup') WHERE name = 'backup_timestamp')
                  THEN 'YES' ELSE 'NO' END
        ELSE 'ERROR: Backup table does not exist'
    END as preservation_status

UNION ALL

SELECT 
    'test_results_backup' as backup_table,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_results_backup')
        THEN 'Records: ' || (SELECT COUNT(*) FROM test_results_backup) || ', Backup timestamp exists: ' ||
             CASE WHEN EXISTS (SELECT 1 FROM pragma_table_info('test_results_backup') WHERE name = 'backup_timestamp')
                  THEN 'YES' ELSE 'NO' END
        ELSE 'ERROR: Backup table does not exist'
    END as preservation_status

UNION ALL

SELECT 
    'test_categories_backup' as backup_table,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_categories_backup')
        THEN 'Records: ' || (SELECT COUNT(*) FROM test_categories_backup) || ', Backup timestamp exists: ' ||
             CASE WHEN EXISTS (SELECT 1 FROM pragma_table_info('test_categories_backup') WHERE name = 'backup_timestamp')
                  THEN 'YES' ELSE 'NO' END
        ELSE 'ERROR: Backup table does not exist'
    END as preservation_status;

-- Seed data rollback validation
-- Specific validation for seed data removal (migration 005)

CREATE VIEW IF NOT EXISTS validate_seed_data_rollback AS
SELECT 
    'seed_categories_removal' as validation_type,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM test_categories 
            WHERE id IN (1, 2, 3, 4, 101, 102, 103, 201, 202)
            AND name IN ('coding', 'reasoning', 'creative', 'tool-calling')
        )
        THEN 'SUCCESS: All seed categories removed'
        ELSE 'WARNING: Some seed categories still exist - may be user-modified'
    END as validation_status;

-- Migration log validation
-- Check that rollback operations were properly logged

CREATE VIEW IF NOT EXISTS validate_migration_log AS
SELECT 
    migration_name,
    action,
    timestamp,
    details,
    CASE 
        WHEN action = 'rollback_complete' THEN 'SUCCESS: Rollback completed'
        WHEN action = 'rollback_start' THEN 'INFO: Rollback initiated'
        WHEN action = 'data_backup' THEN 'SUCCESS: Data backed up'
        ELSE 'INFO: ' || action
    END as log_status
FROM migration_log 
WHERE migration_name IN ('003_test_executions', '004_test_results_categories', '005_seed_test_categories')
ORDER BY timestamp DESC;

-- Comprehensive rollback validation report
-- Combines all validation checks into a single report

CREATE VIEW IF NOT EXISTS comprehensive_rollback_validation AS
SELECT 'Table Removal' as check_category, rollback_status as status FROM validate_test_executions_rollback
UNION ALL
SELECT 'Table Removal', rollback_status FROM validate_test_results_rollback
UNION ALL  
SELECT 'Table Removal', rollback_status FROM validate_test_categories_rollback
UNION ALL
SELECT 'Backup Verification', backup_status FROM validate_test_executions_rollback
UNION ALL
SELECT 'Backup Verification', backup_status FROM validate_test_results_rollback
UNION ALL
SELECT 'Backup Verification', backup_status FROM validate_test_categories_rollback
UNION ALL
SELECT 'Index Removal', validation_status FROM validate_indexes_removed
UNION ALL
SELECT 'Column Removal', validation_status FROM validate_column_removal
UNION ALL
SELECT 'Data Preservation', preservation_status FROM validate_data_preservation
UNION ALL
SELECT 'Seed Data Cleanup', validation_status FROM validate_seed_data_rollback;