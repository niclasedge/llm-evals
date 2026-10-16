# Emergency Database Recovery Procedures

## 🚨 Emergency Quick Reference

### Critical Commands

```bash
# Check system status
make test-database-rollback
cd go-service && go run cmd/migrate/main.go -status

# Emergency backup
cd go-service && cp evaluation.db evaluation.db.emergency.backup

# Force stop all services
pkill -f "go run"
pkill -f "python.*llm"
```

### Emergency Contacts

- **Development Team**: Create issue at project repository
- **Database Recovery**: Use procedures in this document
- **System Status**: Check migration logs and validation results

## Emergency Scenarios

### Scenario 1: Failed Migration Rollback

**Symptoms:**
- Rollback process terminated unexpectedly
- Tables partially removed or corrupted
- Data access errors in application

**Immediate Actions:**

1. **Stop All Services**
```bash
# Stop Go service
pkill -f "go run cmd/server/main.go"

# Stop Python services  
pkill -f "python.*evaluation"
```

2. **Assess Damage**
```bash
cd go-service
sqlite3 evaluation.db << EOF
.tables
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%backup%';
SELECT * FROM migration_log ORDER BY timestamp DESC LIMIT 10;
EOF
```

3. **Check for Backup Tables**
```bash
cd go-service
sqlite3 evaluation.db << EOF
-- Check if any backup tables exist
SELECT 
    name,
    sql
FROM sqlite_master 
WHERE type='table' AND name LIKE '%_backup'
ORDER BY name;

-- Count records in backup tables
.mode column
.headers on
SELECT 
    'test_executions_backup' as table_name,
    COUNT(*) as record_count
FROM test_executions_backup
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_executions_backup')
UNION ALL
SELECT 
    'test_results_backup' as table_name,
    COUNT(*) as record_count  
FROM test_results_backup
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_results_backup')
UNION ALL
SELECT 
    'test_categories_backup' as table_name,
    COUNT(*) as record_count
FROM test_categories_backup  
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE name = 'test_categories_backup');
EOF
```

4. **Execute Emergency Recovery**

Choose appropriate recovery path based on damage assessment:

**Path A: Backup Tables Available**
```sql
-- Connect to database
sqlite3 evaluation.db

BEGIN TRANSACTION;

-- Log emergency recovery start
INSERT INTO migration_log (migration_name, action, details) 
VALUES ('EMERGENCY', 'recovery_start', 'Emergency recovery from failed rollback initiated');

-- Restore test_executions if needed
DROP TABLE IF EXISTS test_executions;
CREATE TABLE test_executions AS 
SELECT id, test_type, model_name, prompt, status, score, 
       correlation_id, session_id, created_at, completed_at,
       metadata, error_message, timeout_seconds
FROM test_executions_backup;

-- Restore test_results if needed  
DROP TABLE IF EXISTS test_results;
CREATE TABLE test_results AS
SELECT id, execution_id, result_type, score, expected_value, 
       actual_value, metadata, created_at
FROM test_results_backup;

-- Restore test_categories if needed
DROP TABLE IF EXISTS test_categories;  
CREATE TABLE test_categories AS
SELECT id, name, display_name, description, parent_id, 
       sort_order, status, version, created_at, updated_at
FROM test_categories_backup;

-- Recreate indexes for test_executions
CREATE INDEX IF NOT EXISTS idx_test_executions_status_created 
ON test_executions(status, created_at);
CREATE INDEX IF NOT EXISTS idx_test_executions_model_type 
ON test_executions(model_name, test_type);
CREATE INDEX IF NOT EXISTS idx_test_executions_correlation_id 
ON test_executions(correlation_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_session_id 
ON test_executions(session_id);

-- Recreate indexes for test_results
CREATE INDEX IF NOT EXISTS idx_test_results_execution_id 
ON test_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_test_results_execution_type 
ON test_results(execution_id, result_type);
CREATE INDEX IF NOT EXISTS idx_test_results_score 
ON test_results(score);

-- Recreate indexes for test_categories
CREATE INDEX IF NOT EXISTS idx_test_categories_name 
ON test_categories(name);
CREATE INDEX IF NOT EXISTS idx_test_categories_parent 
ON test_categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_test_categories_status 
ON test_categories(status);

-- Add foreign key constraint back
ALTER TABLE test_executions ADD COLUMN category_id INTEGER 
REFERENCES test_categories(id);

-- Log recovery completion
INSERT INTO migration_log (migration_name, action, details) 
VALUES ('EMERGENCY', 'recovery_complete', 'Emergency recovery completed successfully');

COMMIT;

-- Verify recovery
.headers on
.mode column
SELECT 'test_executions' as table_name, COUNT(*) as records FROM test_executions
UNION ALL  
SELECT 'test_results' as table_name, COUNT(*) as records FROM test_results
UNION ALL
SELECT 'test_categories' as table_name, COUNT(*) as records FROM test_categories;
```

