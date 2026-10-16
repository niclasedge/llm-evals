package migration_tools

import (
	"context"
	"database/sql"
	"fmt"
	"io/ioutil"
	"log/slog"
	"path/filepath"
	"strings"
	"time"

	"go-service/internal/logging"
)

// ValidationRunner handles validation of rollback operations and database integrity
type ValidationRunner struct {
	db             *sql.DB
	migrationsPath string
	logger         *slog.Logger
}

// ValidationResult contains the results of a validation operation
type ValidationResult struct {
	Success          bool                 `json:"success"`
	ValidationID     string               `json:"validation_id"`
	Timestamp        time.Time            `json:"timestamp"`
	MigrationName    string               `json:"migration_name"`
	Checks           []ValidationCheck    `json:"checks"`
	Summary          ValidationSummary    `json:"summary"`
	Recommendations  []string             `json:"recommendations,omitempty"`
	ErrorMessage     string               `json:"error_message,omitempty"`
}

// ValidationCheck represents a single validation check
type ValidationCheck struct {
	CheckType    string            `json:"check_type"`
	Name         string            `json:"name"`
	Description  string            `json:"description"`
	Status       ValidationStatus  `json:"status"`
	Message      string            `json:"message"`
	Details      map[string]string `json:"details,omitempty"`
	ExecutionTime time.Duration    `json:"execution_time"`
}

// ValidationSummary provides an overview of validation results
type ValidationSummary struct {
	TotalChecks   int `json:"total_checks"`
	PassedChecks  int `json:"passed_checks"`
	FailedChecks  int `json:"failed_checks"`
	WarningChecks int `json:"warning_checks"`
	SkippedChecks int `json:"skipped_checks"`
}

// ValidationStatus represents the status of a validation check
type ValidationStatus string

const (
	ValidationStatusPass    ValidationStatus = "pass"
	ValidationStatusFail    ValidationStatus = "fail"
	ValidationStatusWarning ValidationStatus = "warning"
	ValidationStatusSkipped ValidationStatus = "skipped"
)

// ValidationConfig defines what validations to run
type ValidationConfig struct {
	IncludeTableChecks    bool     `json:"include_table_checks"`
	IncludeIndexChecks    bool     `json:"include_index_checks"`
	IncludeDataChecks     bool     `json:"include_data_checks"`
	IncludeBackupChecks   bool     `json:"include_backup_checks"`
	IncludeSchemaChecks   bool     `json:"include_schema_checks"`
	CustomChecks          []string `json:"custom_checks,omitempty"`
	SkipChecks            []string `json:"skip_checks,omitempty"`
	ContinueOnFailure     bool     `json:"continue_on_failure"`
}

// NewValidationRunner creates a new ValidationRunner instance
func NewValidationRunner(db *sql.DB, migrationsPath string, logger *slog.Logger) *ValidationRunner {
	if logger == nil {
		logger = logging.NewDefaultLogger().Logger
	}
	
	return &ValidationRunner{
		db:             db,
		migrationsPath: migrationsPath,
		logger:         logger,
	}
}

