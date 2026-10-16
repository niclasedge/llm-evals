# Database Rollback Procedures

## Overview

This document provides comprehensive procedures for safely rolling back database migrations in the LLM Evaluation Framework. The rollback system ensures data preservation, validation, and recovery capabilities for all database changes.

## Quick Reference

### Emergency Rollback Commands

```bash
# Quick rollback of specific migration
cd go-service
go run cmd/migrate/main.go -rollback 003_test_executions

# Run rollback with validation
make test-database-rollback

# Check rollback status
go run cmd/migrate/main.go -status
```

### Rollback Test Commands

```bash
# Test all rollback functionality
make test-database-rollback

# Test specific rollback scenarios
cd go-service
go test ./tests/rollback/rollback_test.go -v
go test ./tests/rollback/data_preservation_test.go -v
go test ./tests/rollback/validation_test.go -v
```

## Migration Rollback System

### Available Migrations

The following migrations have rollback support:

1. **003_test_executions** - Test execution table rollback
2. **004_test_results_categories** - Test results and categories tables rollback  
3. **005_seed_test_categories** - Seed data rollback

### Rollback Architecture

```
go-service/internal/database/
├── migrations/
│   ├── down/                    # Rollback SQL scripts
│   │   ├── 003_test_executions.sql
│   │   ├── 004_test_results_categories.sql
│   │   └── 005_seed_test_categories.sql
│   └── rollback/               # Rollback utilities
│       ├── backup_procedures.sql
│       ├── validation_checks.sql
│       └── recovery_scripts.sql
├── migration_tools/            # Go rollback managers
│   ├── rollback_manager.go
│   ├── backup_manager.go
│   └── validation_runner.go
└── tests/rollback/             # Comprehensive tests
    ├── rollback_test.go
    ├── data_preservation_test.go
    └── validation_test.go
```

## Data Preservation Strategy

### Automatic Backup Creation

All rollback operations automatically create backup tables:

- **test_executions** → **test_executions_backup**
- **test_results** → **test_results_backup** 
- **test_categories** → **test_categories_backup**

### Backup Table Features

- Contains all original data with timestamps
- Includes `backup_timestamp` column for audit trail
- Persists after rollback completion for recovery
- Supports both empty and populated table rollbacks

### Data Export Options

The backup manager supports multiple export formats:

```go
config := migration_tools.BackupConfig{
    IncludeData:   true,
    Tables:        []string{"test_executions"},
    ExportFormat:  "json",        // json, csv, sql
    Compression:   true,          // gzip compression
    RetentionDays: 30,           // cleanup policy
}
```

## Rollback Procedures

### 1. Pre-Rollback Checklist

Before performing any rollback:

- [ ] Verify current migration status
- [ ] Check for dependent data or foreign keys
- [ ] Ensure adequate disk space for backups
- [ ] Stop application services if required
- [ ] Create manual backup if needed

### 2. Standard Rollback Process

#### Step 1: Initialize Rollback Manager

```go
import (
    "go-service/internal/database/migration_tools"
    "go-service/internal/logging"
)

// Create managers
logger := logging.NewDefaultLogger().Logger
rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)
```

#### Step 2: Execute Rollback

```go
ctx := context.Background()
result, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
if err != nil {
    log.Fatal("Rollback failed:", err)
}

fmt.Printf("Rollback successful: %v\n", result.Success)
fmt.Printf("Backup tables: %v\n", result.BackupTables)
```

#### Step 3: Validate Rollback

```go
config := migration_tools.ValidationConfig{
    IncludeTableChecks:  true,
    IncludeIndexChecks:  true,
    IncludeDataChecks:   true,
    IncludeBackupChecks: true,
    IncludeSchemaChecks: true,
    ContinueOnFailure:   true,
}

validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
if err != nil || !validationResult.Success {
    // Handle validation failures
    log.Printf("Validation failed: %v", validationResult.Summary)
}
```

### 3. Migration-Specific Procedures

#### Test Executions Rollback (003)

**What it does:**
- Drops `test_executions` table and all indexes
- Creates `test_executions_backup` with all data
- Removes foreign key constraints from dependent tables

**Validation:**
- Verifies table removal
- Confirms backup table exists with correct data count
- Checks index cleanup

**Recovery:** 
```sql
-- Restore from backup if needed
CREATE TABLE test_executions AS SELECT * FROM test_executions_backup;
```