**Path B: No Backup Tables (Critical Data Loss)**
```sql
-- Connect to database
sqlite3 evaluation.db

BEGIN TRANSACTION;

-- Log critical recovery start
INSERT OR IGNORE INTO migration_log (migration_name, action, details) 
VALUES ('EMERGENCY', 'critical_recovery_start', 'Critical recovery - no backups available');

-- Recreate minimal schema
CREATE TABLE IF NOT EXISTS test_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    score REAL,
    correlation_id VARCHAR(50),
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata TEXT,
    error_message TEXT,
    timeout_seconds INTEGER DEFAULT 300
);

CREATE TABLE IF NOT EXISTS test_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES test_categories(id),
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    version VARCHAR(10) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    result_type VARCHAR(50) NOT NULL DEFAULT 'primary',
    score REAL,
    expected_value TEXT,
    actual_value TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recreate essential indexes
CREATE INDEX idx_test_executions_status_created ON test_executions(status, created_at);
CREATE INDEX idx_test_executions_model_type ON test_executions(model_name, test_type);
CREATE INDEX idx_test_results_execution_id ON test_results(execution_id);
CREATE INDEX idx_test_categories_name ON test_categories(name);

-- Add basic seed data
INSERT OR IGNORE INTO test_categories (id, name, display_name, description, version) VALUES
(1, 'coding', 'Coding Evaluation', 'Programming and code generation tasks', '1.0'),
(2, 'reasoning', 'Reasoning Evaluation', 'Logic and analytical thinking tasks', '1.0'),
(3, 'creative', 'Creative Evaluation', 'Creative writing and artistic tasks', '1.0'),
(4, 'tool-calling', 'Tool Calling Evaluation', 'Function calling and tool usage tasks', '1.0');

-- Log critical recovery completion
INSERT INTO migration_log (migration_name, action, details) 
VALUES ('EMERGENCY', 'critical_recovery_complete', 'Critical recovery completed - data may be lost');

COMMIT;

-- Show warning
SELECT 'WARNING: DATA LOSS OCCURRED - All test data has been reset' as message;
```

### Scenario 2: Database Corruption

**Symptoms:**
- Database file cannot be opened
- SQLite integrity check failures
- Persistent I/O errors

**Emergency Actions:**

1. **Immediate Backup**
```bash
cd go-service
cp evaluation.db evaluation.db.corrupted.backup
```

2. **Check Database Integrity**
```bash
cd go-service
sqlite3 evaluation.db "PRAGMA integrity_check;"
```

3. **Recovery Options**

**Option A: Minor Corruption - Repair**
```bash
cd go-service
sqlite3 evaluation.db << EOF
-- Attempt to repair
PRAGMA integrity_check;
REINDEX;
VACUUM;
PRAGMA integrity_check;
EOF
```

