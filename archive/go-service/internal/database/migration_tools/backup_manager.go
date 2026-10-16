package migration_tools

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log/slog"
	"os"
	"path/filepath"
	"time"

	"go-service/internal/logging"
)

// BackupManager handles data preservation for migration rollbacks
type BackupManager struct {
	db         *sql.DB
	backupPath string
	logger     *slog.Logger
}

// BackupConfig defines backup operation configuration
type BackupConfig struct {
	IncludeData   bool     `json:"include_data"`
	Tables        []string `json:"tables,omitempty"`
	ExportFormat  string   `json:"export_format"` // sql, json, csv
	Compression   bool     `json:"compression"`
	RetentionDays int      `json:"retention_days"`
}

// BackupResult contains information about a backup operation
type BackupResult struct {
	Success       bool              `json:"success"`
	BackupID      string            `json:"backup_id"`
	Timestamp     time.Time         `json:"timestamp"`
	Tables        map[string]int    `json:"tables"` // table_name -> row_count
	FilePath      string            `json:"file_path"`
	FileSize      int64             `json:"file_size"`
	ErrorMessage  string            `json:"error_message,omitempty"`
	Metadata      map[string]string `json:"metadata,omitempty"`
}

// BackupMetadata contains detailed information about backed up data
type BackupMetadata struct {
	BackupID      string            `json:"backup_id"`
	Timestamp     time.Time         `json:"timestamp"`
	MigrationName string            `json:"migration_name"`
	Tables        []TableBackupInfo `json:"tables"`
	Config        BackupConfig      `json:"config"`
	DatabaseInfo  DatabaseInfo      `json:"database_info"`
}

// TableBackupInfo contains information about a backed up table
type TableBackupInfo struct {
	TableName string            `json:"table_name"`
	RowCount  int               `json:"row_count"`
	Schema    []ColumnInfo      `json:"schema"`
	Indexes   []string          `json:"indexes"`
	Metadata  map[string]string `json:"metadata,omitempty"`
}

// ColumnInfo describes a table column
type ColumnInfo struct {
	Name         string `json:"name"`
	Type         string `json:"type"`
	NotNull      bool   `json:"not_null"`
	DefaultValue string `json:"default_value,omitempty"`
	PrimaryKey   bool   `json:"primary_key"`
}

// DatabaseInfo contains database metadata
type DatabaseInfo struct {
	Version     string `json:"version"`
	PageSize    int    `json:"page_size"`
	UserVersion int    `json:"user_version"`
}

// NewBackupManager creates a new BackupManager instance
func NewBackupManager(db *sql.DB, backupPath string, logger *slog.Logger) *BackupManager {
	if logger == nil {
		logger = logging.NewDefaultLogger().Logger
	}
	
	// Ensure backup directory exists
	os.MkdirAll(backupPath, 0755)
	
	return &BackupManager{
		db:         db,
		backupPath: backupPath,
		logger:     logger,
	}
}