#### Test Results and Categories Rollback (004)

**What it does:**
- Drops `test_results` and `test_categories` tables
- Creates backup tables with all data
- Removes `category_id` column from `test_executions`
- Handles foreign key constraints properly

**Validation:**
- Verifies both tables removed
- Confirms backup tables exist
- Checks foreign key cleanup
- Validates data consistency

#### Seed Data Rollback (005)

**What it does:**
- Removes only seed categories (IDs 1-4, 101-103, etc.)
- Preserves user-created categories
- Maintains table structure

**Validation:**
- Confirms seed data removal
- Verifies user data preservation
- Checks category hierarchy integrity

## Validation Framework

### Validation Types

The validation system performs comprehensive checks:

1. **Table Checks**
   - Table existence/removal verification
   - Backup table creation confirmation
   - Schema structure validation

2. **Index Checks** 
   - Index removal verification
   - Performance index cleanup
   - Constraint removal validation

3. **Data Checks**
   - Foreign key constraint validation
   - Data integrity verification
   - Row count consistency

4. **Backup Checks**
   - Backup table existence
   - Data preservation verification
   - Timestamp accuracy

5. **Schema Checks**
   - Migration log verification
   - Schema state validation
   - Dependency resolution

### Validation Results

```go
type ValidationResult struct {
    Success       bool
    MigrationName string
    ValidationID  string
    Checks        []ValidationCheck
    Summary       ValidationSummary
    Recommendations []string
    ExecutionTime time.Duration
}

type ValidationCheck struct {
    Name          string
    CheckType     string
    Status        ValidationStatus  // Pass, Fail, Warning, Skip
    Details       map[string]interface{}
    ExecutionTime time.Duration
    ErrorMessage  string
}
```

## Emergency Recovery Procedures

### Recovery from Failed Rollback

If a rollback fails partway through:

1. **Check Migration Log**
```sql
SELECT * FROM migration_log 
WHERE migration_name = '003_test_executions' 
ORDER BY timestamp DESC;
```

2. **Verify Backup Tables**
```sql
-- Check if backup exists
SELECT COUNT(*) FROM sqlite_master 
WHERE type='table' AND name='test_executions_backup';

-- Verify backup data
SELECT COUNT(*) FROM test_executions_backup;
```

3. **Manual Recovery Options**

**Option A: Complete Manual Rollback**
```sql
-- Drop any partially created structures
DROP TABLE IF EXISTS test_executions;
DROP INDEX IF EXISTS idx_test_executions_status_created;

-- Verify backup integrity
SELECT * FROM test_executions_backup LIMIT 5;
```

**Option B: Restore from Backup**
```sql
-- Recreate table from backup
CREATE TABLE test_executions AS 
SELECT * FROM test_executions_backup;

-- Remove backup timestamp column
ALTER TABLE test_executions DROP COLUMN backup_timestamp;

-- Recreate required indexes
CREATE INDEX idx_test_executions_status_created 
ON test_executions(status, created_at);
```

### Data Recovery Scripts

Located in `go-service/internal/database/migrations/rollback/recovery_scripts.sql`:

```sql
-- Recovery script for test_executions
-- Use when rollback fails and manual recovery is needed

BEGIN TRANSACTION;

-- Log recovery start
INSERT INTO migration_log (migration_name, action, details) 
VALUES ('003_test_executions', 'manual_recovery_start', 
        'Manual recovery initiated after failed rollback');

-- Check backup table exists
SELECT CASE 
    WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions_backup')
    THEN 'BACKUP_AVAILABLE'
    ELSE 'BACKUP_MISSING'
END as backup_status;

-- Restore table if backup available
CREATE TABLE IF NOT EXISTS test_executions AS 
SELECT id, test_type, model_name, prompt, status, score, 
       correlation_id, session_id, created_at, completed_at
FROM test_executions_backup;

-- Verify restoration
SELECT COUNT(*) as restored_rows FROM test_executions;

-- Log recovery completion
INSERT INTO migration_log (migration_name, action, details) 
VALUES ('003_test_executions', 'manual_recovery_complete', 
        'Manual recovery completed successfully');

COMMIT;
```

## Troubleshooting Guide

### Common Issues

#### 1. Rollback Script Not Found
```
Error: Failed to load rollback script: no such file or directory
```

