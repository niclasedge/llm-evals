package rollback

import (
	"context"
	"database/sql"
	"testing"
	"time"

	"go-service/internal/database/migration_tools"
	"go-service/internal/logging"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	_ "github.com/mattn/go-sqlite3"
)

// TestValidationRunner tests the validation functionality for rollback operations
func TestValidationRunner(t *testing.T) {
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
	rollbackResult, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)
	require.True(t, rollbackResult.Success)

	// Test comprehensive validation
	config := migration_tools.ValidationConfig{
		IncludeTableChecks:  true,
		IncludeIndexChecks:  true,
		IncludeDataChecks:   true,
		IncludeBackupChecks: true,
		IncludeSchemaChecks: true,
		ContinueOnFailure:   true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err)

	// Verify validation results
	assert.True(t, validationResult.Success, "Validation should pass")
	assert.Equal(t, "003_test_executions", validationResult.MigrationName)
	assert.NotEmpty(t, validationResult.ValidationID)
	assert.Greater(t, len(validationResult.Checks), 0, "Should have validation checks")
	assert.Equal(t, 0, validationResult.Summary.FailedChecks, "Should have no failed checks")
	assert.Greater(t, validationResult.Summary.PassedChecks, 0, "Should have passed checks")

	// Verify specific check types exist
	checkTypes := make(map[string]bool)
	for _, check := range validationResult.Checks {
		checkTypes[check.CheckType] = true
	}

	assert.True(t, checkTypes["table_existence"], "Should have table existence checks")
	assert.True(t, checkTypes["backup_data"], "Should have backup data checks")
}

// TestValidationWithFailures tests validation when some checks fail
func TestValidationWithFailures(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data
	setupTestExecutionData(t, db)

	// Create validation runner
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	// Simulate incomplete rollback by NOT performing the actual rollback
	// This should cause validation failures

	config := migration_tools.ValidationConfig{
		IncludeTableChecks:  true,
		IncludeIndexChecks:  true,
		IncludeDataChecks:   true,
		IncludeBackupChecks: true,
		IncludeSchemaChecks: false, // Skip schema checks to avoid unrelated failures
		ContinueOnFailure:   true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err, "Validation should complete even with failures")

	// Should have failures since rollback wasn't performed
	assert.False(t, validationResult.Success, "Validation should fail when rollback wasn't performed")
	assert.Greater(t, validationResult.Summary.FailedChecks, 0, "Should have failed checks")
	assert.Greater(t, len(validationResult.Recommendations), 0, "Should have recommendations")

	// Check for specific failure messages
	hasTableFailure := false
	hasBackupFailure := false
	for _, check := range validationResult.Checks {
		if check.CheckType == "table_existence" && check.Status == migration_tools.ValidationStatusFail {
			hasTableFailure = true
		}
		if check.CheckType == "backup_existence" && check.Status == migration_tools.ValidationStatusFail {
			hasBackupFailure = true
		}
	}

	assert.True(t, hasTableFailure || hasBackupFailure, "Should have table or backup failures")
}

// TestTableValidations tests specific table validation checks
func TestTableValidations(t *testing.T) {
	ctx := context.Background()

	tests := []struct {
		name          string
		migrationName string
		setupData     func(*testing.T, *sql.DB)
		expectedTables struct {
			removed []string
			backup  []string
		}
	}{
		{
			name:          "Test executions table validation",
			migrationName: "003_test_executions",
			setupData:     setupTestExecutionData,
			expectedTables: struct {
				removed []string
				backup  []string
			}{
				removed: []string{"test_executions"},
				backup:  []string{"test_executions_backup"},
			},
		},
		{
			name:          "Test results and categories validation",
			migrationName: "004_test_results_categories",
			setupData:     setupResultsCategoriesData,
			expectedTables: struct {
				removed []string
				backup  []string
			}{
				removed: []string{"test_results", "test_categories"},
				backup:  []string{"test_results_backup", "test_categories_backup"},
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Setup test database
			db, cleanup := setupTestDatabase(t)
			defer cleanup()

			// Setup test data
			tt.setupData(t, db)

			// Create managers and perform rollback
			logger := logging.NewDefaultLogger().Logger
			migrationsPath := "../../internal/database/migrations"
			rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
			validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

			_, err := rollbackManager.RollbackMigration(ctx, tt.migrationName)
			require.NoError(t, err)

			// Test table validations
			config := migration_tools.ValidationConfig{
				IncludeTableChecks: true,
				ContinueOnFailure:  true,
			}

			validationResult, err := validationRunner.ValidateRollback(ctx, tt.migrationName, config)
			require.NoError(t, err)

			// Verify table removal checks
			for _, tableName := range tt.expectedTables.removed {
				found := false
				for _, check := range validationResult.Checks {
					if check.Name == "table_"+tableName+"_removed" {
						found = true
						assert.Equal(t, migration_tools.ValidationStatusPass, check.Status,
							"Table %s should be marked as removed", tableName)
						break
					}
				}
				assert.True(t, found, "Should have removal check for table %s", tableName)
			}

			// Verify backup table existence checks
			for _, tableName := range tt.expectedTables.backup {
				found := false
				for _, check := range validationResult.Checks {
					if check.Name == "table_"+tableName+"_exists" {
						found = true
						assert.Equal(t, migration_tools.ValidationStatusPass, check.Status,
							"Backup table %s should exist", tableName)
						break
					}
				}
				assert.True(t, found, "Should have existence check for backup table %s", tableName)
			}
		})
	}
}

