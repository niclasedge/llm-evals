package devtools

import (
	"os"
	"testing"
	"time"

	"go-service/internal/devtools"
	"go-service/internal/logging"
)

func TestNewServiceReloader(t *testing.T) {
	// Create a test configuration
	config := &devtools.ReloadConfig{
		BuildCommand:    []string{"echo", "build"},
		StartCommand:    []string{"echo", "start"},
		GracefulTimeout: 5 * time.Second,
		RestartDelay:    500 * time.Millisecond,
		WorkingDir:      ".",
		ShowOutput:      false,
		BuildDir:        "bin",
		ServerBinary:    "bin/server",
	}

	// Create a test logger
	logConfig := logging.Config{
		LogLevel: "info",
		DevMode:  true,
		LogFile:  "/tmp/test-reloader.log",
	}

	logger, err := logging.NewLogger(logConfig)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()
	defer os.Remove("/tmp/test-reloader.log")

	// Create service reloader
	reloader, err := devtools.NewServiceReloader(config, logger)
	if err != nil {
		t.Fatalf("Failed to create service reloader: %v", err)
	}

	// Test that reloader was created successfully
	if reloader == nil {
		t.Error("Service reloader should not be nil")
	}

	// Test that reloader is not running initially
	if reloader.IsRunning() {
		t.Error("Service reloader should not be running initially")
	}
}

func TestDefaultReloadConfig(t *testing.T) {
	config := devtools.DefaultReloadConfig()

	if config == nil {
		t.Fatal("Default reload config should not be nil")
	}

	// Test default values
	if len(config.BuildCommand) == 0 {
		t.Error("Build command should not be empty")
	}

	if len(config.StartCommand) == 0 {
		t.Error("Start command should not be empty")
	}

	if config.GracefulTimeout <= 0 {
		t.Error("Graceful timeout should be positive")
	}

	if config.RestartDelay < 0 {
		t.Error("Restart delay should not be negative")
	}
}

func TestDevConfigGetters(t *testing.T) {
	config := &devtools.DevConfig{
		GracefulTimeoutSec: 15,
		RestartDelayMs:     2000,
	}

	// Test GetGracefulTimeout
	timeout := config.GetGracefulTimeout()
	expected := 15 * time.Second
	if timeout != expected {
		t.Errorf("GetGracefulTimeout() = %v, want %v", timeout, expected)
	}

	// Test GetRestartDelay
	delay := config.GetRestartDelay()
	expectedDelay := 2000 * time.Millisecond
	if delay != expectedDelay {
		t.Errorf("GetRestartDelay() = %v, want %v", delay, expectedDelay)
	}
}

func TestLoadDevConfig(t *testing.T) {
	// Test loading configuration from environment
	originalLogLevel := os.Getenv("LOG_LEVEL")
	originalDevMode := os.Getenv("DEV_MODE")
	originalWatchEnabled := os.Getenv("WATCH_ENABLED")

	// Set test environment variables
	os.Setenv("LOG_LEVEL", "debug")
	os.Setenv("DEV_MODE", "true")
	os.Setenv("WATCH_ENABLED", "false")

	defer func() {
		// Restore original environment
		if originalLogLevel == "" {
			os.Unsetenv("LOG_LEVEL")
		} else {
			os.Setenv("LOG_LEVEL", originalLogLevel)
		}
		if originalDevMode == "" {
			os.Unsetenv("DEV_MODE")
		} else {
			os.Setenv("DEV_MODE", originalDevMode)
		}
		if originalWatchEnabled == "" {
			os.Unsetenv("WATCH_ENABLED")
		} else {
			os.Setenv("WATCH_ENABLED", originalWatchEnabled)
		}
	}()

	config := devtools.LoadDevConfig()

	if config.LogLevel != "debug" {
		t.Errorf("LogLevel = %v, want debug", config.LogLevel)
	}

	if !config.DevMode {
		t.Error("DevMode should be true")
	}

	if config.WatchEnabled {
		t.Error("WatchEnabled should be false")
	}
}
