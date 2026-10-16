# Database Rollback Troubleshooting Guide

## Quick Diagnostic Commands

```bash
# Check current status
make test-database-rollback
cd go-service && go run cmd/migrate/main.go -status

# View recent logs
make logs level=ERROR

# Check database integrity
cd go-service && sqlite3 evaluation.db "PRAGMA integrity_check;"

# Test service health
curl -f http://localhost:8080/health
```

## Common Issues and Solutions

### 1. Rollback Script Errors

#### Issue: "Rollback script not found"
```
Error: Failed to load rollback script: open migrations/down/003_test_executions.sql: no such file or directory
```

**Diagnosis:**
```bash
cd go-service
ls -la internal/database/migrations/down/
```

**Solutions:**

**A. Missing File**
```bash
# Check if file exists
find . -name "*test_executions*" -type f

# If found in different location, copy to correct path
cp path/to/003_test_executions.sql internal/database/migrations/down/
```

**B. Wrong Path**
```bash
# Verify current working directory
pwd

# Check migration path configuration
grep -r "migrationsPath" internal/database/migration_tools/
```

**C. Permission Issues**
```bash
# Fix permissions
chmod 644 internal/database/migrations/down/*.sql
```

#### Issue: "SQL syntax error in rollback script"
```
Error: near line 15: syntax error
```

**Diagnosis:**
```bash
cd go-service
sqlite3 evaluation.db < internal/database/migrations/down/003_test_executions.sql
```

**Solutions:**

**A. Validate SQL Syntax**
```bash
# Test SQL syntax
sqlite3 :memory: < internal/database/migrations/down/003_test_executions.sql
```

**B. Check for Common Issues**
```sql
-- Missing semicolons
-- Invalid table/column names
-- Incorrect SQLite syntax
-- Unmatched quotes or brackets
```

**C. Manual Validation**
```sql
-- Test each SQL block separately
sqlite3 evaluation.db << EOF
BEGIN TRANSACTION;
-- Paste SQL statements one by one to identify problematic line
ROLLBACK;
EOF
```

### 2. Foreign Key Constraint Errors

#### Issue: "FOREIGN KEY constraint failed"
```
Error: FOREIGN KEY constraint failed during rollback
```

**Diagnosis:**
```bash
cd go-service
sqlite3 evaluation.db << EOF
PRAGMA foreign_keys;
PRAGMA foreign_key_check;
SELECT sql FROM sqlite_master WHERE type='table' AND name='test_executions';
EOF
```

**Solutions:**

**A. Disable Foreign Keys Temporarily**
```sql
-- Add to beginning of rollback script
PRAGMA foreign_keys = OFF;

-- Your rollback operations here

-- Re-enable at end
PRAGMA foreign_keys = ON;
```

**B. Check Dependency Order**
```sql
-- Drop dependent tables first
DROP TABLE IF EXISTS test_results;  -- Child table
DROP TABLE IF EXISTS test_executions; -- Parent table
```

**C. Remove Foreign Key Constraints First**
```sql
-- For SQLite, recreate table without foreign key
CREATE TABLE test_executions_temp AS SELECT * FROM test_executions;
DROP TABLE test_executions;
CREATE TABLE test_executions AS SELECT * FROM test_executions_temp;
DROP TABLE test_executions_temp;
```

### 3. Backup Creation Failures

#### Issue: "Failed to create backup table"
```
Error: table test_executions_backup already exists
```

**Diagnosis:**
```bash
cd go-service
sqlite3 evaluation.db << EOF
.tables
SELECT sql FROM sqlite_master WHERE name LIKE '%backup%';
EOF
```

**Solutions:**

**A. Check Existing Backup**
```sql
-- Verify backup table contents
SELECT COUNT(*) FROM test_executions_backup;
SELECT * FROM test_executions_backup LIMIT 5;

-- If backup is valid, you can skip this step or rename it
ALTER TABLE test_executions_backup RENAME TO test_executions_backup_old;
```

**B. Force Backup Recreation**
```sql
-- Add to rollback script
DROP TABLE IF EXISTS test_executions_backup;
CREATE TABLE test_executions_backup AS 
SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
FROM test_executions;
```

**C. Backup to Different Name**
```sql
-- Use timestamped backup name
CREATE TABLE test_executions_backup_20250120 AS 
SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
FROM test_executions;
```

#### Issue: "Backup table is empty"
```
Error: Backup table created but contains no data
```

**Diagnosis:**
```sql
-- Check original table
SELECT COUNT(*) FROM test_executions;

-- Check backup table
SELECT COUNT(*) FROM test_executions_backup;

-- Check table structure
.schema test_executions
.schema test_executions_backup
```

**Solutions:**

**A. Verify Source Table**
```sql
-- If source table is actually empty, backup is correct
SELECT 'Source table is empty - backup is correct' as status
WHERE (SELECT COUNT(*) FROM test_executions) = 0;
```

**B. Manual Backup Creation**
```sql
-- Recreate backup manually
DROP TABLE IF EXISTS test_executions_backup;
INSERT INTO test_executions_backup 
SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
FROM test_executions;
```