// TestIndexValidations tests that index removal is properly validated
func TestIndexValidations(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data
	setupTestExecutionData(t, db)

	// Create managers and perform rollback
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	_, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)

	// Test index validations
	config := migration_tools.ValidationConfig{
		IncludeIndexChecks: true,
		ContinueOnFailure:  true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err)

	// Verify index removal checks exist
	indexCheckFound := false
	for _, check := range validationResult.Checks {
		if check.CheckType == "index_removal" {
			indexCheckFound = true
			assert.Equal(t, migration_tools.ValidationStatusPass, check.Status,
				"Index removal check should pass")
		}
	}
	assert.True(t, indexCheckFound, "Should have index removal checks")
}

// TestDataValidations tests data integrity validation checks
func TestDataValidations(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data with foreign key relationships
	setupResultsCategoriesData(t, db)

	// Create managers and perform rollback
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	_, err := rollbackManager.RollbackMigration(ctx, "004_test_results_categories")
	require.NoError(t, err)

	// Test data validations
	config := migration_tools.ValidationConfig{
		IncludeDataChecks: true,
		ContinueOnFailure: true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "004_test_results_categories", config)
	require.NoError(t, err)

	// Verify foreign key constraint checks
	fkCheckFound := false
	for _, check := range validationResult.Checks {
		if check.CheckType == "foreign_key" {
			fkCheckFound = true
			assert.Equal(t, migration_tools.ValidationStatusPass, check.Status,
				"Foreign key check should pass")
		}
	}
	assert.True(t, fkCheckFound, "Should have foreign key constraint checks")

	// Verify backup consistency checks
	backupConsistencyFound := false
	for _, check := range validationResult.Checks {
		if check.CheckType == "backup_consistency" {
			backupConsistencyFound = true
			assert.Equal(t, migration_tools.ValidationStatusPass, check.Status,
				"Backup consistency check should pass")
		}
	}
	assert.True(t, backupConsistencyFound, "Should have backup consistency checks")
}

// TestBackupValidations tests backup-specific validation checks
func TestBackupValidations(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data
	setupTestExecutionData(t, db)

	// Create managers and perform rollback
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	_, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)

	// Test backup validations
	config := migration_tools.ValidationConfig{
		IncludeBackupChecks: true,
		ContinueOnFailure:   true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err)

	// Verify backup data checks
	backupDataFound := false
	backupExistenceFound := false

	for _, check := range validationResult.Checks {
		if check.CheckType == "backup_data" {
			backupDataFound = true
			assert.Equal(t, migration_tools.ValidationStatusPass, check.Status,
				"Backup data check should pass")
			assert.Contains(t, check.Details, "row_count", "Should include row count details")
		}
		if check.CheckType == "backup_existence" {
			backupExistenceFound = true
			assert.Equal(t, migration_tools.ValidationStatusPass, check.Status,
				"Backup existence check should pass")
		}
	}

	assert.True(t, backupDataFound, "Should have backup data checks")
	assert.True(t, backupExistenceFound, "Should have backup existence checks")
}

