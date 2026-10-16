-- Recovery scripts for database rollback operations
-- Contains procedures to restore data from backup tables if needed

-- Create migration_log table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Recovery procedure for test_executions table
-- This script restores the test_executions table from backup
CREATE VIEW IF NOT EXISTS recover_test_executions_procedure AS
SELECT 
    'BEGIN TRANSACTION; ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''recovery'', ''test_executions_recovery_start'', CURRENT_TIMESTAMP); ' ||
    'CREATE TABLE test_executions AS SELECT ' ||
    'id, test_type, test_category, test_name, model_name, model_provider, model_version, ' ||
    'prompt, parameters, expected_output, status, started_at, completed_at, execution_time_ms, ' ||
    'raw_response, score, score_breakdown, correlation_id, user_id, session_id, environment, ' ||
    'error_message, retry_count, created_at, updated_at ' ||
    'FROM test_executions_backup; ' ||
    'CREATE INDEX idx_test_executions_model_type ON test_executions(model_name, test_type); ' ||
    'CREATE INDEX idx_test_executions_status_created ON test_executions(status, created_at); ' ||
    'CREATE INDEX idx_test_executions_correlation_id ON test_executions(correlation_id); ' ||
    'CREATE INDEX idx_test_executions_session_id ON test_executions(session_id); ' ||
    'CREATE INDEX idx_test_executions_completed_at ON test_executions(completed_at); ' ||
    'CREATE INDEX idx_test_executions_score ON test_executions(score) WHERE score IS NOT NULL; ' ||
    'CREATE INDEX idx_test_executions_model_date ON test_executions(model_name, DATE(created_at)); ' ||
    'CREATE INDEX idx_test_executions_type_status_date ON test_executions(test_type, status, created_at); ' ||
    'INSERT INTO migration_log (migration_name, action, details) VALUES (''recovery'', ''test_executions_recovery_complete'', ' ||
    '''Recovered '' || (SELECT COUNT(*) FROM test_executions) || '' test executions''); ' ||
    'COMMIT;' as recovery_sql;

-- Recovery procedure for test_results table
CREATE VIEW IF NOT EXISTS recover_test_results_procedure AS
SELECT 
    'BEGIN TRANSACTION; ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''recovery'', ''test_results_recovery_start'', CURRENT_TIMESTAMP); ' ||
    'CREATE TABLE test_results AS SELECT ' ||
    'id, execution_id, result_type, result_name, score, max_score, weight, ' ||
    'expected_value, actual_value, normalized_value, evaluation_criteria, scoring_breakdown, comparison_metrics, ' ||
    'accuracy, relevance, completeness, creativity, evaluation_method, evaluator, confidence_level, ' ||
    'validation_errors, parsing_errors, created_at, updated_at ' ||
    'FROM test_results_backup; ' ||
    'CREATE INDEX idx_test_results_execution_id ON test_results(execution_id); ' ||
    'CREATE INDEX idx_test_results_type_score ON test_results(result_type, score); ' ||
    'CREATE INDEX idx_test_results_score ON test_results(score) WHERE score IS NOT NULL; ' ||
    'CREATE INDEX idx_test_results_created_at ON test_results(created_at); ' ||
    'CREATE INDEX idx_test_results_execution_type ON test_results(execution_id, result_type); ' ||
    'INSERT INTO migration_log (migration_name, action, details) VALUES (''recovery'', ''test_results_recovery_complete'', ' ||
    '''Recovered '' || (SELECT COUNT(*) FROM test_results) || '' test results''); ' ||
    'COMMIT;' as recovery_sql;

