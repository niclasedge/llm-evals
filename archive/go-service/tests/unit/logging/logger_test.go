package logging_test

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"go-service/internal/logging"
)

func TestNewLogger(t *testing.T) {
	// Create temporary directory for testing
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "test.log")

	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false,
		LogFile:        logFile,
		LogRotateSize:  1, // 1MB for testing
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()

	// Test logging functionality
	logger.Info("Test message", "key", "value")

	// Verify log file was created
	if _, err := os.Stat(logFile); os.IsNotExist(err) {
		t.Errorf("Log file was not created: %s", logFile)
	}
}

func TestNewLoggerDevMode(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "test-dev.log")

	config := logging.Config{
		LogLevel:       "debug",
		DevMode:        true, // Enable dev mode
		LogFile:        logFile,
		LogRotateSize:  1,
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger in dev mode: %v", err)
	}
	defer logger.Close()

	// Test logging in dev mode (should output to both file and stdout)
	logger.Debug("Debug message in dev mode", "test", true)

	// Verify log file was created
	if _, err := os.Stat(logFile); os.IsNotExist(err) {
		t.Errorf("Log file was not created in dev mode: %s", logFile)
	}
}

func TestNewLoggerInvalidDirectory(t *testing.T) {
	// Use a path that doesn't exist and can't be created
	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false,
		LogFile:        "/nonexistent/readonly/test.log",
		LogRotateSize:  1,
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	// Should fall back to stdout-only logger
	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("NewLogger should not fail even with invalid directory: %v", err)
	}
	defer logger.Close()

	// Test that logging still works (stdout only)
	logger.Info("Fallback message", "fallback", true)
}

func TestLogWithContext(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "context-test.log")

	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false,
		LogFile:        logFile,
		LogRotateSize:  1,
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()

	// Test context with correlation ID
	ctx := context.Background()
	ctx = logging.WithCorrelationID(ctx, "test-correlation-123")
	ctx = logging.WithRequestID(ctx, "test-request-456")

	contextLogger := logging.LogWithContext(ctx, logger.Logger)
	contextLogger.Info("Message with context", "test", "value")

	// Read log file and verify context was included
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	logContent := string(content)
	if !strings.Contains(logContent, "test-correlation-123") {
		t.Errorf("Log should contain correlation ID, got: %s", logContent)
	}
	if !strings.Contains(logContent, "test-request-456") {
		t.Errorf("Log should contain request ID, got: %s", logContent)
	}
}

func TestLogLevels(t *testing.T) {
	tempDir := t.TempDir()

	testCases := []struct {
		name     string
		level    string
		expected bool
	}{
		{"debug_level", "debug", true},
		{"info_level", "info", true},
		{"warn_level", "warn", true},
		{"error_level", "error", true},
		{"invalid_level", "invalid", true}, // Should default to info
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			logFile := filepath.Join(tempDir, tc.name+".log")

			config := logging.Config{
				LogLevel:       tc.level,
				DevMode:        false,
				LogFile:        logFile,
				LogRotateSize:  1,
				LogRotateCount: 3,
				LogRotateAge:   1,
			}

			logger, err := logging.NewLogger(config)
			if !tc.expected && err == nil {
				t.Errorf("Expected error for level %s, but got none", tc.level)
			}
			if tc.expected && err != nil {
				t.Errorf("Unexpected error for level %s: %v", tc.level, err)
			}

			if logger != nil {
				logger.Close()
			}
		})
	}
}

func TestLogRotation(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "rotation-test.log")

	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false,
		LogFile:        logFile,
		LogRotateSize:  1, // 1MB - small for testing
		LogRotateCount: 2,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()

	// Write enough data to trigger rotation
	largeMessage := strings.Repeat("This is a test message for log rotation. ", 1000)
	for i := 0; i < 100; i++ {
		logger.Info("Large message", "iteration", i, "data", largeMessage)
	}

	// Force rotation to ensure it happens
	if err := logger.Rotate(); err != nil {
		t.Errorf("Failed to rotate log: %v", err)
	}

	// Check that log files exist
	if _, err := os.Stat(logFile); os.IsNotExist(err) {
		t.Errorf("Main log file should exist: %s", logFile)
	}

	// Check for rotated files (may exist depending on size)
	rotatedFile := logFile + ".1"
	if _, err := os.Stat(rotatedFile); err == nil {
		t.Logf("Rotated file exists as expected: %s", rotatedFile)
	}
}

func TestContextHelpers(t *testing.T) {
	ctx := context.Background()

	// Test correlation ID
	correlationID := "test-correlation"
	ctx = logging.WithCorrelationID(ctx, correlationID)
	if got := logging.GetCorrelationID(ctx); got != correlationID {
		t.Errorf("Expected correlation ID %s, got %s", correlationID, got)
	}

	// Test request ID
	requestID := "test-request"
	ctx = logging.WithRequestID(ctx, requestID)
	if got := logging.GetRequestID(ctx); got != requestID {
		t.Errorf("Expected request ID %s, got %s", requestID, got)
	}

	// Test user ID
	userID := "test-user"
	ctx = logging.WithUserID(ctx, userID)
	if got := logging.GetUserID(ctx); got != userID {
		t.Errorf("Expected user ID %s, got %s", userID, got)
	}

	// Test empty context
	emptyCtx := context.Background()
	if got := logging.GetCorrelationID(emptyCtx); got != "" {
		t.Errorf("Expected empty correlation ID, got %s", got)
	}
}

func TestNewCorrelationID(t *testing.T) {
	id1 := logging.NewCorrelationID()
	id2 := logging.NewCorrelationID()

	if id1 == "" {
		t.Error("NewCorrelationID should not return empty string")
	}
	if id1 == id2 {
		t.Error("NewCorrelationID should return unique IDs")
	}
}

func TestAutoGenerateIDs(t *testing.T) {
	ctx := context.Background()

	// Test auto-generation when empty string is passed
	ctx = logging.WithCorrelationID(ctx, "")
	if got := logging.GetCorrelationID(ctx); got == "" {
		t.Error("Should auto-generate correlation ID when empty string is passed")
	}

	ctx = logging.WithRequestID(ctx, "")
	if got := logging.GetRequestID(ctx); got == "" {
		t.Error("Should auto-generate request ID when empty string is passed")
	}
}
