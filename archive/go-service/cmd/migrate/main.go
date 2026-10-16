package main

import (
	"context"
	"flag"
	"os"

	"go-service/internal/database"
	"go-service/internal/logging"
)

func main() {
	var (
		dbPath = flag.String("db", "", "Database file path (overrides GO_DB_PATH env var)")
		help   = flag.Bool("help", false, "Show help message")
	)
	flag.Parse()

	if *help {
		flag.Usage()
		os.Exit(0)
	}

	// Initialize structured logger for migration command
	logConfig := logging.Config{
		LogLevel: "info",
		DevMode:  true, // Output to stdout for CLI tool
	}
	logger := logging.NewStdoutLogger(logConfig)
	defer logger.Close()

	ctx := context.Background()

	// Configure database
	var config database.Config
	if *dbPath != "" {
		config = database.Config{
			Path:           *dbPath,
			MaxConnections: 5,
			AutoMigrate:    false,
		}
	} else {
		// Use environment configuration
		config = database.Config{
			Path:           os.Getenv("GO_DB_PATH"),
			MaxConnections: 5,
			AutoMigrate:    false,
		}
		if config.Path == "" {
			config.Path = "./evaluation.db"
		}
	}

	logger.InfoContext(ctx, "Initializing migration tool",
		"component", "migrate.main",
		"database_path", config.Path)

	// Create database connection
	db, err := database.NewDB(config)
	if err != nil {
		logger.ErrorContext(ctx, "Failed to create database",
			"component", "migrate.main",
			"database_path", config.Path,
			"error", err.Error())
		os.Exit(1)
	}
	defer db.Close()

	logger.InfoContext(ctx, "Running migrations on database",
		"component", "migrate.main",
		"database_path", config.Path)

	// Run migrations using the new context-aware method
	if err := db.MigrateWithContext(ctx, logger.Logger); err != nil {
		logger.ErrorContext(ctx, "Migration failed",
			"component", "migrate.main",
			"error", err.Error())
		os.Exit(1)
	}

	logger.InfoContext(ctx, "Migrations completed successfully",
		"component", "migrate.main")

	// Show applied migrations
	applied, err := db.GetAppliedMigrations()
	if err != nil {
		logger.ErrorContext(ctx, "Failed to get applied migrations",
			"component", "migrate.main",
			"error", err.Error())
		os.Exit(1)
	}

	logger.InfoContext(ctx, "Applied migrations",
		"component", "migrate.main",
		"migrations", applied,
		"count", len(applied))

	// Show database stats
	stats, err := db.GetStats()
	if err != nil {
		logger.ErrorContext(ctx, "Failed to get database stats",
			"component", "migrate.main",
			"error", err.Error())
		os.Exit(1)
	}

	logger.InfoContext(ctx, "Database statistics",
		"component", "migrate.main",
		"tables_count", stats["tables_count"],
		"results_count", stats["results_count"])
}