### 4. Validation Failures

#### Issue: "Rollback validation failed"
```
Error: validation failed: table_removal check failed
```

**Diagnosis:**
```bash
cd go-service
go test ./tests/rollback/validation_test.go -v -run TestSpecificValidation
```

**Solutions:**

**A. Check Table Removal**
```sql
-- Verify table was actually dropped
SELECT name FROM sqlite_master WHERE type='table' AND name='test_executions';

-- If table still exists, drop it manually
DROP TABLE IF EXISTS test_executions;
```

**B. Check Validation Logic**
```bash
# Run validation step by step
cd go-service
go test ./tests/rollback/validation_test.go -v -run TestTableValidations
```

**C. Skip Problematic Validations**
```go
// Modify validation config to skip failing checks
config := migration_tools.ValidationConfig{
    IncludeTableChecks:  true,
    IncludeIndexChecks:  false, // Skip if problematic
    IncludeDataChecks:   true,
    IncludeBackupChecks: true,
    IncludeSchemaChecks: false, // Skip if problematic
    ContinueOnFailure:   true,   // Continue despite failures
}
```

### 5. Transaction and Locking Issues

#### Issue: "Database is locked"
```
Error: database is locked
```

**Diagnosis:**
```bash
# Check for running processes
ps aux | grep -E "(sqlite|evaluation\.db)"

# Check for SQLite locks
lsof go-service/evaluation.db
```

**Solutions:**

**A. Stop Competing Processes**
```bash
# Stop Go service
pkill -f "go run cmd/server/main.go"

# Stop test processes
pkill -f "go test"

# Wait for locks to release
sleep 5
```

**B. Check for Long-Running Transactions**
```sql
-- Check for active transactions (SQLite doesn't show this directly)
-- Close all connections and restart
```

**C. Force Unlock (Use with caution)**
```bash
# Only if no other processes are using the database
cd go-service
fuser -k evaluation.db  # Kill processes using the file
```

#### Issue: "Transaction rollback failed"
```
Error: failed to commit rollback transaction
```

**Diagnosis:**
```sql
-- Check database integrity
PRAGMA integrity_check;

-- Check journal file
-- ls -la evaluation.db*
```

**Solutions:**

**A. Manual Transaction Management**
```sql
-- Run rollback script manually with explicit transaction control
BEGIN IMMEDIATE TRANSACTION;
-- Your rollback operations
COMMIT;
```

**B. Check Disk Space**
```bash
df -h .  # Check available disk space
du -sh evaluation.db*  # Check database size
```

### 6. Performance Issues

#### Issue: "Rollback timeout"
```
Error: rollback operation timed out
```

**Diagnosis:**
```bash
# Check database size and complexity
cd go-service
sqlite3 evaluation.db << EOF
SELECT name, COUNT(*) as row_count 
FROM sqlite_master m
JOIN (
    SELECT 'test_executions' as name, COUNT(*) as count FROM test_executions
    UNION ALL
    SELECT 'test_results' as name, COUNT(*) as count FROM test_results
    UNION ALL  
    SELECT 'test_categories' as name, COUNT(*) as count FROM test_categories
) t ON m.name = t.name
WHERE m.type = 'table';
EOF
```

**Solutions:**

**A. Increase Timeout**
```go
// In Go code, increase context timeout
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
defer cancel()
```

**B. Batch Processing**
```sql
-- For large tables, process in batches
CREATE TABLE test_executions_backup AS 
SELECT * FROM test_executions LIMIT 10000;

INSERT INTO test_executions_backup 
SELECT * FROM test_executions 
WHERE id > (SELECT MAX(id) FROM test_executions_backup)
LIMIT 10000;
-- Repeat until all data is backed up
```

**C. Optimize Database**
```sql
-- Run before rollback for better performance
ANALYZE;
VACUUM;
REINDEX;
```

### 7. Index and Schema Issues

#### Issue: "Index creation failed during rollback"
```
Error: index idx_test_executions_status already exists
```

**Diagnosis:**
```sql
-- Check existing indexes
SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE '%test_executions%';
```

**Solutions:**

**A. Drop Existing Indexes**
```sql
-- Add to rollback script
DROP INDEX IF EXISTS idx_test_executions_status;
DROP INDEX IF EXISTS idx_test_executions_model_type;
-- etc.
```

**B. Check Index Dependencies**
```sql
-- Verify indexes are properly removed with table
SELECT COUNT(*) FROM sqlite_master 
WHERE type='index' AND sql LIKE '%test_executions%';
```

#### Issue: "Schema mismatch after rollback"
```
Error: table test_executions has wrong schema
```

**Diagnosis:**
```sql
-- Compare expected vs actual schema
.schema test_executions

-- Check for orphaned columns or constraints
PRAGMA table_info(test_executions);
```

**Solutions:**

**A. Recreate Table with Correct Schema**
```sql
-- Drop and recreate with exact schema needed
DROP TABLE IF EXISTS test_executions;
CREATE TABLE test_executions (
    -- Copy exact schema from migration file
);
```

