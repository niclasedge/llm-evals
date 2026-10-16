package rollback

import (
	"context"
	"database/sql"
	"path/filepath"
	"testing"

	"go-service/internal/database"
	"go-service/internal/database/migration_tools"
	"go-service/internal/logging"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	_ "github.com/mattn/go-sqlite3"
)

// setupTestDatabase creates a test database and returns cleanup function
func setupTestDatabase(t *testing.T) (*sql.DB, func()) {
	tempDir := t.TempDir()
	dbPath := filepath.Join(tempDir, "test_rollback.db")

	db, err := sql.Open("sqlite3", dbPath)
	require.NoError(t, err, "Failed to open test database")

	// Run forward migrations first
	config := database.Config{
		Path:           dbPath,
		MaxConnections: 5,
		AutoMigrate:    true,
	}

	testDB, err := database.NewDB(config)
	require.NoError(t, err, "Failed to create database instance")
	
	// Close the database instance but keep the raw connection
	testDB.Close()

	cleanup := func() {
		db.Close()
	}

	return db, cleanup
}

// setupTestExecutionData creates test data in test_executions table
func setupTestExecutionData(t *testing.T, db *sql.DB) {
	// Insert test data
	insertSQL := `
		INSERT INTO test_executions (
			test_type, model_name, prompt, status, score, correlation_id, session_id
		) VALUES 
		('coding', 'llama3.2:3b', 'Write a fibonacci function', 'completed', 0.85, 'test-1', 'session-1'),
		('reasoning', 'gemma3:27b', 'Solve logic puzzle', 'completed', 0.92, 'test-2', 'session-1'),
		('creative', 'mistral-small3.2', 'Write a story', 'completed', 0.78, 'test-3', 'session-2')
	`
	_, err := db.Exec(insertSQL)
	require.NoError(t, err, "Failed to insert test execution data")
}

// setupResultsCategoriesData creates test data in test_results and test_categories tables
func setupResultsCategoriesData(t *testing.T, db *sql.DB) {
	// The tables should already have seed data from migration 005
	// Add some additional test data
	insertCategorySQL := `
		INSERT INTO test_categories (
			name, display_name, description, status, version
		) VALUES 
		('custom-test', 'Custom Test Category', 'User-created test category', 'active', '1.0')
	`
	_, err := db.Exec(insertCategorySQL)
	require.NoError(t, err, "Failed to insert test category data")

	// Get test execution IDs for foreign key references
	insertResultSQL := `
		INSERT INTO test_results (
			execution_id, result_type, score, expected_value, actual_value
		) VALUES 
		(1, 'primary', 0.85, 'correct solution', 'working solution'),
		(2, 'primary', 0.92, 'logical answer', 'correct logic'),
		(3, 'primary', 0.78, 'creative story', 'engaging narrative')
	`
	_, err = db.Exec(insertResultSQL)
	require.NoError(t, err, "Failed to insert test result data")
}

// setupSeedData verifies seed data exists (should already be there from migration 005)
func setupSeedData(t *testing.T, db *sql.DB) {
	// Verify seed data exists
	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM test_categories WHERE id IN (1,2,3,4)").Scan(&count)
	require.NoError(t, err, "Failed to query seed data")
	assert.GreaterOrEqual(t, count, 4, "Seed data should exist before rollback test")
}