// ValidateRollback performs comprehensive validation of a rollback operation
func (vr *ValidationRunner) ValidateRollback(ctx context.Context, migrationName string, config ValidationConfig) (*ValidationResult, error) {
	correlationID := logging.NewCorrelationID()
	ctx = logging.WithCorrelationID(ctx, correlationID)
	
	validationID := fmt.Sprintf("validation_%s_%d", migrationName, time.Now().Unix())
	
	result := &ValidationResult{
		ValidationID:  validationID,
		Timestamp:     time.Now(),
		MigrationName: migrationName,
		Checks:        make([]ValidationCheck, 0),
		Recommendations: make([]string, 0),
	}
	
	logger := logging.LogWithContext(ctx, vr.logger)
	logger.Info("Starting rollback validation",
		"component", "migration_tools.validation_runner",
		"validation_id", validationID,
		"migration", migrationName,
	)
	
	// Run validation checks based on configuration
	if config.IncludeTableChecks {
		vr.runTableValidations(ctx, migrationName, result)
	}
	
	if config.IncludeIndexChecks {
		vr.runIndexValidations(ctx, migrationName, result)
	}
	
	if config.IncludeDataChecks {
		vr.runDataValidations(ctx, migrationName, result)
	}
	
	if config.IncludeBackupChecks {
		vr.runBackupValidations(ctx, migrationName, result)
	}
	
	if config.IncludeSchemaChecks {
		vr.runSchemaValidations(ctx, migrationName, result)
	}
	
	// Run custom validation scripts
	for _, checkName := range config.CustomChecks {
		if !vr.shouldSkipCheck(checkName, config.SkipChecks) {
			vr.runCustomValidation(ctx, checkName, result)
		}
	}
	
	// Calculate summary
	vr.calculateSummary(result)
	
	// Generate recommendations
	vr.generateRecommendations(result)
	
	// Determine overall success
	result.Success = result.Summary.FailedChecks == 0
	
	logger.Info("Rollback validation completed",
		"validation_id", validationID,
		"total_checks", result.Summary.TotalChecks,
		"passed", result.Summary.PassedChecks,
		"failed", result.Summary.FailedChecks,
		"warnings", result.Summary.WarningChecks,
		"success", result.Success,
	)
	
	return result, nil
}

// runTableValidations validates table existence and removal
func (vr *ValidationRunner) runTableValidations(ctx context.Context, migrationName string, result *ValidationResult) {
	logger := logging.LogWithContext(ctx, vr.logger)
	
	switch migrationName {
	case "003_test_executions":
		vr.addTableExistenceCheck("test_executions", false, "test_executions table should be removed", result)
		vr.addTableExistenceCheck("test_executions_backup", true, "test_executions backup should exist", result)
		
	case "004_test_results_categories":
		vr.addTableExistenceCheck("test_results", false, "test_results table should be removed", result)
		vr.addTableExistenceCheck("test_categories", false, "test_categories table should be removed", result)
		vr.addTableExistenceCheck("test_results_backup", true, "test_results backup should exist", result)
		vr.addTableExistenceCheck("test_categories_backup", true, "test_categories backup should exist", result)
		
	case "005_seed_test_categories":
		// For seed rollback, table should still exist but seed data should be removed
		if vr.tableExists("test_categories") {
			vr.addSeedDataCheck("test_categories", result)
		} else {
			vr.addValidationCheck(ValidationCheck{
				CheckType:   "table_existence",
				Name:        "test_categories_exists",
				Description: "test_categories table should exist after seed rollback",
				Status:      ValidationStatusWarning,
				Message:     "test_categories table does not exist",
			}, result)
		}
	}
	
	logger.Debug("Table validations completed", "migration", migrationName)
}

// runIndexValidations validates index removal
func (vr *ValidationRunner) runIndexValidations(ctx context.Context, migrationName string, result *ValidationResult) {
	logger := logging.LogWithContext(ctx, vr.logger)
	
	expectedRemovedIndexes := vr.getExpectedRemovedIndexes(migrationName)
	
	for _, indexName := range expectedRemovedIndexes {
		exists := vr.indexExists(indexName)
		status := ValidationStatusPass
		message := fmt.Sprintf("Index %s successfully removed", indexName)
		
		if exists {
			status = ValidationStatusFail
			message = fmt.Sprintf("Index %s still exists", indexName)
		}
		
		vr.addValidationCheck(ValidationCheck{
			CheckType:   "index_removal",
			Name:        fmt.Sprintf("index_%s_removed", indexName),
			Description: fmt.Sprintf("Index %s should be removed", indexName),
			Status:      status,
			Message:     message,
		}, result)
	}
	
	logger.Debug("Index validations completed", "migration", migrationName)
}

// runDataValidations validates data integrity and preservation
func (vr *ValidationRunner) runDataValidations(ctx context.Context, migrationName string, result *ValidationResult) {
	logger := logging.LogWithContext(ctx, vr.logger)
	
	// Check foreign key constraints are properly handled
	vr.checkForeignKeyConstraints(ctx, migrationName, result)
	
	// Check data consistency in backup tables
	vr.checkBackupDataConsistency(ctx, migrationName, result)
	
	logger.Debug("Data validations completed", "migration", migrationName)
}

