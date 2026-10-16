-- Rollback seed data for test categories
-- This script removes seeded data while preserving any user-created categories

-- Log rollback start (using existing schema_migrations table for now)
-- Create migration_log table if it doesn't exist for detailed tracking
CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

INSERT INTO migration_log (migration_name, action, timestamp) 
VALUES ('005_seed_test_categories', 'rollback_start', CURRENT_TIMESTAMP);

-- Remove subcategories first (due to foreign key constraints)
DELETE FROM test_categories 
WHERE id IN (101, 102, 103, 201, 202) 
AND created_at <= (SELECT created_at FROM test_categories WHERE id = 1);

-- Remove main categories (only if they match original seed data)
DELETE FROM test_categories 
WHERE id IN (1, 2, 3, 4)
AND name IN ('coding', 'reasoning', 'creative', 'tool-calling')
AND version = '1.0';

-- Verify rollback
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'SUCCESS: All seed categories removed'
        ELSE 'WARNING: ' || COUNT(*) || ' seed categories remain'
    END as rollback_status
FROM test_categories 
WHERE id IN (1, 2, 3, 4, 101, 102, 103, 201, 202);

-- Log completion
INSERT INTO migration_log (migration_name, action, timestamp) 
VALUES ('005_seed_test_categories', 'rollback_complete', CURRENT_TIMESTAMP);