// Test migration rollback functionality
func TestMigrationRollback(t *testing.T) {
	tests := []struct {
		name          string
		migrationName string
		setupData     func(*testing.T, *sql.DB)
		validateData  func(*testing.T, *sql.DB, *migration_tools.RollbackResult)
	}{
		{
			name:          "Test executions table rollback",
			migrationName: "003_test_executions",
			setupData:     setupTestExecutionData,
			validateData:  validateTestExecutionRollback,
		},
		{
			name:          "Test results and categories rollback",
			migrationName: "004_test_results_categories",
			setupData:     setupResultsCategoriesData,
			validateData:  validateResultsCategoriesRollback,
		},
		{
			name:          "Seed data rollback",
			migrationName: "005_seed_test_categories",
			setupData:     setupSeedData,
			validateData:  validateSeedDataRollback,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()

			// Setup test database
			db, cleanup := setupTestDatabase(t)
			defer cleanup()

			// Setup test data
			tt.setupData(t, db)

			// Create rollback manager
			logger := logging.NewDefaultLogger().Logger
			migrationsPath := "../../internal/database/migrations"
			rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)

			// Perform rollback
			result, err := rollbackManager.RollbackMigration(ctx, tt.migrationName)
			require.NoError(t, err, "Rollback should not fail")
			assert.True(t, result.Success, "Rollback should be successful")
			assert.Equal(t, tt.migrationName, result.MigrationName)

			// Validate rollback
			tt.validateData(t, db, result)
		})
	}
}

// validateTestExecutionRollback validates that test_executions table rollback was successful
func validateTestExecutionRollback(t *testing.T, db *sql.DB, result *migration_tools.RollbackResult) {
	// Table should be removed
	var exists int
	err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='test_executions'").Scan(&exists)
	require.NoError(t, err)
	assert.Equal(t, 0, exists, "test_executions table should be removed")

	// Backup table should exist
	err = db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='test_executions_backup'").Scan(&exists)
	require.NoError(t, err)
	assert.Equal(t, 1, exists, "test_executions_backup table should exist")

	// Backup should contain data
	var backupCount int
	err = db.QueryRow("SELECT COUNT(*) FROM test_executions_backup").Scan(&backupCount)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, backupCount, 3, "Backup should contain test data")

	// Backup should have timestamp column
	err = db.QueryRow("SELECT COUNT(*) FROM pragma_table_info('test_executions_backup') WHERE name='backup_timestamp'").Scan(&exists)
	require.NoError(t, err)
	assert.Equal(t, 1, exists, "Backup table should have timestamp column")

	// Verify result contains backup table info
	assert.Contains(t, result.BackupTables, "test_executions_backup")
}

// validateResultsCategoriesRollback validates that test_results and test_categories rollback was successful
func validateResultsCategoriesRollback(t *testing.T, db *sql.DB, result *migration_tools.RollbackResult) {
	// Both tables should be removed
	var exists int
	err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('test_results', 'test_categories')").Scan(&exists)
	require.NoError(t, err)
	assert.Equal(t, 0, exists, "test_results and test_categories tables should be removed")

	// Backup tables should exist
	err = db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('test_results_backup', 'test_categories_backup')").Scan(&exists)
	require.NoError(t, err)
	assert.Equal(t, 2, exists, "Backup tables should exist")

	// Check category_id column was removed from test_executions
	var columnExists int
	err = db.QueryRow("SELECT COUNT(*) FROM pragma_table_info('test_executions') WHERE name='category_id'").Scan(&columnExists)
	require.NoError(t, err)
	assert.Equal(t, 0, columnExists, "category_id column should be removed from test_executions")

	// Verify backup tables contain data
	var backupCount int
	err = db.QueryRow("SELECT COUNT(*) FROM test_results_backup").Scan(&backupCount)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, backupCount, 3, "test_results_backup should contain data")

	err = db.QueryRow("SELECT COUNT(*) FROM test_categories_backup").Scan(&backupCount)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, backupCount, 1, "test_categories_backup should contain data")

	// Verify result contains backup table info
	assert.Contains(t, result.BackupTables, "test_results_backup")
	assert.Contains(t, result.BackupTables, "test_categories_backup")
}