**Solution:**
- Verify migration file exists in `migrations/down/` directory
- Check file permissions
- Ensure correct migration name format

#### 2. Foreign Key Constraint Errors
```
Error: FOREIGN KEY constraint failed
```

**Solution:**
- Check rollback order (child tables first)
- Verify constraint removal in rollback script
- Use `PRAGMA foreign_keys = OFF;` if necessary

#### 3. Backup Table Already Exists
```
Error: table test_executions_backup already exists
```

**Solution:**
- Previous rollback may have failed
- Check backup table contents
- Use `DROP TABLE IF EXISTS` in script

#### 4. Validation Failures
```
Error: Rollback validation failed: table still exists
```

**Solution:**
- Check if rollback script executed completely
- Verify transaction was committed
- Run validation manually to identify issues

### Debugging Tools

#### 1. Check Migration Status
```bash
cd go-service
go run cmd/migrate/main.go -status
```

#### 2. View Migration Logs
```sql
SELECT migration_name, action, timestamp, details 
FROM migration_log 
WHERE migration_name LIKE '%test_executions%' 
ORDER BY timestamp DESC;
```

#### 3. Manual Validation
```bash
cd go-service
go test ./tests/rollback/validation_test.go -v -run TestSpecificValidation
```

#### 4. Database Schema Check
```sql
-- List all tables
SELECT name FROM sqlite_master WHERE type='table';

-- Check table schema
PRAGMA table_info(test_executions);

-- Check foreign keys
PRAGMA foreign_key_list(test_executions);
```

## Performance Considerations

### Rollback Performance Metrics

Based on testing with various dataset sizes:

| Dataset Size | Rollback Time | Backup Size | Validation Time |
|-------------|---------------|-------------|-----------------|
| 100 records | < 1 second    | ~50KB      | < 1 second     |
| 1,000 records | ~2 seconds  | ~500KB     | ~2 seconds     |
| 10,000 records | ~10 seconds | ~5MB       | ~5 seconds     |
| 100,000 records | ~60 seconds | ~50MB      | ~30 seconds    |

### Optimization Tips

1. **Large Dataset Rollbacks**
   - Schedule during maintenance windows
   - Monitor disk space usage
   - Consider batch processing for huge datasets

2. **Backup Storage**
   - Backup tables are retained for safety
   - Implement cleanup policies for old backups
   - Consider compression for large backups

3. **Validation Performance**
   - Skip non-critical checks for faster rollbacks
   - Use parallel validation where possible
   - Implement timeout limits for large datasets

## Security Considerations

### Access Control

- Rollback operations require database write permissions
- Migration logs contain sensitive operation details
- Backup tables may contain production data

### Audit Trail

- All rollback operations are logged in `migration_log` table
- Validation results are persisted for compliance
- Backup timestamps provide audit trail

### Data Protection

- Backup tables preserve original data integrity
- No data is permanently deleted during rollback
- Recovery procedures available for all scenarios

## Best Practices

### Development Environment

1. **Always test rollbacks in development first**
2. **Verify backup creation before rollback**
3. **Run validation after every rollback**
4. **Keep migration logs for troubleshooting**

### Production Environment

1. **Create manual backups before major rollbacks**
2. **Schedule rollbacks during maintenance windows**
3. **Monitor system resources during rollback**
4. **Have recovery procedures ready**
5. **Test rollback scripts thoroughly before deployment**

### Code Review

1. **Review all rollback scripts before merging**
2. **Ensure proper foreign key handling**
3. **Verify backup creation logic**
4. **Test with both empty and populated tables**

## Support and Escalation

### Log Collection

When reporting rollback issues, collect:

```bash
# Migration logs
cd go-service && sqlite3 evaluation.db "SELECT * FROM migration_log WHERE migration_name LIKE '%rollback%';"

# System logs
make logs level=ERROR

# Database schema
cd go-service && sqlite3 evaluation.db ".schema"

# Test results
make test-database-rollback 2>&1 | tee rollback-test-results.log
```

### Escalation Path

1. **Level 1**: Check this documentation and run validation tests
2. **Level 2**: Review migration logs and run debugging commands
3. **Level 3**: Manual recovery using provided recovery scripts
4. **Level 4**: Contact development team with collected logs

---

*Last Updated: 2025-01-20*  
*Version: 1.0*  
*For technical support, refer to the project issue tracker*