**Option B: Major Corruption - Recover Data**
```bash
cd go-service

# Create new database
mv evaluation.db evaluation.db.corrupted
sqlite3 evaluation_new.db < ../internal/database/migrations/001_initial_schema.sql

# Try to recover data from corrupted database
sqlite3 << EOF
ATTACH 'evaluation.db.corrupted' AS corrupted;
ATTACH 'evaluation_new.db' AS clean;

-- Attempt to copy recoverable data
BEGIN TRANSACTION;

INSERT OR IGNORE INTO clean.test_executions 
SELECT * FROM corrupted.test_executions 
WHERE id IS NOT NULL;

INSERT OR IGNORE INTO clean.test_categories 
SELECT * FROM corrupted.test_categories 
WHERE id IS NOT NULL;

INSERT OR IGNORE INTO clean.test_results 
SELECT * FROM corrupted.test_results 
WHERE id IS NOT NULL AND execution_id IS NOT NULL;

COMMIT;

-- Verify recovery
SELECT COUNT(*) as recovered_executions FROM clean.test_executions;
SELECT COUNT(*) as recovered_categories FROM clean.test_categories;  
SELECT COUNT(*) as recovered_results FROM clean.test_results;

DETACH corrupted;
DETACH clean;
EOF

# Replace with recovered database
mv evaluation_new.db evaluation.db
```

### Scenario 3: Service Won't Start After Rollback

**Symptoms:**
- Go service crashes on startup
- Migration errors preventing service start
- Database connection failures

**Recovery Steps:**

1. **Check Service Logs**
```bash
make logs level=ERROR
```

2. **Reset Migration State**
```bash
cd go-service
sqlite3 evaluation.db << EOF
-- Check migration state
SELECT * FROM schema_migrations ORDER BY version DESC;

-- Reset problematic migration if needed
DELETE FROM schema_migrations WHERE version = '003_test_executions';

-- Check for orphaned foreign keys
PRAGMA foreign_key_check;
EOF
```

3. **Force Service Start**
```bash
cd go-service
# Start with migration disabled
DISABLE_AUTO_MIGRATE=true go run cmd/server/main.go
```

4. **Manual Migration Repair**
```bash
cd go-service
go run cmd/migrate/main.go -force-state 002_performance_metrics
```

### Scenario 4: Data Loss During Rollback

**Symptoms:**
- Backup tables are missing or empty
- Critical data disappeared after rollback
- Application errors due to missing data

**Recovery Actions:**

1. **Check for Any Remaining Data**
```bash
cd go-service
sqlite3 evaluation.db << EOF
-- Look for any tables with data
.tables
SELECT name, 
       (SELECT COUNT(*) FROM sqlite_master s2 WHERE s2.name = s1.name AND type='table') as exists,
       CASE WHEN type='table' THEN 
         (SELECT COUNT(*) FROM pragma_table_info(s1.name)) 
       END as columns
FROM sqlite_master s1 
WHERE type='table' AND name LIKE '%test%'
ORDER BY name;
EOF
```

2. **Search for External Backups**
```bash
# Look for any backup files
find . -name "*.db*" -o -name "*backup*" | grep -E '\.(db|sql|json)$'

# Check logs directory for exported data
find logs/ -name "*.json" -o -name "*.sql" | head -10
```

3. **Restore from External Backup**
```bash
# If backup files found
cd go-service

# Option 1: Restore from .db backup
if [ -f evaluation.db.backup ]; then
    cp evaluation.db.backup evaluation.db
    echo "Database restored from backup file"
fi

# Option 2: Import from JSON export
if [ -f backup_data.json ]; then
    python3 << EOF
import json
import sqlite3

# Load backup data
with open('backup_data.json', 'r') as f:
    data = json.load(f)

# Connect to database
conn = sqlite3.connect('evaluation.db')
cursor = conn.cursor()

# Restore test_executions
if 'test_executions' in data:
    for record in data['test_executions']:
        cursor.execute('''
            INSERT OR REPLACE INTO test_executions 
            (id, test_type, model_name, prompt, status, score, correlation_id, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (record.get('id'), record.get('test_type'), record.get('model_name'), 
              record.get('prompt'), record.get('status'), record.get('score'),
              record.get('correlation_id'), record.get('session_id'), record.get('created_at')))

conn.commit()
conn.close()
print("Data restored from JSON backup")
EOF
fi
```