// CreateBackup creates a comprehensive backup of specified tables
func (bm *BackupManager) CreateBackup(ctx context.Context, migrationName string, config BackupConfig) (*BackupResult, error) {
	correlationID := logging.NewCorrelationID()
	ctx = logging.WithCorrelationID(ctx, correlationID)
	
	backupID := fmt.Sprintf("%s_%s_%d", migrationName, config.ExportFormat, time.Now().Unix())
	
	result := &BackupResult{
		BackupID:  backupID,
		Timestamp: time.Now(),
		Tables:    make(map[string]int),
		Metadata:  make(map[string]string),
	}
	
	logger := logging.LogWithContext(ctx, bm.logger)
	logger.Info("Starting backup operation",
		"component", "migration_tools.backup_manager",
		"backup_id", backupID,
		"migration", migrationName,
		"format", config.ExportFormat,
	)
	
	// Determine tables to backup
	tables := config.Tables
	if len(tables) == 0 {
		// Auto-detect tables based on migration
		tables = bm.getTablesForMigration(migrationName)
	}
	
	// Create backup metadata
	metadata := &BackupMetadata{
		BackupID:      backupID,
		Timestamp:     result.Timestamp,
		MigrationName: migrationName,
		Config:        config,
		Tables:        make([]TableBackupInfo, 0, len(tables)),
	}
	
	// Get database info
	dbInfo, err := bm.getDatabaseInfo(ctx)
	if err != nil {
		logger.Warn("Failed to get database info", "error", err)
	} else {
		metadata.DatabaseInfo = dbInfo
	}
	
	// Create backup file
	backupFileName := fmt.Sprintf("%s.%s", backupID, config.ExportFormat)
	if config.Compression {
		backupFileName += ".gz"
	}
	
	backupFilePath := filepath.Join(bm.backupPath, backupFileName)
	
	// Export data based on format
	switch config.ExportFormat {
	case "sql":
		err = bm.exportToSQL(ctx, tables, backupFilePath, config.Compression, metadata)
	case "json":
		err = bm.exportToJSON(ctx, tables, backupFilePath, config.Compression, metadata)
	case "csv":
		err = bm.exportToCSV(ctx, tables, backupFilePath, config.Compression, metadata)
	default:
		err = fmt.Errorf("unsupported export format: %s", config.ExportFormat)
	}
	
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("Export failed: %v", err)
		logger.Error("Backup export failed",
			"error", err,
			"backup_id", backupID,
			"format", config.ExportFormat,
		)
		return result, err
	}
	
	// Get file size
	if stat, err := os.Stat(backupFilePath); err == nil {
		result.FileSize = stat.Size()
	}
	
	// Save metadata
	metadataPath := filepath.Join(bm.backupPath, fmt.Sprintf("%s_metadata.json", backupID))
	if err := bm.saveMetadata(metadata, metadataPath); err != nil {
		logger.Warn("Failed to save backup metadata", "error", err)
	}
	
	// Populate result
	result.Success = true
	result.FilePath = backupFilePath
	result.Metadata["metadata_file"] = metadataPath
	
	// Collect table row counts
	for _, tableInfo := range metadata.Tables {
		result.Tables[tableInfo.TableName] = tableInfo.RowCount
	}
	
	logger.Info("Backup operation completed successfully",
		"backup_id", backupID,
		"file_path", backupFilePath,
		"file_size", result.FileSize,
		"tables_backed_up", len(result.Tables),
	)
	
	// Clean up old backups if retention policy is set
	if config.RetentionDays > 0 {
		go bm.cleanupOldBackups(config.RetentionDays)
	}
	
	return result, nil
}

// RestoreFromBackup restores data from a backup file
func (bm *BackupManager) RestoreFromBackup(ctx context.Context, backupID string, options RestoreOptions) error {
	logger := logging.LogWithContext(ctx, bm.logger)
	
	// Load backup metadata
	metadataPath := filepath.Join(bm.backupPath, fmt.Sprintf("%s_metadata.json", backupID))
	metadata, err := bm.loadMetadata(metadataPath)
	if err != nil {
		return fmt.Errorf("failed to load backup metadata: %w", err)
	}
	
	logger.Info("Starting restore operation",
		"backup_id", backupID,
		"migration", metadata.MigrationName,
		"tables", len(metadata.Tables),
	)
	
	// Determine backup file
	backupFileName := fmt.Sprintf("%s.%s", backupID, metadata.Config.ExportFormat)
	if metadata.Config.Compression {
		backupFileName += ".gz"
	}
	backupFilePath := filepath.Join(bm.backupPath, backupFileName)
	
	// Restore based on format
	switch metadata.Config.ExportFormat {
	case "sql":
		err = bm.restoreFromSQL(ctx, backupFilePath, metadata.Config.Compression, options)
	case "json":
		err = bm.restoreFromJSON(ctx, backupFilePath, metadata.Config.Compression, options)
	default:
		err = fmt.Errorf("restore from %s format not implemented", metadata.Config.ExportFormat)
	}
	
	if err != nil {
		logger.Error("Restore operation failed",
			"error", err,
			"backup_id", backupID,
		)
		return err
	}
	
	logger.Info("Restore operation completed successfully",
		"backup_id", backupID,
	)
	
	return nil
}

// RestoreOptions defines options for restore operations
type RestoreOptions struct {
	DropExisting     bool     `json:"drop_existing"`
	IgnoreConstraints bool    `json:"ignore_constraints"`
	TablesOnly       []string `json:"tables_only,omitempty"`
	DryRun          bool     `json:"dry_run"`
}

// Helper methods

