package migration_tools

import (
	"context"
	"database/sql"
	"fmt"
	"io/ioutil"
	"log/slog"
	"path/filepath"
	"strings"

	"go-service/internal/logging"
)

// RollbackManager handles database migration rollbacks with comprehensive logging and validation
type RollbackManager struct {
	db             *sql.DB
	migrationsPath string
	logger         *slog.Logger
}

// RollbackResult contains the results of a rollback operation
type RollbackResult struct {
	Success       bool     `json:"success"`
	MigrationName string   `json:"migration_name"`
	BackupTables  []string `json:"backup_tables"`
	ErrorMessage  string   `json:"error_message,omitempty"`
	RecoveryInfo  string   `json:"recovery_info,omitempty"`
	ValidationResults map[string]string `json:"validation_results,omitempty"`
}

// NewRollbackManager creates a new RollbackManager instance
func NewRollbackManager(db *sql.DB, migrationsPath string, logger *slog.Logger) *RollbackManager {
	if logger == nil {
		logger = logging.NewDefaultLogger().Logger
	}
	
	return &RollbackManager{
		db:             db,
		migrationsPath: migrationsPath,
		logger:         logger,
	}
}

// RollbackMigration performs a complete rollback of a specific migration
func (rm *RollbackManager) RollbackMigration(ctx context.Context, migrationName string) (*RollbackResult, error) {
	correlationID := logging.NewCorrelationID()
	ctx = logging.WithCorrelationID(ctx, correlationID)
	
	result := &RollbackResult{
		MigrationName: migrationName,
		BackupTables:  []string{},
		ValidationResults: make(map[string]string),
	}
	
	logger := logging.LogWithContext(ctx, rm.logger)
	logger.Info("Starting migration rollback",
		"component", "migration_tools.rollback_manager",
		"migration", migrationName,
		"correlation_id", correlationID,
	)
	
	// Load rollback script
	rollbackScript, err := rm.loadRollbackScript(migrationName)
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("Failed to load rollback script: %v", err)
		logger.Error("Failed to load rollback script",
			"error", err,
			"migration", migrationName,
		)
		return result, err
	}
	
	// Create backup before rollback
	backupTables, err := rm.createDataBackup(ctx, migrationName)
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("Failed to create backup: %v", err)
		logger.Error("Failed to create backup",
			"error", err,
			"migration", migrationName,
		)
		return result, err
	}
	result.BackupTables = backupTables
	
	// Execute rollback in transaction
	tx, err := rm.db.BeginTx(ctx, nil)
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("Failed to begin transaction: %v", err)
		logger.Error("Failed to begin transaction", "error", err)
		return result, err
	}
	defer tx.Rollback()
	
	// Execute rollback script
	_, err = tx.ExecContext(ctx, rollbackScript)
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("Rollback script execution failed: %v", err)
		logger.Error("Rollback script failed",
			"error", err,
			"migration", migrationName,
		)
		return result, err
	}
	
	// Commit rollback
	if err := tx.Commit(); err != nil {
		result.ErrorMessage = fmt.Sprintf("Failed to commit rollback: %v", err)
		logger.Error("Failed to commit rollback", "error", err)
		return result, err
	}
	
	// Validate rollback
	validationResults, err := rm.validateRollback(ctx, migrationName)
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("Rollback validation failed: %v", err)
		result.RecoveryInfo = rm.generateRecoveryInfo(migrationName, backupTables)
		result.ValidationResults = validationResults
		logger.Error("Rollback validation failed",
			"error", err,
			"migration", migrationName,
			"validation_results", validationResults,
		)
		return result, err
	}
	
	result.Success = true
	result.ValidationResults = validationResults
	
	logger.Info("Migration rollback completed successfully",
		"migration", migrationName,
		"backup_tables", backupTables,
		"validation_results", validationResults,
	)
	
	return result, nil
}