**B. Use Migration Files as Reference**
```bash
# Check original migration for correct schema
cat internal/database/migrations/003_test_executions.sql
```

## Advanced Debugging

### Enable Debug Logging

```bash
# Set debug logging for detailed output
export LOG_LEVEL=debug
cd go-service
go test ./tests/rollback/... -v
```

### Database Analysis Tools

```sql
-- Check database statistics
SELECT 
    name,
    (SELECT COUNT(*) FROM pragma_table_info(name)) as column_count,
    CASE WHEN type = 'table' THEN
        (SELECT sql FROM sqlite_master s2 WHERE s2.name = s1.name LIMIT 1)
    END as definition
FROM sqlite_master s1
WHERE type IN ('table', 'index') AND name LIKE '%test_%'
ORDER BY type, name;

-- Check foreign key relationships
SELECT 
    m.name as table_name,
    p.id as fk_id,
    p.seq as seq,
    p."table" as referenced_table,
    p."from" as from_column,
    p."to" as to_column
FROM sqlite_master m
JOIN pragma_foreign_key_list(m.name) p
WHERE m.type = 'table' AND m.name LIKE '%test_%'
ORDER BY m.name, p.id, p.seq;
```

### Manual Rollback Execution

For complex debugging, execute rollback steps manually:

```sql
-- Step 1: Create backup
CREATE TABLE test_executions_backup AS 
SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
FROM test_executions;

-- Step 2: Verify backup
SELECT COUNT(*) FROM test_executions_backup;

-- Step 3: Drop indexes
DROP INDEX IF EXISTS idx_test_executions_status_created;
-- (list all indexes)

-- Step 4: Drop table
DROP TABLE IF EXISTS test_executions;

-- Step 5: Verify removal
SELECT name FROM sqlite_master WHERE name = 'test_executions';

-- Step 6: Log operation
INSERT INTO migration_log (migration_name, action, timestamp) 
VALUES ('003_test_executions', 'manual_rollback_complete', CURRENT_TIMESTAMP);
```

## Prevention Strategies

### Pre-Rollback Checklist

```bash
# 1. Check database integrity
cd go-service && sqlite3 evaluation.db "PRAGMA integrity_check;"

# 2. Verify no active connections
lsof evaluation.db || echo "No active connections"

# 3. Check disk space
df -h . && du -sh evaluation.db

# 4. Create manual backup
cp evaluation.db evaluation.db.pre-rollback.backup

# 5. Test rollback script syntax
sqlite3 :memory: < internal/database/migrations/down/003_test_executions.sql
```

### Development Best Practices

1. **Always Test Rollbacks in Development**
```bash
# Test with empty database
make setup-test-db
make test-database-rollback

# Test with populated database  
make setup-test-db
# Insert test data
make test-database-rollback
```

2. **Validate SQL Scripts**
```bash
# Use sqlfluff or similar tools
pip install sqlfluff
sqlfluff lint internal/database/migrations/down/*.sql
```

3. **Use Transactions Properly**
```sql
-- Always wrap rollback operations in transactions
BEGIN TRANSACTION;
-- Rollback operations here
-- Add validation checks
SELECT CASE WHEN ... THEN 'SUCCESS' ELSE 'FAILURE' END;
COMMIT; -- Only if validation passes
```

## When to Escalate

Escalate to senior developers when:

1. **Data Loss Risk**: Backup tables are missing or corrupted
2. **Schema Corruption**: Database schema is inconsistent 
3. **Performance Issues**: Rollback takes longer than acceptable downtime
4. **Repeated Failures**: Same rollback fails multiple times
5. **Production Impact**: Service cannot restart after rollback

### Escalation Information to Provide

```bash
# Collect this information before escalating:

# 1. Error logs
make logs level=ERROR > rollback_error_logs.txt

# 2. Database state
cd go-service
sqlite3 evaluation.db << EOF > database_state.txt
.tables
.schema
SELECT * FROM migration_log ORDER BY timestamp DESC LIMIT 20;
PRAGMA integrity_check;
EOF

# 3. System information
uname -a > system_info.txt
df -h >> system_info.txt
ps aux | grep -E "(sqlite|go)" >> system_info.txt

# 4. Reproduction steps
echo "Steps to reproduce the issue:" > reproduction_steps.txt
# Document exact commands that led to the issue
```

## Testing and Validation

After resolving any rollback issue:

```bash
# 1. Run full test suite
make test-database-rollback

# 2. Validate specific scenarios
cd go-service
go test ./tests/rollback/rollback_test.go -v -run TestSpecificScenario

# 3. Performance test
go test ./tests/rollback/data_preservation_test.go -v -run TestBackupWithLargeDataset

# 4. Integration test
make test-integration-go
```

---

*This troubleshooting guide covers the most common rollback issues. For complex scenarios not covered here, refer to the emergency recovery procedures or escalate to the development team.*

*Last Updated: 2025-01-20*  
*Version: 1.0*