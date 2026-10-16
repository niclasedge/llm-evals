package main

import (
	"fmt"
	"os"
	"time"

	"go-service/internal/devtools"
	"go-service/internal/logging"
)

func main() {
	// Load development configuration
	devConfig := devtools.LoadDevConfig()

	// Initialize logger for development
	logConfig := logging.Config{
		LogLevel: devConfig.LogLevel,
		DevMode:  devConfig.DevMode,
		LogFile:  "logs/reloader.log",
	}

	logger, err := logging.NewLogger(logConfig)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Close()

	// Create reloader configuration
	reloadConfig := &devtools.ReloadConfig{
		BuildCommand:    []string{"go", "build", "-o", "bin/server", "cmd/server/main.go"},
		StartCommand:    []string{"./bin/server"},
		GracefulTimeout: devConfig.GetGracefulTimeout(),
		RestartDelay:    devConfig.GetRestartDelay(),
		WorkingDir:      ".",
		ShowOutput:      true,
		BuildDir:        "bin",
		ServerBinary:    "bin/server",
	}

	// Create and start service reloader
	reloader, err := devtools.NewServiceReloader(reloadConfig, logger)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to create service reloader: %v\n", err)
		os.Exit(1)
	}

	if err := reloader.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to start service reloader: %v\n", err)
		os.Exit(1)
	}

	// Wait for reloader to finish (on shutdown signal)
	for reloader.IsRunning() {
		// Small sleep to prevent busy waiting
		time.Sleep(100 * time.Millisecond)
	}
}
