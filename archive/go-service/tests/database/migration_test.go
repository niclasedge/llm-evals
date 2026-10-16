package database

import (
	"os"
	"path/filepath"
	"testing"

	"go-service/internal/database"
)

func TestMigrations(t *testing.T) {
	// Create temporary database
	tempDir := t.TempDir()
	dbPath := filepath.Join(tempDir, "test_migrations.db")

	config := database.Config{
		Path:           dbPath,
		MaxConnections: 5,
		AutoMigrate:    false, // We'll test manual migration
	}

	db, err := database.NewDB(config)
	if err != nil {
		t.Fatalf("Failed to create database: %v", err)
	}
	defer db.Close()

	// Test migration
	if err := db.Migrate(); err != nil {
		t.Fatalf("Failed to run migrations: %v", err)
	}

	// Check that tables were created
	tables := []string{"evaluation_results", "evaluation_sessions", "performance_metrics", "model_performance_summary"}
	for _, table := range tables {
		var count int
		err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", table).Scan(&count)
		if err != nil {
			t.Fatalf("Failed to check for table %s: %v", table, err)
		}
		if count != 1 {
			t.Errorf("Table %s was not created", table)
		}
	}

	// Test that migrations table exists and has entries
	var migrationCount int
	err = db.QueryRow("SELECT COUNT(*) FROM schema_migrations").Scan(&migrationCount)
	if err != nil {
		t.Fatalf("Failed to query schema_migrations: %v", err)
	}
	if migrationCount == 0 {
		t.Error("No migrations were recorded")
	}

	// Test that running migrations again is idempotent
	if err := db.Migrate(); err != nil {
		t.Fatalf("Failed to run migrations second time: %v", err)
	}

	// Check that migration count didn't increase
	var newMigrationCount int
	err = db.QueryRow("SELECT COUNT(*) FROM schema_migrations").Scan(&newMigrationCount)
	if err != nil {
		t.Fatalf("Failed to query schema_migrations after second run: %v", err)
	}
	if newMigrationCount != migrationCount {
		t.Errorf("Migration count changed from %d to %d on second run", migrationCount, newMigrationCount)
	}
}

func TestMigrationRollback(t *testing.T) {
	// Create temporary database
	tempDir := t.TempDir()
	dbPath := filepath.Join(tempDir, "test_rollback.db")

	config := database.Config{
		Path:           dbPath,
		MaxConnections: 5,
		AutoMigrate:    true,
	}

	db, err := database.NewDB(config)
	if err != nil {
		t.Fatalf("Failed to create database: %v", err)
	}
	defer db.Close()

	// Get applied migrations
	applied, err := db.GetAppliedMigrations()
	if err != nil {
		t.Fatalf("Failed to get applied migrations: %v", err)
	}

	if len(applied) == 0 {
		t.Fatal("No migrations were applied")
	}

	// Test rollback of last migration
	lastMigration := applied[len(applied)-1]
	if err := db.RollbackMigration(lastMigration); err != nil {
		t.Fatalf("Failed to rollback migration %s: %v", lastMigration, err)
	}

	// Check that migration was removed from tracking
	newApplied, err := db.GetAppliedMigrations()
	if err != nil {
		t.Fatalf("Failed to get applied migrations after rollback: %v", err)
	}

	found := false
	for _, migration := range newApplied {
		if migration == lastMigration {
			found = true
			break
		}
	}

	if found {
		t.Errorf("Migration %s was not rolled back", lastMigration)
	}
}

func TestDatabaseFromEnv(t *testing.T) {
	// Set environment variables
	tempDir := t.TempDir()
	dbPath := filepath.Join(tempDir, "env_test.db")

	os.Setenv("GO_DB_PATH", dbPath)
	os.Setenv("GO_DB_MAX_CONNECTIONS", "15")
	os.Setenv("GO_DB_MIGRATE", "true")

	defer func() {
		os.Unsetenv("GO_DB_PATH")
		os.Unsetenv("GO_DB_MAX_CONNECTIONS")
		os.Unsetenv("GO_DB_MIGRATE")
	}()

	// Create database from environment
	db, err := database.NewDBFromEnv()
	if err != nil {
		t.Fatalf("Failed to create database from env: %v", err)
	}
	defer db.Close()

	// Test that database was created and migrated
	stats, err := db.GetStats()
	if err != nil {
		t.Fatalf("Failed to get database stats: %v", err)
	}

	if stats["tables_count"].(int) == 0 {
		t.Error("No tables were created")
	}

	// Check that the database file exists
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		t.Error("Database file was not created")
	}
}
