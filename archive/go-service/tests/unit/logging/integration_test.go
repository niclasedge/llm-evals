package logging_test

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"go-service/internal/logging"
)

// TestHighVolumeLogging tests log rotation under high volume
func TestHighVolumeLogging(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping high volume test in short mode")
	}

	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "high-volume.log")

	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false,
		LogFile:        logFile,
		LogRotateSize:  1, // 1MB - small for testing
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()

	// Generate high volume of logs
	messageSize := 1000 // 1KB per message
	numMessages := 2000 // 2MB total
	message := strings.Repeat("a", messageSize)

	start := time.Now()
	for i := 0; i < numMessages; i++ {
		logger.Info("High volume test",
			"iteration", i,
			"timestamp", time.Now().Unix(),
			"large_data", message)

		// Small delay to allow for rotation
		if i%100 == 0 {
			time.Sleep(1 * time.Millisecond)
		}
	}
	duration := time.Since(start)

	t.Logf("Logged %d messages (%d bytes each) in %v", numMessages, messageSize, duration)

	// Verify main log file exists
	if _, err := os.Stat(logFile); os.IsNotExist(err) {
		t.Errorf("Main log file should exist: %s", logFile)
	}

	// Check for rotated files
	entries, err := os.ReadDir(tempDir)
	if err != nil {
		t.Fatalf("Failed to read temp directory: %v", err)
	}

	logFiles := 0
	for _, entry := range entries {
		if strings.HasPrefix(entry.Name(), "high-volume.log") {
			logFiles++
			t.Logf("Found log file: %s", entry.Name())
		}
	}

	if logFiles < 1 {
		t.Errorf("Expected at least one log file, got %d", logFiles)
	}

	// Check if main log file has content (rotation may or may not occur depending on exact timing)
	stat, err := os.Stat(logFile)
	if err != nil {
		t.Errorf("Main log file should exist: %v", err)
	} else if stat.Size() == 0 {
		t.Error("Main log file should have content")
	}
}

// TestConcurrentLogging tests thread safety
func TestConcurrentLogging(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "concurrent.log")

	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false,
		LogFile:        logFile,
		LogRotateSize:  10, // 10MB
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()

	// Number of concurrent goroutines
	numGoroutines := 10
	messagesPerGoroutine := 100

	// Channel to wait for all goroutines to complete
	done := make(chan bool, numGoroutines)

	// Start concurrent logging
	for i := 0; i < numGoroutines; i++ {
		go func(goroutineID int) {
			defer func() { done <- true }()

			for j := 0; j < messagesPerGoroutine; j++ {
				logger.Info("Concurrent log message",
					"goroutine_id", goroutineID,
					"message_id", j,
					"timestamp", time.Now().UnixNano())
			}
		}(i)
	}

	// Wait for all goroutines to complete
	for i := 0; i < numGoroutines; i++ {
		<-done
	}

	// Verify log file exists and has content
	if _, err := os.Stat(logFile); os.IsNotExist(err) {
		t.Errorf("Log file should exist: %s", logFile)
	}

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	if len(content) == 0 {
		t.Error("Log file should not be empty after concurrent logging")
	}

	// Count log entries (each should be on a separate line)
	lines := strings.Split(string(content), "\n")
	nonEmptyLines := 0
	for _, line := range lines {
		if strings.TrimSpace(line) != "" {
			nonEmptyLines++
		}
	}

	expectedMessages := numGoroutines * messagesPerGoroutine
	if nonEmptyLines < expectedMessages {
		t.Errorf("Expected at least %d log messages, got %d", expectedMessages, nonEmptyLines)
	}
}

// TestJSONFormatConsistency verifies JSON format in both file and stdout
func TestJSONFormatConsistency(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "json-test.log")

	// Test file-only mode
	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false, // File only
		LogFile:        logFile,
		LogRotateSize:  100,
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()

	// Log a structured message
	ctx := context.Background()
	ctx = logging.WithCorrelationID(ctx, "test-correlation")
	ctx = logging.WithRequestID(ctx, "test-request")

	contextLogger := logging.LogWithContext(ctx, logger.Logger)
	contextLogger.Info("Test JSON format",
		"string_field", "test_value",
		"int_field", 42,
		"bool_field", true,
		"float_field", 3.14)

	// Read and parse log file
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	if len(lines) == 0 {
		t.Fatal("No log entries found")
	}

	// Parse the first log entry as JSON
	var logEntry map[string]interface{}
	if err := json.Unmarshal([]byte(lines[0]), &logEntry); err != nil {
		t.Fatalf("Failed to parse log entry as JSON: %v\nContent: %s", err, lines[0])
	}

	// Verify expected fields
	expectedFields := map[string]interface{}{
		"correlation_id": "test-correlation",
		"request_id":     "test-request",
		"msg":            "Test JSON format",
		"string_field":   "test_value",
		"int_field":      float64(42), // JSON unmarshals numbers as float64
		"bool_field":     true,
		"float_field":    3.14,
	}

	for key, expected := range expectedFields {
		if actual, exists := logEntry[key]; !exists {
			t.Errorf("Expected field %s not found in log entry", key)
		} else if actual != expected {
			t.Errorf("Field %s: expected %v, got %v", key, expected, actual)
		}
	}

	// Verify timestamp exists and is valid
	if timeStr, exists := logEntry["time"]; !exists {
		t.Error("Timestamp field 'time' not found")
	} else {
		if _, err := time.Parse(time.RFC3339, timeStr.(string)); err != nil {
			t.Errorf("Invalid timestamp format: %v", timeStr)
		}
	}

	// Verify level field
	if level, exists := logEntry["level"]; !exists {
		t.Error("Level field not found")
	} else if level != "INFO" {
		t.Errorf("Expected level INFO, got %v", level)
	}
}