// runBackupValidations validates backup table creation and data preservation
func (vr *ValidationRunner) runBackupValidations(ctx context.Context, migrationName string, result *ValidationResult) {
	logger := logging.LogWithContext(ctx, vr.logger)
	
	expectedBackupTables := vr.getExpectedBackupTables(migrationName)
	
	for _, tableName := range expectedBackupTables {
		backupTableName := tableName + "_backup"
		
		if vr.tableExists(backupTableName) {
			// Check backup has data
			count, err := vr.getTableRowCount(backupTableName)
			if err != nil {
				vr.addValidationCheck(ValidationCheck{
					CheckType:   "backup_data",
					Name:        fmt.Sprintf("backup_%s_accessible", tableName),
					Description: fmt.Sprintf("Backup table %s should be accessible", backupTableName),
					Status:      ValidationStatusFail,
					Message:     fmt.Sprintf("Failed to query backup table: %v", err),
				}, result)
				continue
			}
			
			status := ValidationStatusPass
			message := fmt.Sprintf("Backup table %s contains %d records", backupTableName, count)
			
			if count == 0 {
				status = ValidationStatusWarning
				message = fmt.Sprintf("Backup table %s is empty", backupTableName)
			}
			
			vr.addValidationCheck(ValidationCheck{
				CheckType:   "backup_data",
				Name:        fmt.Sprintf("backup_%s_data", tableName),
				Description: fmt.Sprintf("Backup table %s should contain data", backupTableName),
				Status:      status,
				Message:     message,
				Details:     map[string]string{"row_count": fmt.Sprintf("%d", count)},
			}, result)
			
		} else {
			vr.addValidationCheck(ValidationCheck{
				CheckType:   "backup_existence",
				Name:        fmt.Sprintf("backup_%s_exists", tableName),
				Description: fmt.Sprintf("Backup table %s should exist", backupTableName),
				Status:      ValidationStatusFail,
				Message:     fmt.Sprintf("Backup table %s does not exist", backupTableName),
			}, result)
		}
	}
	
	logger.Debug("Backup validations completed", "migration", migrationName)
}

// runSchemaValidations validates database schema integrity
func (vr *ValidationRunner) runSchemaValidations(ctx context.Context, migrationName string, result *ValidationResult) {
	logger := logging.LogWithContext(ctx, vr.logger)
	
	// Check schema_migrations table is updated
	vr.checkSchemaMigrationsTable(ctx, migrationName, result)
	
	// Check migration_log table entries
	vr.checkMigrationLogEntries(ctx, migrationName, result)
	
	logger.Debug("Schema validations completed", "migration", migrationName)
}

// runCustomValidation runs custom validation scripts
func (vr *ValidationRunner) runCustomValidation(ctx context.Context, checkName string, result *ValidationResult) {
	start := time.Now()
	
	scriptPath := filepath.Join(vr.migrationsPath, "rollback", fmt.Sprintf("%s.sql", checkName))
	
	script, err := ioutil.ReadFile(scriptPath)
	if err != nil {
		vr.addValidationCheck(ValidationCheck{
			CheckType:     "custom_validation",
			Name:          checkName,
			Description:   fmt.Sprintf("Custom validation: %s", checkName),
			Status:        ValidationStatusFail,
			Message:       fmt.Sprintf("Failed to load validation script: %v", err),
			ExecutionTime: time.Since(start),
		}, result)
		return
	}
	
	rows, err := vr.db.QueryContext(ctx, string(script))
	if err != nil {
		vr.addValidationCheck(ValidationCheck{
			CheckType:     "custom_validation",
			Name:          checkName,
			Description:   fmt.Sprintf("Custom validation: %s", checkName),
			Status:        ValidationStatusFail,
			Message:       fmt.Sprintf("Failed to execute validation script: %v", err),
			ExecutionTime: time.Since(start),
		}, result)
		return
	}
	defer rows.Close()
	
	// Process validation results
	status := ValidationStatusPass
	var messages []string
	
	for rows.Next() {
		var checkType, message string
		if err := rows.Scan(&checkType, &message); err != nil {
			continue
		}
		
		messages = append(messages, fmt.Sprintf("%s: %s", checkType, message))
		
		if strings.Contains(message, "ERROR") {
			status = ValidationStatusFail
		} else if strings.Contains(message, "WARNING") && status == ValidationStatusPass {
			status = ValidationStatusWarning
		}
	}
	
	vr.addValidationCheck(ValidationCheck{
		CheckType:     "custom_validation",
		Name:          checkName,
		Description:   fmt.Sprintf("Custom validation: %s", checkName),
		Status:        status,
		Message:       strings.Join(messages, "; "),
		ExecutionTime: time.Since(start),
	}, result)
}