-- Recovery procedure for test_categories table
CREATE VIEW IF NOT EXISTS recover_test_categories_procedure AS
SELECT 
    'BEGIN TRANSACTION; ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''recovery'', ''test_categories_recovery_start'', CURRENT_TIMESTAMP); ' ||
    'CREATE TABLE test_categories AS SELECT ' ||
    'id, name, display_name, description, parent_category_id, category_path, sort_order, ' ||
    'template_prompt, default_parameters, scoring_criteria, allowed_models, ' ||
    'min_execution_time, max_execution_time, timeout_seconds, icon, color, tags, ' ||
    'status, version, created_at, updated_at ' ||
    'FROM test_categories_backup; ' ||
    'CREATE INDEX idx_test_categories_name ON test_categories(name); ' ||
    'CREATE INDEX idx_test_categories_parent ON test_categories(parent_category_id); ' ||
    'CREATE INDEX idx_test_categories_path ON test_categories(category_path); ' ||
    'CREATE INDEX idx_test_categories_status ON test_categories(status); ' ||
    'CREATE INDEX idx_test_categories_parent_order ON test_categories(parent_category_id, sort_order); ' ||
    'INSERT INTO migration_log (migration_name, action, details) VALUES (''recovery'', ''test_categories_recovery_complete'', ' ||
    '''Recovered '' || (SELECT COUNT(*) FROM test_categories) || '' test categories''); ' ||
    'COMMIT;' as recovery_sql;

-- Recovery procedure to restore category_id column in test_executions
-- This adds back the category_id column that was removed during rollback
CREATE VIEW IF NOT EXISTS recover_test_executions_category_link AS
SELECT 
    'BEGIN TRANSACTION; ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''recovery'', ''category_link_recovery_start'', CURRENT_TIMESTAMP); ' ||
    'ALTER TABLE test_executions ADD COLUMN category_id INTEGER REFERENCES test_categories(id) ON DELETE SET NULL; ' ||
    'CREATE INDEX idx_test_executions_category_id ON test_executions(category_id); ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''recovery'', ''category_link_recovery_complete'', CURRENT_TIMESTAMP); ' ||
    'COMMIT;' as recovery_sql;

-- Comprehensive recovery procedure
-- Restores all test tables and their relationships from backup
CREATE VIEW IF NOT EXISTS comprehensive_recovery_procedure AS
SELECT 
    'BEGIN TRANSACTION; ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''recovery'', ''comprehensive_recovery_start'', CURRENT_TIMESTAMP); ' ||
    
    -- Recover test_categories first (no dependencies)
    'CREATE TABLE test_categories AS SELECT ' ||
    'id, name, display_name, description, parent_category_id, category_path, sort_order, ' ||
    'template_prompt, default_parameters, scoring_criteria, allowed_models, ' ||
    'min_execution_time, max_execution_time, timeout_seconds, icon, color, tags, ' ||
    'status, version, created_at, updated_at ' ||
    'FROM test_categories_backup; ' ||
    
    -- Recover test_executions second
    'CREATE TABLE test_executions AS SELECT ' ||
    'id, test_type, test_category, test_name, model_name, model_provider, model_version, ' ||
    'prompt, parameters, expected_output, status, started_at, completed_at, execution_time_ms, ' ||
    'raw_response, score, score_breakdown, correlation_id, user_id, session_id, environment, ' ||
    'error_message, retry_count, created_at, updated_at ' ||
    'FROM test_executions_backup; ' ||
    
    -- Add category_id column to test_executions
    'ALTER TABLE test_executions ADD COLUMN category_id INTEGER REFERENCES test_categories(id) ON DELETE SET NULL; ' ||
    
    -- Recover test_results last (depends on test_executions)
    'CREATE TABLE test_results AS SELECT ' ||
    'id, execution_id, result_type, result_name, score, max_score, weight, ' ||
    'expected_value, actual_value, normalized_value, evaluation_criteria, scoring_breakdown, comparison_metrics, ' ||
    'accuracy, relevance, completeness, creativity, evaluation_method, evaluator, confidence_level, ' ||
    'validation_errors, parsing_errors, created_at, updated_at ' ||
    'FROM test_results_backup; ' ||
    
    -- Recreate all indexes
    'CREATE INDEX idx_test_categories_name ON test_categories(name); ' ||
    'CREATE INDEX idx_test_categories_parent ON test_categories(parent_category_id); ' ||
    'CREATE INDEX idx_test_categories_path ON test_categories(category_path); ' ||
    'CREATE INDEX idx_test_categories_status ON test_categories(status); ' ||
    'CREATE INDEX idx_test_categories_parent_order ON test_categories(parent_category_id, sort_order); ' ||
    
    'CREATE INDEX idx_test_executions_model_type ON test_executions(model_name, test_type); ' ||
    'CREATE INDEX idx_test_executions_status_created ON test_executions(status, created_at); ' ||
    'CREATE INDEX idx_test_executions_correlation_id ON test_executions(correlation_id); ' ||
    'CREATE INDEX idx_test_executions_session_id ON test_executions(session_id); ' ||
    'CREATE INDEX idx_test_executions_completed_at ON test_executions(completed_at); ' ||
    'CREATE INDEX idx_test_executions_score ON test_executions(score) WHERE score IS NOT NULL; ' ||
    'CREATE INDEX idx_test_executions_model_date ON test_executions(model_name, DATE(created_at)); ' ||
    'CREATE INDEX idx_test_executions_type_status_date ON test_executions(test_type, status, created_at); ' ||
    'CREATE INDEX idx_test_executions_category_id ON test_executions(category_id); ' ||
    
    'CREATE INDEX idx_test_results_execution_id ON test_results(execution_id); ' ||
    'CREATE INDEX idx_test_results_type_score ON test_results(result_type, score); ' ||
    'CREATE INDEX idx_test_results_score ON test_results(score) WHERE score IS NOT NULL; ' ||
    'CREATE INDEX idx_test_results_created_at ON test_results(created_at); ' ||
    'CREATE INDEX idx_test_results_execution_type ON test_results(execution_id, result_type); ' ||
    
    'INSERT INTO migration_log (migration_name, action, details) VALUES (''recovery'', ''comprehensive_recovery_complete'', ' ||
    '''Recovered all test tables with '' || (SELECT COUNT(*) FROM test_executions) || '' executions, '' || ' ||
    '(SELECT COUNT(*) FROM test_results) || '' results, '' || ' ||
    '(SELECT COUNT(*) FROM test_categories) || '' categories''); ' ||
    'COMMIT;' as recovery_sql;

