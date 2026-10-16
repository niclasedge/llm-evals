package database

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

// Config holds database configuration
type Config struct {
	Path           string
	MaxConnections int
	AutoMigrate    bool
}

// DB wraps the SQL database connection
type DB struct {
	*sql.DB
	config Config
}

// NewDB creates a new database connection
func NewDB(config Config) (*DB, error) {
	// Ensure directory exists
	if err := ensureDir(filepath.Dir(config.Path)); err != nil {
		return nil, fmt.Errorf("failed to create database directory: %w", err)
	}

	// Open database connection with improved concurrency settings
	db, err := sql.Open("sqlite", config.Path+"?_foreign_keys=on&_journal_mode=WAL&_busy_timeout=5000")
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Set connection pool limits - for SQLite, limit to 1 connection for writes
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	// Test connection
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	dbWrapper := &DB{
		DB:     db,
		config: config,
	}

	// Run migrations if enabled
	if config.AutoMigrate {
		if err := dbWrapper.Migrate(); err != nil {
			return nil, fmt.Errorf("failed to run migrations: %w", err)
		}
	}

	return dbWrapper, nil
}

// NewDBFromEnv creates a database connection from environment variables
func NewDBFromEnv() (*DB, error) {
	config := Config{
		Path:           getEnvDefault("GO_DB_PATH", "./evaluation.db"),
		MaxConnections: getEnvIntDefault("GO_DB_MAX_CONNECTIONS", 10),
		AutoMigrate:    getEnvBoolDefault("GO_DB_MIGRATE", true),
	}

	return NewDB(config)
}

// Close closes the database connection
func (db *DB) Close() error {
	return db.DB.Close()
}

// Health checks database connectivity
func (db *DB) Health() error {
	return db.Ping()
}

// GetStats returns database statistics
func (db *DB) GetStats() (map[string]interface{}, error) {
	stats := db.Stats()

	var tableCount int
	err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").Scan(&tableCount)
	if err != nil {
		return nil, err
	}

	var resultCount int
	err = db.QueryRow("SELECT COUNT(*) FROM evaluation_results").Scan(&resultCount)
	if err != nil {
		// Table might not exist yet
		resultCount = 0
	}

	return map[string]interface{}{
		"open_connections":    stats.OpenConnections,
		"in_use":              stats.InUse,
		"idle":                stats.Idle,
		"wait_count":          stats.WaitCount,
		"wait_duration":       stats.WaitDuration.String(),
		"max_idle_closed":     stats.MaxIdleClosed,
		"max_lifetime_closed": stats.MaxLifetimeClosed,
		"tables_count":        tableCount,
		"results_count":       resultCount,
	}, nil
}

// ensureDir creates directory if it doesn't exist
func ensureDir(dir string) error {
	if dir == "" || dir == "." {
		return nil
	}
	return os.MkdirAll(dir, 0755)
}

// getEnvDefault returns environment variable value or default
func getEnvDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getEnvIntDefault returns environment variable as int or default
func getEnvIntDefault(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := fmt.Sscanf(value, "%d", &defaultValue); err == nil && intValue == 1 {
			return defaultValue
		}
	}
	return defaultValue
}

// getEnvBoolDefault returns environment variable as bool or default
func getEnvBoolDefault(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		switch value {
		case "true", "1", "yes":
			return true
		case "false", "0", "no":
			return false
		}
	}
	return defaultValue
}
