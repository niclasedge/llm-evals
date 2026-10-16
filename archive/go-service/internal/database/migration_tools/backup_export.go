package migration_tools

import (
	"compress/gzip"
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
)

// exportToSQL exports table data to SQL format
func (bm *BackupManager) exportToSQL(ctx context.Context, tables []string, filePath string, compress bool, metadata *BackupMetadata) error {
	var writer io.Writer
	
	file, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("failed to create backup file: %w", err)
	}
	defer file.Close()
	
	if compress {
		gzWriter := gzip.NewWriter(file)
		defer gzWriter.Close()
		writer = gzWriter
	} else {
		writer = file
	}
	
	// Write header
	fmt.Fprintf(writer, "-- Database backup created at %s\n", metadata.Timestamp.Format("2006-01-02 15:04:05"))
	fmt.Fprintf(writer, "-- Migration: %s\n", metadata.MigrationName)
	fmt.Fprintf(writer, "-- Backup ID: %s\n\n", metadata.BackupID)
	
	fmt.Fprintf(writer, "BEGIN TRANSACTION;\n\n")
	
	for _, tableName := range tables {
		if !bm.tableExists(tableName) {
			continue
		}
		
		// Get table info for metadata
		tableInfo, err := bm.getTableInfo(ctx, tableName)
		if err != nil {
			return fmt.Errorf("failed to get table info for %s: %w", tableName, err)
		}
		metadata.Tables = append(metadata.Tables, tableInfo)
		
		// Export table schema
		err = bm.exportTableSchema(ctx, tableName, writer)
		if err != nil {
			return fmt.Errorf("failed to export schema for %s: %w", tableName, err)
		}
		
		// Export table data
		err = bm.exportTableData(ctx, tableName, writer)
		if err != nil {
			return fmt.Errorf("failed to export data for %s: %w", tableName, err)
		}
		
		fmt.Fprintf(writer, "\n")
	}
	
	fmt.Fprintf(writer, "COMMIT;\n")
	
	return nil
}

// exportToJSON exports table data to JSON format
func (bm *BackupManager) exportToJSON(ctx context.Context, tables []string, filePath string, compress bool, metadata *BackupMetadata) error {
	var writer io.Writer
	
	file, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("failed to create backup file: %w", err)
	}
	defer file.Close()
	
	if compress {
		gzWriter := gzip.NewWriter(file)
		defer gzWriter.Close()
		writer = gzWriter
	} else {
		writer = file
	}
	
	backupData := map[string]interface{}{
		"metadata": metadata,
		"tables":   make(map[string]interface{}),
	}
	
	for _, tableName := range tables {
		if !bm.tableExists(tableName) {
			continue
		}
		
		// Get table info for metadata
		tableInfo, err := bm.getTableInfo(ctx, tableName)
		if err != nil {
			return fmt.Errorf("failed to get table info for %s: %w", tableName, err)
		}
		metadata.Tables = append(metadata.Tables, tableInfo)
		
		// Get table data
		tableData, err := bm.getTableDataJSON(ctx, tableName)
		if err != nil {
			return fmt.Errorf("failed to get data for %s: %w", tableName, err)
		}
		
		backupData["tables"].(map[string]interface{})[tableName] = map[string]interface{}{
			"schema": tableInfo.Schema,
			"data":   tableData,
		}
	}
	
	encoder := json.NewEncoder(writer)
	encoder.SetIndent("", "  ")
	return encoder.Encode(backupData)
}

// exportToCSV exports table data to CSV format
func (bm *BackupManager) exportToCSV(ctx context.Context, tables []string, filePath string, compress bool, metadata *BackupMetadata) error {
	var writer io.Writer
	
	file, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("failed to create backup file: %w", err)
	}
	defer file.Close()
	
	if compress {
		gzWriter := gzip.NewWriter(file)
		defer gzWriter.Close()
		writer = gzWriter
	} else {
		writer = file
	}
	
	csvWriter := csv.NewWriter(writer)
	defer csvWriter.Flush()
	
	for _, tableName := range tables {
		if !bm.tableExists(tableName) {
			continue
		}
		
		// Get table info for metadata
		tableInfo, err := bm.getTableInfo(ctx, tableName)
		if err != nil {
			return fmt.Errorf("failed to get table info for %s: %w", tableName, err)
		}
		metadata.Tables = append(metadata.Tables, tableInfo)
		
		// Write table header
		csvWriter.Write([]string{fmt.Sprintf("TABLE: %s", tableName)})
		
		// Write column headers
		var headers []string
		for _, col := range tableInfo.Schema {
			headers = append(headers, col.Name)
		}
		csvWriter.Write(headers)
		
		// Write table data
		err = bm.exportTableDataCSV(ctx, tableName, csvWriter)
		if err != nil {
			return fmt.Errorf("failed to export CSV data for %s: %w", tableName, err)
		}
		
		// Write separator
		csvWriter.Write([]string{})
	}
	
	return nil
}