// Helper methods

// addTableExistenceCheck adds a validation check for table existence
func (vr *ValidationRunner) addTableExistenceCheck(tableName string, shouldExist bool, description string, result *ValidationResult) {
	exists := vr.tableExists(tableName)
	status := ValidationStatusPass
	message := fmt.Sprintf("Table %s existence validated", tableName)
	
	if shouldExist && !exists {
		status = ValidationStatusFail
		message = fmt.Sprintf("Table %s does not exist but should", tableName)
	} else if !shouldExist && exists {
		status = ValidationStatusFail
		message = fmt.Sprintf("Table %s exists but should not", tableName)
	}
	
	vr.addValidationCheck(ValidationCheck{
		CheckType:   "table_existence",
		Name:        fmt.Sprintf("table_%s_%s", tableName, map[bool]string{true: "exists", false: "removed"}[shouldExist]),
		Description: description,
		Status:      status,
		Message:     message,
	}, result)
}

// addSeedDataCheck validates seed data removal
func (vr *ValidationRunner) addSeedDataCheck(tableName string, result *ValidationResult) {
	count, err := vr.getSeedCategoryCount()
	
	status := ValidationStatusPass
	message := "All seed categories successfully removed"
	
	if err != nil {
		status = ValidationStatusFail
		message = fmt.Sprintf("Failed to check seed data: %v", err)
	} else if count > 0 {
		status = ValidationStatusWarning
		message = fmt.Sprintf("%d seed categories remain (may be user-modified)", count)
	}
	
	vr.addValidationCheck(ValidationCheck{
		CheckType:   "seed_data",
		Name:        "seed_categories_removed",
		Description: "Seed categories should be removed",
		Status:      status,
		Message:     message,
		Details:     map[string]string{"remaining_count": fmt.Sprintf("%d", count)},
	}, result)
}

// addValidationCheck adds a validation check to the result
func (vr *ValidationRunner) addValidationCheck(check ValidationCheck, result *ValidationResult) {
	result.Checks = append(result.Checks, check)
}

// calculateSummary calculates validation summary statistics
func (vr *ValidationRunner) calculateSummary(result *ValidationResult) {
	summary := ValidationSummary{
		TotalChecks: len(result.Checks),
	}
	
	for _, check := range result.Checks {
		switch check.Status {
		case ValidationStatusPass:
			summary.PassedChecks++
		case ValidationStatusFail:
			summary.FailedChecks++
		case ValidationStatusWarning:
			summary.WarningChecks++
		case ValidationStatusSkipped:
			summary.SkippedChecks++
		}
	}
	
	result.Summary = summary
}

// generateRecommendations generates recommendations based on validation results
func (vr *ValidationRunner) generateRecommendations(result *ValidationResult) {
	if result.Summary.FailedChecks > 0 {
		result.Recommendations = append(result.Recommendations, 
			"Some validation checks failed. Review error messages and consider using recovery scripts.")
	}
	
	if result.Summary.WarningChecks > 0 {
		result.Recommendations = append(result.Recommendations,
			"Some validation checks produced warnings. Review for potential issues.")
	}
	
	// Check for missing backup tables
	for _, check := range result.Checks {
		if check.CheckType == "backup_existence" && check.Status == ValidationStatusFail {
			result.Recommendations = append(result.Recommendations,
				"Missing backup tables detected. Ensure data can be recovered before proceeding.")
			break
		}
	}
	
	// Check for foreign key issues
	for _, check := range result.Checks {
		if check.CheckType == "foreign_key" && check.Status == ValidationStatusFail {
			result.Recommendations = append(result.Recommendations,
				"Foreign key constraint issues detected. Verify data integrity.")
			break
		}
	}
}