## Recovery Validation

After any emergency recovery, run comprehensive validation:

```bash
# Run all rollback tests
make test-database-rollback

# Validate database integrity
cd go-service
sqlite3 evaluation.db << EOF
PRAGMA integrity_check;
PRAGMA foreign_key_check;

-- Verify table structure
.schema test_executions
.schema test_results  
.schema test_categories

-- Check data consistency
SELECT 
    'test_executions' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT correlation_id) as unique_correlations,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tests
FROM test_executions
UNION ALL
SELECT 
    'test_results' as table_name,
    COUNT(*) as total_records, 
    COUNT(DISTINCT execution_id) as unique_executions,
    COUNT(CASE WHEN score IS NOT NULL THEN 1 END) as scored_results
FROM test_results
UNION ALL
SELECT 
    'test_categories' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN parent_id IS NULL THEN 1 END) as root_categories,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_categories
FROM test_categories;
EOF

# Test service startup
cd go-service
timeout 10s go run cmd/server/main.go &
sleep 5
curl -f http://localhost:8080/health || echo "Service health check failed"
```

## Prevention Measures

### Automated Backups

Set up automated backups to prevent data loss:

```bash
# Add to crontab
crontab -e

# Backup every hour during business hours
0 9-17 * * 1-5 /path/to/llm-evals/scripts/backup_database.sh

# Daily backup at midnight
0 0 * * * /path/to/llm-evals/scripts/daily_backup.sh
```

Create backup script:
```bash
#!/bin/bash
# scripts/backup_database.sh

BACKUP_DIR="/backups/llm-evals"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

cd /path/to/llm-evals/go-service
cp evaluation.db "$BACKUP_DIR/evaluation_${TIMESTAMP}.db"

# Keep only last 7 days of hourly backups
find "$BACKUP_DIR" -name "evaluation_*.db" -mtime +7 -delete

echo "Database backed up to $BACKUP_DIR/evaluation_${TIMESTAMP}.db"
```

### Monitoring and Alerts

Set up monitoring for database issues:

```bash
# Health check script
#!/bin/bash
# scripts/health_check.sh

cd /path/to/llm-evals/go-service

# Check database accessibility
if ! sqlite3 evaluation.db "SELECT 1;" >/dev/null 2>&1; then
    echo "ALERT: Database not accessible"
    exit 1
fi

# Check for corruption
if ! sqlite3 evaluation.db "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "ALERT: Database corruption detected" 
    exit 1
fi

# Check service health
if ! curl -sf http://localhost:8080/health >/dev/null; then
    echo "ALERT: Service not responding"
    exit 1
fi

echo "System healthy"
```

## Post-Recovery Checklist

After emergency recovery:

- [ ] Verify all tables exist and contain expected data
- [ ] Run comprehensive test suite
- [ ] Check application functionality
- [ ] Validate data integrity
- [ ] Update monitoring alerts
- [ ] Document incident for future prevention
- [ ] Review and improve backup procedures
- [ ] Test rollback procedures in development environment

## Contact and Escalation

### Emergency Response Team

1. **Database Issues**: Development team via project issues
2. **Infrastructure**: System administrators
3. **Data Loss**: Senior development team + management

### Documentation and Reporting

After emergency recovery:

1. Document what happened and when
2. Identify root cause
3. Update procedures to prevent recurrence
4. Share lessons learned with team
5. Improve monitoring and alerting

---

**🚨 Remember: In emergencies, preserve data first, then restore service functionality.**

*Last Updated: 2025-01-20*  
*Emergency Procedures Version: 1.0*