// getTablesForMigration returns the tables affected by a migration
func (bm *BackupManager) getTablesForMigration(migrationName string) []string {
	switch migrationName {
	case "003_test_executions":
		return []string{"test_executions"}
	case "004_test_results_categories":
		return []string{"test_results", "test_categories"}
	case "005_seed_test_categories":
		return []string{"test_categories"}
	default:
		// Return all test-related tables
		return []string{"test_executions", "test_results", "test_categories"}
	}
}

// getDatabaseInfo retrieves database metadata
func (bm *BackupManager) getDatabaseInfo(ctx context.Context) (DatabaseInfo, error) {
	var info DatabaseInfo
	
	// Get SQLite version
	err := bm.db.QueryRowContext(ctx, "SELECT sqlite_version()").Scan(&info.Version)
	if err != nil {
		return info, err
	}
	
	// Get page size
	err = bm.db.QueryRowContext(ctx, "PRAGMA page_size").Scan(&info.PageSize)
	if err != nil {
		return info, err
	}
	
	// Get user version
	err = bm.db.QueryRowContext(ctx, "PRAGMA user_version").Scan(&info.UserVersion)
	if err != nil {
		return info, err
	}
	
	return info, nil
}

// getTableInfo retrieves detailed information about a table
func (bm *BackupManager) getTableInfo(ctx context.Context, tableName string) (TableBackupInfo, error) {
	info := TableBackupInfo{
		TableName: tableName,
		Schema:    make([]ColumnInfo, 0),
		Indexes:   make([]string, 0),
		Metadata:  make(map[string]string),
	}
	
	// Get row count
	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM %s", tableName)
	err := bm.db.QueryRowContext(ctx, countQuery).Scan(&info.RowCount)
	if err != nil {
		return info, fmt.Errorf("failed to get row count for %s: %w", tableName, err)
	}
	
	// Get table schema
	schemaQuery := fmt.Sprintf("PRAGMA table_info(%s)", tableName)
	rows, err := bm.db.QueryContext(ctx, schemaQuery)
	if err != nil {
		return info, fmt.Errorf("failed to get schema for %s: %w", tableName, err)
	}
	defer rows.Close()
	
	for rows.Next() {
		var cid int
		var column ColumnInfo
		var nullable int
		
		err := rows.Scan(&cid, &column.Name, &column.Type, &nullable, &column.DefaultValue, &column.PrimaryKey)
		if err != nil {
			return info, fmt.Errorf("failed to scan column info: %w", err)
		}
		
		column.NotNull = nullable == 1
		info.Schema = append(info.Schema, column)
	}
	
	// Get indexes
	indexQuery := fmt.Sprintf("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='%s'", tableName)
	indexRows, err := bm.db.QueryContext(ctx, indexQuery)
	if err == nil {
		defer indexRows.Close()
		for indexRows.Next() {
			var indexName string
			if err := indexRows.Scan(&indexName); err == nil {
				info.Indexes = append(info.Indexes, indexName)
			}
		}
	}
	
	return info, nil
}

// saveMetadata saves backup metadata to a JSON file
func (bm *BackupManager) saveMetadata(metadata *BackupMetadata, filePath string) error {
	data, err := json.MarshalIndent(metadata, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal metadata: %w", err)
	}
	
	return ioutil.WriteFile(filePath, data, 0644)
}

// loadMetadata loads backup metadata from a JSON file
func (bm *BackupManager) loadMetadata(filePath string) (*BackupMetadata, error) {
	data, err := ioutil.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read metadata file: %w", err)
	}
	
	var metadata BackupMetadata
	err = json.Unmarshal(data, &metadata)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal metadata: %w", err)
	}
	
	return &metadata, nil
}

// cleanupOldBackups removes backup files older than the retention period
func (bm *BackupManager) cleanupOldBackups(retentionDays int) {
	cutoff := time.Now().AddDate(0, 0, -retentionDays)
	
	files, err := ioutil.ReadDir(bm.backupPath)
	if err != nil {
		bm.logger.Error("Failed to list backup directory", "error", err)
		return
	}
	
	for _, file := range files {
		if file.ModTime().Before(cutoff) {
			filePath := filepath.Join(bm.backupPath, file.Name())
			if err := os.Remove(filePath); err != nil {
				bm.logger.Warn("Failed to remove old backup file",
					"file", filePath,
					"error", err,
				)
			} else {
				bm.logger.Info("Removed old backup file", "file", filePath)
			}
		}
	}
}