// shouldSkipCheck determines if a check should be skipped
func (vr *ValidationRunner) shouldSkipCheck(checkName string, skipList []string) bool {
	for _, skip := range skipList {
		if skip == checkName {
			return true
		}
	}
	return false
}

// Helper methods for database queries (reused from other components)

func (vr *ValidationRunner) tableExists(tableName string) bool {
	query := "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
	var exists int
	err := vr.db.QueryRow(query, tableName).Scan(&exists)
	return err == nil
}

func (vr *ValidationRunner) indexExists(indexName string) bool {
	query := "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?"
	var exists int
	err := vr.db.QueryRow(query, indexName).Scan(&exists)
	return err == nil
}

func (vr *ValidationRunner) getTableRowCount(tableName string) (int, error) {
	query := fmt.Sprintf("SELECT COUNT(*) FROM %s", tableName)
	var count int
	err := vr.db.QueryRow(query).Scan(&count)
	return count, err
}

func (vr *ValidationRunner) getSeedCategoryCount() (int, error) {
	if !vr.tableExists("test_categories") {
		return 0, nil
	}
	
	query := `
		SELECT COUNT(*) FROM test_categories 
		WHERE id IN (1, 2, 3, 4, 101, 102, 103, 201, 202)
		AND name IN ('coding', 'reasoning', 'creative', 'tool-calling', 
					 'algorithms', 'data-structures', 'debugging', 
					 'logical-reasoning', 'mathematical-reasoning')
	`
	var count int
	err := vr.db.QueryRow(query).Scan(&count)
	return count, err
}

// getExpectedRemovedIndexes returns indexes that should be removed for a migration
func (vr *ValidationRunner) getExpectedRemovedIndexes(migrationName string) []string {
	switch migrationName {
	case "003_test_executions":
		return []string{
			"idx_test_executions_type_status_date",
			"idx_test_executions_model_date",
			"idx_test_executions_score",
			"idx_test_executions_completed_at",
			"idx_test_executions_session_id",
			"idx_test_executions_correlation_id",
			"idx_test_executions_status_created",
			"idx_test_executions_model_type",
		}
	case "004_test_results_categories":
		return []string{
			"idx_test_results_execution_id",
			"idx_test_results_type_score",
			"idx_test_results_score",
			"idx_test_results_created_at",
			"idx_test_results_execution_type",
			"idx_test_categories_name",
			"idx_test_categories_parent",
			"idx_test_categories_path",
			"idx_test_categories_status",
			"idx_test_categories_parent_order",
			"idx_test_executions_category_id",
		}
	default:
		return []string{}
	}
}

// getExpectedBackupTables returns tables that should have backups for a migration
func (vr *ValidationRunner) getExpectedBackupTables(migrationName string) []string {
	switch migrationName {
	case "003_test_executions":
		return []string{"test_executions"}
	case "004_test_results_categories":
		return []string{"test_results", "test_categories"}
	case "005_seed_test_categories":
		return []string{"test_categories"}
	default:
		return []string{}
	}
}

// checkForeignKeyConstraints validates foreign key constraint handling
func (vr *ValidationRunner) checkForeignKeyConstraints(ctx context.Context, migrationName string, result *ValidationResult) {
	// For migration 004, check that category_id column was removed from test_executions
	if migrationName == "004_test_results_categories" {
		if vr.tableExists("test_executions") {
			hasColumn := vr.columnExists("test_executions", "category_id")
			
			status := ValidationStatusPass
			message := "category_id column successfully removed from test_executions"
			
			if hasColumn {
				status = ValidationStatusFail
				message = "category_id column still exists in test_executions"
			}
			
			vr.addValidationCheck(ValidationCheck{
				CheckType:   "foreign_key",
				Name:        "category_id_column_removed",
				Description: "category_id column should be removed from test_executions",
				Status:      status,
				Message:     message,
			}, result)
		}
	}
}

