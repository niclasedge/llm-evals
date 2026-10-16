package migration_tools

import (
	"bufio"
	"compress/gzip"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
)

// restoreFromSQL restores database from SQL backup file
func (bm *BackupManager) restoreFromSQL(ctx context.Context, filePath string, compressed bool, options RestoreOptions) error {
	var reader io.Reader
	
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open backup file: %w", err)
	}
	defer file.Close()
	
	if compressed {
		gzReader, err := gzip.NewReader(file)
		if err != nil {
			return fmt.Errorf("failed to create gzip reader: %w", err)
		}
		defer gzReader.Close()
		reader = gzReader
	} else {
		reader = file
	}
	
	if options.DryRun {
		bm.logger.Info("Dry run mode: would execute SQL restore", "file", filePath)
		return nil
	}
	
	// Read and execute SQL statements
	scanner := bufio.NewScanner(reader)
	var currentStatement strings.Builder
	var lineCount int
	var statementCount int
	
	tx, err := bm.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()
	
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		lineCount++
		
		// Skip comments and empty lines
		if line == "" || strings.HasPrefix(line, "--") {
			continue
		}
		
		currentStatement.WriteString(line)
		currentStatement.WriteString(" ")
		
		// Execute statement if it ends with semicolon
		if strings.HasSuffix(line, ";") {
			statement := strings.TrimSpace(currentStatement.String())
			
			// Filter statements based on options
			if bm.shouldExecuteStatement(statement, options) {
				_, err := tx.ExecContext(ctx, statement)
				if err != nil {
					return fmt.Errorf("failed to execute statement at line %d: %s\nError: %w", 
						lineCount, statement, err)
				}
				statementCount++
			}
			
			currentStatement.Reset()
		}
	}
	
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("error reading backup file: %w", err)
	}
	
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit restore transaction: %w", err)
	}
	
	bm.logger.Info("SQL restore completed",
		"file", filePath,
		"lines_processed", lineCount,
		"statements_executed", statementCount,
	)
	
	return nil
}

// restoreFromJSON restores database from JSON backup file
func (bm *BackupManager) restoreFromJSON(ctx context.Context, filePath string, compressed bool, options RestoreOptions) error {
	var reader io.Reader
	
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open backup file: %w", err)
	}
	defer file.Close()
	
	if compressed {
		gzReader, err := gzip.NewReader(file)
		if err != nil {
			return fmt.Errorf("failed to create gzip reader: %w", err)
		}
		defer gzReader.Close()
		reader = gzReader
	} else {
		reader = file
	}
	
	if options.DryRun {
		bm.logger.Info("Dry run mode: would execute JSON restore", "file", filePath)
		return nil
	}
	
	// Parse JSON backup
	var backupData map[string]interface{}
	decoder := json.NewDecoder(reader)
	err = decoder.Decode(&backupData)
	if err != nil {
		return fmt.Errorf("failed to decode JSON backup: %w", err)
	}
	
	// Extract tables data
	tablesData, ok := backupData["tables"].(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid backup format: missing tables data")
	}
	
	tx, err := bm.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()
	
	for tableName, tableInfo := range tablesData {
		// Skip if not in tables filter
		if len(options.TablesOnly) > 0 && !bm.containsString(options.TablesOnly, tableName) {
			continue
		}
		
		tableData, ok := tableInfo.(map[string]interface{})
		if !ok {
			continue
		}
		
		schema, ok := tableData["schema"].([]interface{})
		if !ok {
			continue
		}
		
		data, ok := tableData["data"].([]interface{})
		if !ok {
			continue
		}
		
		// Drop existing table if requested
		if options.DropExisting {
			_, err := tx.ExecContext(ctx, fmt.Sprintf("DROP TABLE IF EXISTS %s", tableName))
			if err != nil {
				return fmt.Errorf("failed to drop table %s: %w", tableName, err)
			}
		}
		
		// Recreate table from schema
		err := bm.recreateTableFromSchema(ctx, tx, tableName, schema)
		if err != nil {
			return fmt.Errorf("failed to recreate table %s: %w", tableName, err)
		}
		
		// Insert data
		err = bm.insertJSONData(ctx, tx, tableName, data)
		if err != nil {
			return fmt.Errorf("failed to insert data into %s: %w", tableName, err)
		}
		
		bm.logger.Info("Restored table from JSON",
			"table", tableName,
			"rows", len(data),
		)
	}
	
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit restore transaction: %w", err)
	}
	
	bm.logger.Info("JSON restore completed", "file", filePath)
	
	return nil
}