// Helper methods for export

// exportTableSchema exports CREATE TABLE statement
func (bm *BackupManager) exportTableSchema(ctx context.Context, tableName string, writer io.Writer) error {
	query := "SELECT sql FROM sqlite_master WHERE type='table' AND name=?"
	var createSQL string
	
	err := bm.db.QueryRowContext(ctx, query, tableName).Scan(&createSQL)
	if err != nil {
		return fmt.Errorf("failed to get CREATE statement for %s: %w", tableName, err)
	}
	
	fmt.Fprintf(writer, "-- Table: %s\n", tableName)
	fmt.Fprintf(writer, "DROP TABLE IF EXISTS %s;\n", tableName)
	fmt.Fprintf(writer, "%s;\n\n", createSQL)
	
	return nil
}

// exportTableData exports INSERT statements for table data
func (bm *BackupManager) exportTableData(ctx context.Context, tableName string, writer io.Writer) error {
	query := fmt.Sprintf("SELECT * FROM %s", tableName)
	rows, err := bm.db.QueryContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to query table %s: %w", tableName, err)
	}
	defer rows.Close()
	
	columns, err := rows.Columns()
	if err != nil {
		return fmt.Errorf("failed to get columns for %s: %w", tableName, err)
	}
	
	fmt.Fprintf(writer, "-- Data for table: %s\n", tableName)
	
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}
		
		err := rows.Scan(valuePtrs...)
		if err != nil {
			return fmt.Errorf("failed to scan row: %w", err)
		}
		
		// Build INSERT statement
		var valueStrings []string
		for _, value := range values {
			if value == nil {
				valueStrings = append(valueStrings, "NULL")
			} else {
				switch v := value.(type) {
				case string:
					valueStrings = append(valueStrings, fmt.Sprintf("'%s'", strings.ReplaceAll(v, "'", "''")))
				case []byte:
					valueStrings = append(valueStrings, fmt.Sprintf("'%s'", strings.ReplaceAll(string(v), "'", "''")))
				default:
					valueStrings = append(valueStrings, fmt.Sprintf("%v", v))
				}
			}
		}
		
		columnList := strings.Join(columns, ", ")
		valueList := strings.Join(valueStrings, ", ")
		fmt.Fprintf(writer, "INSERT INTO %s (%s) VALUES (%s);\n", tableName, columnList, valueList)
	}
	
	return nil
}

// getTableDataJSON retrieves table data as JSON
func (bm *BackupManager) getTableDataJSON(ctx context.Context, tableName string) ([]map[string]interface{}, error) {
	query := fmt.Sprintf("SELECT * FROM %s", tableName)
	rows, err := bm.db.QueryContext(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to query table %s: %w", tableName, err)
	}
	defer rows.Close()
	
	columns, err := rows.Columns()
	if err != nil {
		return nil, fmt.Errorf("failed to get columns for %s: %w", tableName, err)
	}
	
	var result []map[string]interface{}
	
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}
		
		err := rows.Scan(valuePtrs...)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}
		
		row := make(map[string]interface{})
		for i, column := range columns {
			row[column] = values[i]
		}
		
		result = append(result, row)
	}
	
	return result, nil
}

// exportTableDataCSV exports table data to CSV writer
func (bm *BackupManager) exportTableDataCSV(ctx context.Context, tableName string, csvWriter *csv.Writer) error {
	query := fmt.Sprintf("SELECT * FROM %s", tableName)
	rows, err := bm.db.QueryContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to query table %s: %w", tableName, err)
	}
	defer rows.Close()
	
	columns, err := rows.Columns()
	if err != nil {
		return fmt.Errorf("failed to get columns for %s: %w", tableName, err)
	}
	
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}
		
		err := rows.Scan(valuePtrs...)
		if err != nil {
			return fmt.Errorf("failed to scan row: %w", err)
		}
		
		var stringValues []string
		for _, value := range values {
			if value == nil {
				stringValues = append(stringValues, "")
			} else {
				stringValues = append(stringValues, fmt.Sprintf("%v", value))
			}
		}
		
		csvWriter.Write(stringValues)
	}
	
	return nil
}

// tableExists checks if a table exists in the database
func (bm *BackupManager) tableExists(tableName string) bool {
	query := "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
	var exists int
	err := bm.db.QueryRow(query, tableName).Scan(&exists)
	return err == nil
}