// checkBackupDataConsistency validates backup table data consistency
func (vr *ValidationRunner) checkBackupDataConsistency(ctx context.Context, migrationName string, result *ValidationResult) {
	expectedBackupTables := vr.getExpectedBackupTables(migrationName)
	
	for _, tableName := range expectedBackupTables {
		backupTableName := tableName + "_backup"
		
		if vr.tableExists(backupTableName) {
			// Check backup table has backup_timestamp column
			hasTimestamp := vr.columnExists(backupTableName, "backup_timestamp")
			
			status := ValidationStatusPass
			message := fmt.Sprintf("Backup table %s has proper timestamp", backupTableName)
			
			if !hasTimestamp {
				status = ValidationStatusWarning
				message = fmt.Sprintf("Backup table %s missing backup_timestamp column", backupTableName)
			}
			
			vr.addValidationCheck(ValidationCheck{
				CheckType:   "backup_consistency",
				Name:        fmt.Sprintf("backup_%s_timestamp", tableName),
				Description: fmt.Sprintf("Backup table %s should have timestamp", backupTableName),
				Status:      status,
				Message:     message,
			}, result)
		}
	}
}

// checkSchemaMigrationsTable validates schema migrations tracking
func (vr *ValidationRunner) checkSchemaMigrationsTable(ctx context.Context, migrationName string, result *ValidationResult) {
	if !vr.tableExists("schema_migrations") {
		vr.addValidationCheck(ValidationCheck{
			CheckType:   "schema_tracking",
			Name:        "schema_migrations_exists",
			Description: "schema_migrations table should exist for tracking",
			Status:      ValidationStatusWarning,
			Message:     "schema_migrations table does not exist",
		}, result)
		return
	}
	
	// Check if migration is properly tracked
	query := "SELECT COUNT(*) FROM schema_migrations WHERE version = ?"
	var count int
	err := vr.db.QueryRowContext(ctx, query, migrationName).Scan(&count)
	
	status := ValidationStatusPass
	message := fmt.Sprintf("Migration %s tracking validated", migrationName)
	
	if err != nil || count == 0 {
		status = ValidationStatusWarning
		message = fmt.Sprintf("Migration %s not found in schema_migrations", migrationName)
	}
	
	vr.addValidationCheck(ValidationCheck{
		CheckType:   "schema_tracking",
		Name:        "migration_tracked",
		Description: "Migration should be tracked in schema_migrations",
		Status:      status,
		Message:     message,
	}, result)
}

// checkMigrationLogEntries validates migration log entries
func (vr *ValidationRunner) checkMigrationLogEntries(ctx context.Context, migrationName string, result *ValidationResult) {
	if !vr.tableExists("migration_log") {
		vr.addValidationCheck(ValidationCheck{
			CheckType:   "migration_logging",
			Name:        "migration_log_exists",
			Description: "migration_log table should exist for detailed tracking",
			Status:      ValidationStatusWarning,
			Message:     "migration_log table does not exist",
		}, result)
		return
	}
	
	// Check for rollback entries
	query := "SELECT COUNT(*) FROM migration_log WHERE migration_name = ? AND action LIKE '%rollback%'"
	var count int
	err := vr.db.QueryRowContext(ctx, query, migrationName).Scan(&count)
	
	status := ValidationStatusPass
	message := fmt.Sprintf("Rollback logging validated for %s", migrationName)
	
	if err != nil || count == 0 {
		status = ValidationStatusWarning
		message = fmt.Sprintf("No rollback log entries found for %s", migrationName)
	}
	
	vr.addValidationCheck(ValidationCheck{
		CheckType:   "migration_logging",
		Name:        "rollback_logged",
		Description: "Rollback should be logged in migration_log",
		Status:      status,
		Message:     message,
		Details:     map[string]string{"log_entries": fmt.Sprintf("%d", count)},
	}, result)
}

// columnExists checks if a column exists in a table
func (vr *ValidationRunner) columnExists(tableName, columnName string) bool {
	query := fmt.Sprintf("SELECT COUNT(*) FROM pragma_table_info('%s') WHERE name = ?", tableName)
	var count int
	err := vr.db.QueryRow(query, columnName).Scan(&count)
	return err == nil && count > 0
}