// createDataBackup creates backup tables for the migration data
func (rm *RollbackManager) createDataBackup(ctx context.Context, migrationName string) ([]string, error) {
	var backupTables []string
	logger := logging.LogWithContext(ctx, rm.logger)
	
	// Migration-specific backup logic
	switch migrationName {
	case "003_test_executions":
		if rm.tableExists("test_executions") {
			err := rm.backupTable(ctx, "test_executions")
			if err != nil {
				return nil, err
			}
			backupTables = append(backupTables, "test_executions_backup")
			logger.Info("Created backup for test_executions table")
		}
		
	case "004_test_results_categories":
		if rm.tableExists("test_results") {
			err := rm.backupTable(ctx, "test_results")
			if err != nil {
				return nil, err
			}
			backupTables = append(backupTables, "test_results_backup")
			logger.Info("Created backup for test_results table")
		}
		
		if rm.tableExists("test_categories") {
			err := rm.backupTable(ctx, "test_categories")
			if err != nil {
				return nil, err
			}
			backupTables = append(backupTables, "test_categories_backup")
			logger.Info("Created backup for test_categories table")
		}
		
	case "005_seed_test_categories":
		// For seed data, we only need to backup if categories exist
		if rm.tableExists("test_categories") {
			count, err := rm.getTableRowCount("test_categories")
			if err == nil && count > 0 {
				err := rm.backupTable(ctx, "test_categories")
				if err != nil {
					return nil, err
				}
				backupTables = append(backupTables, "test_categories_backup")
				logger.Info("Created backup for test_categories seed data")
			}
		}
	}
	
	return backupTables, nil
}

// backupTable creates a backup copy of the specified table
func (rm *RollbackManager) backupTable(ctx context.Context, tableName string) error {
	backupTableName := tableName + "_backup"
	
	// Drop existing backup if present
	dropQuery := fmt.Sprintf("DROP TABLE IF EXISTS %s", backupTableName)
	if _, err := rm.db.ExecContext(ctx, dropQuery); err != nil {
		return fmt.Errorf("failed to drop existing backup table %s: %w", backupTableName, err)
	}
	
	// Create backup table
	createQuery := fmt.Sprintf(`
		CREATE TABLE %s AS 
		SELECT *, CURRENT_TIMESTAMP as backup_timestamp 
		FROM %s
	`, backupTableName, tableName)
	
	_, err := rm.db.ExecContext(ctx, createQuery)
	if err != nil {
		return fmt.Errorf("failed to create backup table %s: %w", backupTableName, err)
	}
	
	return nil
}

// validateRollback executes validation checks to verify rollback completion
func (rm *RollbackManager) validateRollback(ctx context.Context, migrationName string) (map[string]string, error) {
	validationResults := make(map[string]string)
	
	// Load and execute validation script
	validationScript, err := rm.loadValidationScript(migrationName)
	if err != nil {
		// If no specific validation script, use generic validation
		return rm.performGenericValidation(ctx, migrationName)
	}
	
	rows, err := rm.db.QueryContext(ctx, validationScript)
	if err != nil {
		return validationResults, fmt.Errorf("validation query failed: %w", err)
	}
	defer rows.Close()
	
	// Process validation results
	for rows.Next() {
		var checkType, status string
		if err := rows.Scan(&checkType, &status); err != nil {
			return validationResults, fmt.Errorf("failed to scan validation result: %w", err)
		}
		
		validationResults[checkType] = status
		
		if strings.Contains(status, "ERROR") {
			return validationResults, fmt.Errorf("validation failed for %s: %s", checkType, status)
		}
	}
	
	return validationResults, nil
}