// TestSchemaValidations tests schema-related validation checks
func TestSchemaValidations(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data
	setupTestExecutionData(t, db)

	// Create migration_log table first to avoid warnings
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS migration_log (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			migration_name TEXT NOT NULL,
			action TEXT NOT NULL,
			timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
			details TEXT
		)
	`)
	require.NoError(t, err)

	// Create managers and perform rollback
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	_, err = rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)

	// Test schema validations
	config := migration_tools.ValidationConfig{
		IncludeSchemaChecks: true,
		ContinueOnFailure:   true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err)

	// Verify migration logging checks
	migrationLoggingFound := false
	for _, check := range validationResult.Checks {
		if check.CheckType == "migration_logging" {
			migrationLoggingFound = true
			// Should pass or warn (depending on if migration_log table exists)
			assert.Contains(t, []migration_tools.ValidationStatus{
				migration_tools.ValidationStatusPass,
				migration_tools.ValidationStatusWarning,
			}, check.Status, "Migration logging check should pass or warn")
		}
	}
	assert.True(t, migrationLoggingFound, "Should have migration logging checks")
}

// TestValidationRecommendations tests that appropriate recommendations are generated
func TestValidationRecommendations(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data but DON'T perform rollback to create failures
	setupTestExecutionData(t, db)

	// Create validation runner
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	// Run validation without rollback (should create failures)
	config := migration_tools.ValidationConfig{
		IncludeTableChecks:  true,
		IncludeBackupChecks: true,
		ContinueOnFailure:   true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err)

	// Should have failures and recommendations
	assert.False(t, validationResult.Success, "Validation should fail")
	assert.Greater(t, validationResult.Summary.FailedChecks, 0, "Should have failed checks")
	assert.Greater(t, len(validationResult.Recommendations), 0, "Should have recommendations")

	// Verify specific recommendations exist
	recommendationText := ""
	for _, rec := range validationResult.Recommendations {
		recommendationText += rec + " "
	}

	assert.Contains(t, recommendationText, "validation checks failed",
		"Should recommend reviewing failed checks")
}

// TestCustomValidations tests custom validation script functionality
func TestCustomValidations(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data and perform rollback
	setupTestExecutionData(t, db)

	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	_, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)

	// Test custom validations (note: this will fail if the custom script doesn't exist)
	config := migration_tools.ValidationConfig{
		CustomChecks:      []string{"custom_table_check"}, // This script may not exist
		ContinueOnFailure: true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err)

	// Check if custom validation was attempted
	customCheckFound := false
	for _, check := range validationResult.Checks {
		if check.CheckType == "custom_validation" && check.Name == "custom_table_check" {
			customCheckFound = true
			// Should fail because the script likely doesn't exist
			assert.Equal(t, migration_tools.ValidationStatusFail, check.Status,
				"Custom check should fail if script doesn't exist")
			break
		}
	}
	assert.True(t, customCheckFound, "Should attempt custom validation")
}

// TestValidationPerformance tests that validation completes within reasonable time
func TestValidationPerformance(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping performance test in short mode")
	}

	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Create larger dataset
	createLargeDataset(t, db, 500)

	// Create managers and perform rollback
	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	_, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)

	// Measure validation performance
	config := migration_tools.ValidationConfig{
		IncludeTableChecks:  true,
		IncludeIndexChecks:  true,
		IncludeDataChecks:   true,
		IncludeBackupChecks: true,
		IncludeSchemaChecks: true,
		ContinueOnFailure:   true,
	}

	start := time.Now()
	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	duration := time.Since(start)

	require.NoError(t, err)
	assert.True(t, validationResult.Success, "Validation should pass")

	// Log performance and assert reasonable time
	t.Logf("Validation of 500-record rollback took %v", duration)
	assert.Less(t, duration, 5*time.Second, "Validation should complete within reasonable time")

	// Verify all checks have execution times
	for _, check := range validationResult.Checks {
		if check.CheckType == "custom_validation" {
			assert.Greater(t, check.ExecutionTime, time.Duration(0), "Should have execution time recorded")
		}
	}
}

// TestValidationSummary tests that validation summary is calculated correctly
func TestValidationSummary(t *testing.T) {
	ctx := context.Background()

	// Setup test database
	db, cleanup := setupTestDatabase(t)
	defer cleanup()

	// Setup test data and perform rollback
	setupTestExecutionData(t, db)

	logger := logging.NewDefaultLogger().Logger
	migrationsPath := "../../internal/database/migrations"
	rollbackManager := migration_tools.NewRollbackManager(db, migrationsPath, logger)
	validationRunner := migration_tools.NewValidationRunner(db, migrationsPath, logger)

	_, err := rollbackManager.RollbackMigration(ctx, "003_test_executions")
	require.NoError(t, err)

	// Run comprehensive validation
	config := migration_tools.ValidationConfig{
		IncludeTableChecks:  true,
		IncludeIndexChecks:  true,
		IncludeDataChecks:   true,
		IncludeBackupChecks: true,
		IncludeSchemaChecks: true,
		ContinueOnFailure:   true,
	}

	validationResult, err := validationRunner.ValidateRollback(ctx, "003_test_executions", config)
	require.NoError(t, err)

	// Verify summary calculations
	summary := validationResult.Summary
	totalCalculated := summary.PassedChecks + summary.FailedChecks + summary.WarningChecks + summary.SkippedChecks

	assert.Equal(t, summary.TotalChecks, totalCalculated, "Summary totals should match")
	assert.Equal(t, len(validationResult.Checks), summary.TotalChecks, "Total checks should match actual checks")
	assert.GreaterOrEqual(t, summary.PassedChecks, 0, "Should have non-negative passed checks")
	assert.GreaterOrEqual(t, summary.FailedChecks, 0, "Should have non-negative failed checks")
	assert.GreaterOrEqual(t, summary.WarningChecks, 0, "Should have non-negative warning checks")
	assert.GreaterOrEqual(t, summary.SkippedChecks, 0, "Should have non-negative skipped checks")

	// Since rollback was successful, should have mostly passed checks
	assert.Greater(t, summary.PassedChecks, 0, "Should have some passed checks")
	assert.Equal(t, 0, summary.FailedChecks, "Should have no failed checks for successful rollback")
}