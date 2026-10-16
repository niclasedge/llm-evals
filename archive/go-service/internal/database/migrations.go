package database

import (
	"context"
	"embed"
	"fmt"
	"io/fs"
	"log/slog"
	"path/filepath"
	"sort"
	"strings"
)

//go:embed migrations/*.sql
var migrationFiles embed.FS

// Migrate runs database migrations
func (db *DB) Migrate() error {
	return db.MigrateWithContext(context.Background(), slog.Default())
}

// MigrateWithContext runs database migrations with context and logger
func (db *DB) MigrateWithContext(ctx context.Context, logger *slog.Logger) error {
	logger.InfoContext(ctx, "Starting database migrations",
		"component", "database.migrations")

	// Create migrations table if it doesn't exist
	if err := db.createMigrationsTable(); err != nil {
		logger.ErrorContext(ctx, "Failed to create migrations table",
			"component", "database.migrations",
			"error", err.Error())
		return fmt.Errorf("failed to create migrations table: %w", err)
	}

	// Get migration files
	migrations, err := db.getMigrationFiles()
	if err != nil {
		logger.ErrorContext(ctx, "Failed to get migration files",
			"component", "database.migrations",
			"error", err.Error())
		return fmt.Errorf("failed to get migration files: %w", err)
	}

	logger.InfoContext(ctx, "Found migration files",
		"component", "database.migrations",
		"count", len(migrations))

	// Run each migration
	for _, migration := range migrations {
		if err := db.runMigrationWithContext(ctx, logger, migration); err != nil {
			logger.ErrorContext(ctx, "Failed to run migration",
				"component", "database.migrations",
				"migration", migration.Name,
				"error", err.Error())
			return fmt.Errorf("failed to run migration %s: %w", migration.Name, err)
		}
	}

	logger.InfoContext(ctx, "Database migrations completed successfully",
		"component", "database.migrations",
		"total_migrations", len(migrations))
	return nil
}

// Migration represents a database migration
type Migration struct {
	Name    string
	Content string
}

// createMigrationsTable creates the migrations tracking table
func (db *DB) createMigrationsTable() error {
	query := `
		CREATE TABLE IF NOT EXISTS schema_migrations (
			version TEXT PRIMARY KEY,
			applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
		)
	`
	_, err := db.Exec(query)
	return err
}

// getMigrationFiles reads and sorts migration files
func (db *DB) getMigrationFiles() ([]Migration, error) {
	var migrations []Migration

	err := fs.WalkDir(migrationFiles, ".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if d.IsDir() || !strings.HasSuffix(path, ".sql") {
			return nil
		}

		content, err := migrationFiles.ReadFile(path)
		if err != nil {
			return fmt.Errorf("failed to read migration file %s: %w", path, err)
		}

		migrations = append(migrations, Migration{
			Name:    filepath.Base(path),
			Content: string(content),
		})

		return nil
	})

	if err != nil {
		return nil, err
	}

	// Sort migrations by name to ensure proper order
	sort.Slice(migrations, func(i, j int) bool {
		return migrations[i].Name < migrations[j].Name
	})

	return migrations, nil
}

// runMigration executes a single migration if not already applied
func (db *DB) runMigration(migration Migration) error {
	return db.runMigrationWithContext(context.Background(), slog.Default(), migration)
}

// runMigrationWithContext executes a single migration if not already applied with context and logger
func (db *DB) runMigrationWithContext(ctx context.Context, logger *slog.Logger, migration Migration) error {
	// Check if migration already applied
	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM schema_migrations WHERE version = ?", migration.Name).Scan(&count)
	if err != nil {
		logger.ErrorContext(ctx, "Failed to check migration status",
			"component", "database.migrations",
			"migration", migration.Name,
			"error", err.Error())
		return err
	}

	if count > 0 {
		logger.InfoContext(ctx, "Migration already applied, skipping",
			"component", "database.migrations",
			"migration", migration.Name)
		return nil
	}

	// Begin transaction
	tx, err := db.Begin()
	if err != nil {
		logger.ErrorContext(ctx, "Failed to begin transaction for migration",
			"component", "database.migrations",
			"migration", migration.Name,
			"error", err.Error())
		return err
	}
	defer tx.Rollback()

	// Execute migration
	logger.InfoContext(ctx, "Applying migration",
		"component", "database.migrations",
		"migration", migration.Name)

	if _, err := tx.Exec(migration.Content); err != nil {
		logger.ErrorContext(ctx, "Failed to execute migration SQL",
			"component", "database.migrations",
			"migration", migration.Name,
			"error", err.Error())
		return fmt.Errorf("failed to execute migration SQL: %w", err)
	}

	// Record migration as applied
	if _, err := tx.Exec("INSERT INTO schema_migrations (version) VALUES (?)", migration.Name); err != nil {
		logger.ErrorContext(ctx, "Failed to record migration",
			"component", "database.migrations",
			"migration", migration.Name,
			"error", err.Error())
		return fmt.Errorf("failed to record migration: %w", err)
	}

	// Commit transaction
	if err := tx.Commit(); err != nil {
		logger.ErrorContext(ctx, "Failed to commit migration",
			"component", "database.migrations",
			"migration", migration.Name,
			"error", err.Error())
		return fmt.Errorf("failed to commit migration: %w", err)
	}

	logger.InfoContext(ctx, "Migration applied successfully",
		"component", "database.migrations",
		"migration", migration.Name)
	return nil
}

// RollbackMigration removes a migration (for testing purposes)
func (db *DB) RollbackMigration(migrationName string) error {
	_, err := db.Exec("DELETE FROM schema_migrations WHERE version = ?", migrationName)
	return err
}

// GetAppliedMigrations returns list of applied migrations
func (db *DB) GetAppliedMigrations() ([]string, error) {
	rows, err := db.Query("SELECT version FROM schema_migrations ORDER BY applied_at")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var migrations []string
	for rows.Next() {
		var version string
		if err := rows.Scan(&version); err != nil {
			return nil, err
		}
		migrations = append(migrations, version)
	}

	return migrations, rows.Err()
}