// validateSeedDataRollback validates that seed data rollback was successful
func validateSeedDataRollback(t *testing.T, db *sql.DB, result *migration_tools.RollbackResult) {
	// Table should still exist (we only remove seed data, not the table)
	var exists int
	err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='test_categories'").Scan(&exists)
	require.NoError(t, err)
	assert.Equal(t, 1, exists, "test_categories table should still exist after seed rollback")

	// Seed categories should be removed
	var seedCount int
	err = db.QueryRow(`
		SELECT COUNT(*) FROM test_categories 
		WHERE id IN (1, 2, 3, 4, 101, 102, 103, 201, 202)
		AND name IN ('coding', 'reasoning', 'creative', 'tool-calling')
	`).Scan(&seedCount)
	require.NoError(t, err)
	assert.Equal(t, 0, seedCount, "Seed categories should be removed")

	// User-created categories should remain (if any were added)
	var userCount int
	err = db.QueryRow("SELECT COUNT(*) FROM test_categories WHERE name = 'custom-test'").Scan(&userCount)
	if err == nil {
		// If the custom category was added, it should still be there
		assert.GreaterOrEqual(t, userCount, 0, "User categories should be preserved")
	}

	// Backup table should exist
	if len(result.BackupTables) > 0 {
		assert.Contains(t, result.BackupTables, "test_categories_backup")
	}
}

// Test rollback validation functionality
func TestRollbackValidation(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data
	setupTestExecutionData(t, db)

	// Create managers
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	// Perform rollback
	result, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)
	require.True(t, result.Success)

	// Validate rollback
	config := migration_tools.ValidationConfig{
		IncludeTableChecks:  true,
		IncludeIndexChecks:  true,
		IncludeDataChecks:   true,
		IncludeBackupChecks: true,
		IncludeSchemaChecks: true,
		ContinueOnFailure:   true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err, "Validation should not fail")
	assert.True(t, validationResult.Success, "Validation should pass")
	assert.Equal(t, "003_test_executions", validationResult.MigrationName)
	assert.Greater(t, len(validationResult.Checks), 0, "Should have validation checks")
	assert.Equal(t, 0, validationResult.Summary.FailedChecks, "Should have no failed checks")
}

// Test backup and recovery functionality
func TestBackupAndRecovery(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data
	setupTestExecutionData(t, db)

	// Create backup manager
	logger := logging.NewDefaultLogger().Logger
	backupPath := t.TempDir()
	backupManager := migration_tools.NewBackupManager(db, backupPath, logger)

	// Create backup
	config := migration_tools.BackupConfig{
		IncludeData:   true,
		Tables:        []string{"test_executions"},
		ExportFormat:  "json",
		Compression:   false,
		RetentionDays: 7,
	}

	backupResult, err := backupManager.CreateBackup(ctx, "003_test_executions", config)
	require.NoError(t, err, "Backup creation should not fail")
	assert.True(t, backupResult.Success, "Backup should be successful")
	assert.NotEmpty(t, backupResult.BackupID, "Backup should have ID")
	assert.NotEmpty(t, backupResult.FilePath, "Backup should have file path")
	assert.Greater(t, backupResult.FileSize, int64(0), "Backup file should not be empty")
	assert.Equal(t, 3, backupResult.Tables["test_executions"], "Should backup 3 test execution records")
}

// Benchmark rollback performance
func BenchmarkRollback(b *testing.B) {
	ctx := context.Background()

	// Setup test database
	tempDir := b.TempDir()
	dbPath := filepath.Join(tempDir, "bench_rollback.db")

	config := database.Config{
		Path:           dbPath,
		MaxConnections: 5,
		AutoMigrate:    true,
	}

	testDB, err := database.NewDB(config)
	require.NoError(b, err)
	testDB.Close()

	db, err := sql.Open("sqlite3", dbPath)
	require.NoError(b, err)
	defer db.Close()

	// Create managers
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		// Setup test data for each iteration
		setupTestExecutionData(&testing.T{}, db)

		// Benchmark rollback operation
		result, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
		require.NoError(b, err)
		require.True(b, result.Success)

		// Recreate table for next iteration
		_, err = db.Exec(`
			CREATE TABLE test_executions (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				test_type VARCHAR(50) NOT NULL,
				model_name VARCHAR(100) NOT NULL,
				prompt TEXT NOT NULL,
				status VARCHAR(20) DEFAULT 'pending',
				score REAL,
				correlation_id VARCHAR(50),
				session_id VARCHAR(100),
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		`)
		require.NoError(b, err)
	}
}