// Helper methods for restore

// shouldExecuteStatement determines if a SQL statement should be executed based on options
func (bm *BackupManager) shouldExecuteStatement(statement string, options RestoreOptions) bool {
	statement = strings.ToUpper(strings.TrimSpace(statement))
	
	// Skip DROP statements if not requested
	if strings.HasPrefix(statement, "DROP") && !options.DropExisting {
		return false
	}
	
	// Filter by table names if specified
	if len(options.TablesOnly) > 0 {
		isTableOperation := false
		for _, tableName := range options.TablesOnly {
			tablePattern := strings.ToUpper(tableName)
			if strings.Contains(statement, tablePattern) {
				isTableOperation = true
				break
			}
		}
		if !isTableOperation && (strings.HasPrefix(statement, "CREATE TABLE") || 
			strings.HasPrefix(statement, "INSERT INTO") || 
			strings.HasPrefix(statement, "DROP TABLE")) {
			return false
		}
	}
	
	return true
}

// recreateTableFromSchema recreates a table from JSON schema information
func (bm *BackupManager) recreateTableFromSchema(ctx context.Context, tx *sql.Tx, tableName string, schema []interface{}) error {
	var columns []string
	var primaryKeys []string
	
	for _, col := range schema {
		columnInfo, ok := col.(map[string]interface{})
		if !ok {
			continue
		}
		
		name, _ := columnInfo["name"].(string)
		colType, _ := columnInfo["type"].(string)
		notNull, _ := columnInfo["not_null"].(bool)
		primaryKey, _ := columnInfo["primary_key"].(bool)
		defaultValue, _ := columnInfo["default_value"].(string)
		
		if name == "" || colType == "" {
			continue
		}
		
		columnDef := fmt.Sprintf("%s %s", name, colType)
		
		if primaryKey {
			primaryKeys = append(primaryKeys, name)
		}
		
		if notNull {
			columnDef += " NOT NULL"
		}
		
		if defaultValue != "" {
			columnDef += fmt.Sprintf(" DEFAULT %s", defaultValue)
		}
		
		columns = append(columns, columnDef)
	}
	
	if len(primaryKeys) > 0 {
		columns = append(columns, fmt.Sprintf("PRIMARY KEY (%s)", strings.Join(primaryKeys, ", ")))
	}
	
	createSQL := fmt.Sprintf("CREATE TABLE %s (%s)", tableName, strings.Join(columns, ", "))
	
	_, err := tx.ExecContext(ctx, createSQL)
	return err
}

// insertJSONData inserts data from JSON into a table
func (bm *BackupManager) insertJSONData(ctx context.Context, tx *sql.Tx, tableName string, data []interface{}) error {
	if len(data) == 0 {
		return nil
	}
	
	// Get first row to determine columns
	firstRow, ok := data[0].(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid row data format")
	}
	
	var columns []string
	for column := range firstRow {
		// Skip backup_timestamp column if it exists
		if column != "backup_timestamp" {
			columns = append(columns, column)
		}
	}
	
	if len(columns) == 0 {
		return nil
	}
	
	// Prepare INSERT statement
	placeholders := make([]string, len(columns))
	for i := range placeholders {
		placeholders[i] = "?"
	}
	
	insertSQL := fmt.Sprintf("INSERT INTO %s (%s) VALUES (%s)",
		tableName,
		strings.Join(columns, ", "),
		strings.Join(placeholders, ", "))
	
	stmt, err := tx.PrepareContext(ctx, insertSQL)
	if err != nil {
		return fmt.Errorf("failed to prepare insert statement: %w", err)
	}
	defer stmt.Close()
	
	// Insert each row
	for _, row := range data {
		rowData, ok := row.(map[string]interface{})
		if !ok {
			continue
		}
		
		values := make([]interface{}, len(columns))
		for i, column := range columns {
			values[i] = rowData[column]
		}
		
		_, err := stmt.ExecContext(ctx, values...)
		if err != nil {
			return fmt.Errorf("failed to insert row: %w", err)
		}
	}
	
	return nil
}

// containsString checks if a slice contains a string
func (bm *BackupManager) containsString(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}