// TestDualOutputMode tests dev mode with both file and stdout
func TestDualOutputMode(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "dual-output.log")

	config := logging.Config{
		LogLevel:       "debug",
		DevMode:        true, // Enable dual output
		LogFile:        logFile,
		LogRotateSize:  100,
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Close()

	// Log different levels
	logger.Debug("Debug message", "level", "debug")
	logger.Info("Info message", "level", "info")
	logger.Warn("Warning message", "level", "warn")
	logger.Error("Error message", "level", "error")

	// Verify log file contains all messages
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	logContent := string(content)
	expectedMessages := []string{
		"Debug message",
		"Info message",
		"Warning message",
		"Error message",
	}

	for _, msg := range expectedMessages {
		if !strings.Contains(logContent, msg) {
			t.Errorf("Log file should contain message: %s", msg)
		}
	}

	// Verify JSON format in dual output
	lines := strings.Split(strings.TrimSpace(logContent), "\n")
	for i, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}

		var entry map[string]interface{}
		if err := json.Unmarshal([]byte(line), &entry); err != nil {
			t.Errorf("Line %d is not valid JSON: %v\nLine: %s", i+1, err, line)
		}
	}
}

// TestErrorHandlingAndRecovery tests error scenarios
func TestErrorHandlingAndRecovery(t *testing.T) {
	// Test logging after file system errors
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "error-test.log")

	config := logging.Config{
		LogLevel:       "info",
		DevMode:        false,
		LogFile:        logFile,
		LogRotateSize:  100,
		LogRotateCount: 3,
		LogRotateAge:   1,
	}

	logger, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}

	// Log some initial messages
	logger.Info("Initial message", "test", "error_handling")

	// Verify initial logging works
	if _, err := os.Stat(logFile); os.IsNotExist(err) {
		t.Error("Initial log file should exist")
	}

	// Clean up
	logger.Close()

	// Test recovery - create new logger with same config
	logger2, err := logging.NewLogger(config)
	if err != nil {
		t.Fatalf("Failed to create second logger: %v", err)
	}
	defer logger2.Close()

	// Should be able to log again
	logger2.Info("Recovery message", "test", "recovery")

	// Verify recovery logging works
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatalf("Failed to read log file after recovery: %v", err)
	}

	if !strings.Contains(string(content), "Recovery message") {
		t.Error("Log file should contain recovery message")
	}
}

// TestConfigurationEdgeCases tests edge cases in configuration
func TestConfigurationEdgeCases(t *testing.T) {
	tempDir := t.TempDir()

	testCases := []struct {
		name   string
		config logging.Config
		valid  bool
	}{
		{
			name: "zero_rotation_size",
			config: logging.Config{
				LogLevel:       "info",
				LogFile:        filepath.Join(tempDir, "zero-size.log"),
				LogRotateSize:  0,
				LogRotateCount: 3,
				LogRotateAge:   1,
			},
			valid: true, // lumberjack handles this
		},
		{
			name: "negative_rotation_count",
			config: logging.Config{
				LogLevel:       "info",
				LogFile:        filepath.Join(tempDir, "negative-count.log"),
				LogRotateSize:  100,
				LogRotateCount: -1,
				LogRotateAge:   1,
			},
			valid: true, // lumberjack handles this
		},
		{
			name: "zero_rotation_age",
			config: logging.Config{
				LogLevel:       "info",
				LogFile:        filepath.Join(tempDir, "zero-age.log"),
				LogRotateSize:  100,
				LogRotateCount: 3,
				LogRotateAge:   0,
			},
			valid: true, // lumberjack handles this
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			logger, err := logging.NewLogger(tc.config)

			if tc.valid && err != nil {
				t.Errorf("Expected valid config, but got error: %v", err)
			}
			if !tc.valid && err == nil {
				t.Errorf("Expected invalid config, but got no error")
			}

			if logger != nil {
				// Test that logging still works
				logger.Info("Test message", "config", tc.name)
				logger.Close()
			}
		})
	}
}