-- Partial recovery procedures
-- These allow selective recovery of specific data

-- Recover only seed data for test categories
CREATE VIEW IF NOT EXISTS recover_seed_categories_procedure AS
SELECT 
    'BEGIN TRANSACTION; ' ||
    'INSERT INTO migration_log (migration_name, action, timestamp) VALUES (''recovery'', ''seed_categories_recovery_start'', CURRENT_TIMESTAMP); ' ||
    'INSERT INTO test_categories SELECT * FROM test_categories_backup ' ||
    'WHERE id IN (1, 2, 3, 4, 101, 102, 103, 201, 202) ' ||
    'AND name IN (''coding'', ''reasoning'', ''creative'', ''tool-calling'', ''algorithms'', ''data-structures'', ''debugging'', ''logical-reasoning'', ''mathematical-reasoning''); ' ||
    'INSERT INTO migration_log (migration_name, action, details) VALUES (''recovery'', ''seed_categories_recovery_complete'', ' ||
    '''Recovered '' || (SELECT COUNT(*) FROM test_categories WHERE id IN (1,2,3,4,101,102,103,201,202)) || '' seed categories''); ' ||
    'COMMIT;' as recovery_sql;

-- Recovery validation
-- Check recovery success and data integrity
CREATE VIEW IF NOT EXISTS validate_recovery_success AS
SELECT 
    'test_executions' as table_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions')
        THEN 'SUCCESS: Table recovered with ' || (SELECT COUNT(*) FROM test_executions) || ' records'
        ELSE 'ERROR: Table not recovered'
    END as recovery_status

UNION ALL

SELECT 
    'test_results' as table_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_results')
        THEN 'SUCCESS: Table recovered with ' || (SELECT COUNT(*) FROM test_results) || ' records'
        ELSE 'ERROR: Table not recovered'
    END as recovery_status

UNION ALL

SELECT 
    'test_categories' as table_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_categories')
        THEN 'SUCCESS: Table recovered with ' || (SELECT COUNT(*) FROM test_categories) || ' records'
        ELSE 'ERROR: Table not recovered'
    END as recovery_status;

-- Emergency data export procedures
-- Export critical data to text format for manual recovery

CREATE VIEW IF NOT EXISTS export_backup_data_info AS
SELECT 
    'backup_summary' as export_type,
    'test_executions_backup: ' || (SELECT COUNT(*) FROM test_executions_backup) || ' records, ' ||
    'test_results_backup: ' || (SELECT COUNT(*) FROM test_results_backup) || ' records, ' ||
    'test_categories_backup: ' || (SELECT COUNT(*) FROM test_categories_backup) || ' records' as export_info

UNION ALL

SELECT 
    'recovery_instructions' as export_type,
    'To recover: 1) Run comprehensive_recovery_procedure, 2) Validate with validate_recovery_success, 3) Test application functionality' as export_info;