// performGenericValidation performs basic validation checks
func (rm *RollbackManager) performGenericValidation(ctx context.Context, migrationName string) (map[string]string, error) {
	results := make(map[string]string)
	
	switch migrationName {
	case "003_test_executions":
		if rm.tableExists("test_executions") {
			results["table_removal"] = "ERROR: test_executions table still exists"
		} else {
			results["table_removal"] = "SUCCESS: test_executions table removed"
		}
		
		if rm.tableExists("test_executions_backup") {
			results["backup_verification"] = "SUCCESS: test_executions_backup table exists"
		} else {
			results["backup_verification"] = "WARNING: test_executions_backup table not found"
		}
		
	case "004_test_results_categories":
		tablesRemoved := true
		if rm.tableExists("test_results") {
			results["test_results_removal"] = "ERROR: test_results table still exists"
			tablesRemoved = false
		} else {
			results["test_results_removal"] = "SUCCESS: test_results table removed"
		}
		
		if rm.tableExists("test_categories") {
			results["test_categories_removal"] = "ERROR: test_categories table still exists"
			tablesRemoved = false
		} else {
			results["test_categories_removal"] = "SUCCESS: test_categories table removed"
		}
		
		if tablesRemoved {
			results["table_removal"] = "SUCCESS: All tables removed"
		} else {
			results["table_removal"] = "ERROR: Some tables still exist"
		}
		
	case "005_seed_test_categories":
		count, err := rm.getSeedCategoryCount()
		if err != nil {
			results["seed_data_removal"] = fmt.Sprintf("ERROR: Failed to check seed data: %v", err)
		} else if count == 0 {
			results["seed_data_removal"] = "SUCCESS: All seed categories removed"
		} else {
			results["seed_data_removal"] = fmt.Sprintf("WARNING: %d seed categories remain", count)
		}
	}
	
	return results, nil
}

// Helper methods

// tableExists checks if a table exists in the database
func (rm *RollbackManager) tableExists(tableName string) bool {
	query := "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
	var exists int
	err := rm.db.QueryRow(query, tableName).Scan(&exists)
	return err == nil
}

// getTableRowCount returns the number of rows in a table
func (rm *RollbackManager) getTableRowCount(tableName string) (int, error) {
	query := fmt.Sprintf("SELECT COUNT(*) FROM %s", tableName)
	var count int
	err := rm.db.QueryRow(query).Scan(&count)
	return count, err
}

// getSeedCategoryCount returns the count of seed categories that should have been removed
func (rm *RollbackManager) getSeedCategoryCount() (int, error) {
	if !rm.tableExists("test_categories") {
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
	err := rm.db.QueryRow(query).Scan(&count)
	return count, err
}

// loadRollbackScript loads the rollback SQL script for the migration
func (rm *RollbackManager) loadRollbackScript(migrationName string) (string, error) {
	scriptPath := filepath.Join(rm.migrationsPath, "down", migrationName+".sql")
	content, err := ioutil.ReadFile(scriptPath)
	if err != nil {
		return "", fmt.Errorf("failed to read rollback script %s: %w", scriptPath, err)
	}
	return string(content), nil
}

// loadValidationScript loads the validation SQL script for the migration
func (rm *RollbackManager) loadValidationScript(migrationName string) (string, error) {
	scriptPath := filepath.Join(rm.migrationsPath, "rollback", "validation_checks.sql")
	content, err := ioutil.ReadFile(scriptPath)
	if err != nil {
		return "", fmt.Errorf("failed to read validation script %s: %w", scriptPath, err)
	}
	return string(content), nil
}

// generateRecoveryInfo creates recovery instructions for failed rollbacks
func (rm *RollbackManager) generateRecoveryInfo(migrationName string, backupTables []string) string {
	info := fmt.Sprintf("Recovery instructions for failed rollback of %s:\n", migrationName)
	info += "1. Check migration_log table for detailed error information\n"
	info += "2. Verify backup tables exist and contain expected data:\n"
	
	for _, table := range backupTables {
		info += fmt.Sprintf("   - %s\n", table)
	}
	
	info += "3. Use recovery scripts in migrations/rollback/recovery_scripts.sql\n"
	info += "4. Run validation checks after recovery\n"
	info += "5. Consider manual intervention if automated recovery fails\n"
	
	return info
}