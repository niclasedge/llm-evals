package logging_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"go-service/internal/logging"
)

func TestNewRotationManager(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "rotation-test.log")

	config := logging.Config{
		LogFile:        logFile,
		LogRotateSize:  100,
		LogRotateCount: 10,
		LogRotateAge:   1,
	}

	rm, err := logging.NewRotationManager(config)
	if err != nil {
		t.Fatalf("Failed to create rotation manager: %v", err)
	}
	defer rm.Close()

	if rm == nil {
		t.Error("Rotation manager should not be nil")
	}
}

func TestRotationManagerInvalidPath(t *testing.T) {
	testCases := []struct {
		name        string
		logFile     string
		expectError bool
	}{
		{"no_extension", "logs/test", true},
		{"wrong_extension", "logs/test.txt", true},
		{"root_directory", "/test.log", true},
		{"current_directory", "./test.log", true},
		{"valid_path", "logs/test.log", false},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			config := logging.Config{
				LogFile:        tc.logFile,
				LogRotateSize:  100,
				LogRotateCount: 10,
				LogRotateAge:   1,
			}

			rm, err := logging.NewRotationManager(config)
			if tc.expectError && err == nil {
				t.Errorf("Expected error for path %s, but got none", tc.logFile)
			}
			if !tc.expectError && err != nil {
				t.Errorf("Unexpected error for path %s: %v", tc.logFile, err)
			}

			if rm != nil {
				rm.Close()
			}
		})
	}
}

func TestGetRotatedFiles(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "app.log")

	config := logging.Config{
		LogFile:        logFile,
		LogRotateSize:  100,
		LogRotateCount: 5,
		LogRotateAge:   1,
	}

	rm, err := logging.NewRotationManager(config)
	if err != nil {
		t.Fatalf("Failed to create rotation manager: %v", err)
	}
	defer rm.Close()

	// Create main log file
	if err := os.WriteFile(logFile, []byte("main log"), 0644); err != nil {
		t.Fatalf("Failed to create main log file: %v", err)
	}

	// Create some rotated files
	rotatedFiles := []string{
		filepath.Join(tempDir, "app.log.1"),
		filepath.Join(tempDir, "app.log.2"),
		filepath.Join(tempDir, "app.log.3"),
	}

	for _, file := range rotatedFiles {
		if err := os.WriteFile(file, []byte("rotated log"), 0644); err != nil {
			t.Fatalf("Failed to create rotated file %s: %v", file, err)
		}
	}

	// Create some non-log files that should be ignored
	nonLogFiles := []string{
		filepath.Join(tempDir, "other.txt"),
		filepath.Join(tempDir, "app.log.backup"),
	}

	for _, file := range nonLogFiles {
		if err := os.WriteFile(file, []byte("not a log"), 0644); err != nil {
			t.Fatalf("Failed to create non-log file %s: %v", file, err)
		}
	}

	// Test GetRotatedFiles
	found, err := rm.GetRotatedFiles()
	if err != nil {
		t.Fatalf("GetRotatedFiles failed: %v", err)
	}

	if len(found) != len(rotatedFiles) {
		t.Logf("Found files: %v", found)
		t.Logf("Expected files: %v", rotatedFiles)
		t.Errorf("Expected %d rotated files, got %d", len(rotatedFiles), len(found))
	}

	// Check that all expected files were found
	for _, expected := range rotatedFiles {
		foundFile := false
		for _, actual := range found {
			if actual == expected {
				foundFile = true
				break
			}
		}
		if !foundFile {
			t.Errorf("Expected rotated file not found: %s", expected)
		}
	}
}

func TestCleanupOldFiles(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "cleanup-test.log")

	config := logging.Config{
		LogFile:        logFile,
		LogRotateSize:  100,
		LogRotateCount: 5,
		LogRotateAge:   1, // 1 day
	}

	rm, err := logging.NewRotationManager(config)
	if err != nil {
		t.Fatalf("Failed to create rotation manager: %v", err)
	}
	defer rm.Close()

	// Create main log file
	if err := os.WriteFile(logFile, []byte("main log"), 0644); err != nil {
		t.Fatalf("Failed to create main log file: %v", err)
	}

	// Create an old rotated file (simulate old timestamp)
	oldFile := filepath.Join(tempDir, "cleanup-test.log.1")
	if err := os.WriteFile(oldFile, []byte("old log"), 0644); err != nil {
		t.Fatalf("Failed to create old log file: %v", err)
	}

	// Make the file appear old by changing its modification time
	oldTime := time.Now().AddDate(0, 0, -2) // 2 days ago
	if err := os.Chtimes(oldFile, oldTime, oldTime); err != nil {
		t.Fatalf("Failed to change file time: %v", err)
	}

	// Create a recent rotated file
	recentFile := filepath.Join(tempDir, "cleanup-test.log.2")
	if err := os.WriteFile(recentFile, []byte("recent log"), 0644); err != nil {
		t.Fatalf("Failed to create recent log file: %v", err)
	}

	// Run cleanup
	if err := rm.CleanupOldFiles(); err != nil {
		t.Fatalf("CleanupOldFiles failed: %v", err)
	}

	// Check that old file was removed
	if _, err := os.Stat(oldFile); !os.IsNotExist(err) {
		t.Errorf("Old file should have been removed: %s", oldFile)
	}

	// Check that recent file still exists
	if _, err := os.Stat(recentFile); os.IsNotExist(err) {
		t.Errorf("Recent file should still exist: %s", recentFile)
	}
}

func TestGetLogFileInfo(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "info-test.log")

	config := logging.Config{
		LogFile:        logFile,
		LogRotateSize:  50,
		LogRotateCount: 3,
		LogRotateAge:   2,
	}

	rm, err := logging.NewRotationManager(config)
	if err != nil {
		t.Fatalf("Failed to create rotation manager: %v", err)
	}
	defer rm.Close()

	// Create main log file with some content
	content := "Test log content for size calculation"
	if err := os.WriteFile(logFile, []byte(content), 0644); err != nil {
		t.Fatalf("Failed to create log file: %v", err)
	}

	// Create a rotated file
	rotatedFile := filepath.Join(tempDir, "info-test.log.1")
	if err := os.WriteFile(rotatedFile, []byte("rotated content"), 0644); err != nil {
		t.Fatalf("Failed to create rotated file: %v", err)
	}

	// Get log file info
	info, err := rm.GetLogFileInfo()
	if err != nil {
		t.Fatalf("GetLogFileInfo failed: %v", err)
	}

	// Check current file info
	if currentFile, ok := info["current_file"].(map[string]interface{}); ok {
		if path, ok := currentFile["path"].(string); !ok || path != logFile {
			t.Errorf("Expected current file path %s, got %v", logFile, path)
		}
		if size, ok := currentFile["size"].(int64); !ok || size != int64(len(content)) {
			t.Errorf("Expected current file size %d, got %v", len(content), size)
		}
	} else {
		t.Error("current_file info missing or invalid")
	}

	// Check rotated files count
	if count, ok := info["rotated_files_count"].(int); !ok || count != 1 {
		t.Errorf("Expected 1 rotated file, got %v", count)
	}

	// Check configuration
	if configInfo, ok := info["config"].(map[string]interface{}); ok {
		if maxSize, ok := configInfo["max_size"].(int); !ok || maxSize != 50 {
			t.Errorf("Expected max_size 50, got %v", maxSize)
		}
		if maxBackups, ok := configInfo["max_backups"].(int); !ok || maxBackups != 3 {
			t.Errorf("Expected max_backups 3, got %v", maxBackups)
		}
		if maxAge, ok := configInfo["max_age_days"].(int); !ok || maxAge != 2 {
			t.Errorf("Expected max_age_days 2, got %v", maxAge)
		}
		if compress, ok := configInfo["compress"].(bool); !ok || !compress {
			t.Errorf("Expected compress true, got %v", compress)
		}
	} else {
		t.Error("config info missing or invalid")
	}
}

func TestForceRotation(t *testing.T) {
	tempDir := t.TempDir()
	logFile := filepath.Join(tempDir, "force-rotation-test.log")

	config := logging.Config{
		LogFile:        logFile,
		LogRotateSize:  100,
		LogRotateCount: 5,
		LogRotateAge:   1,
	}

	rm, err := logging.NewRotationManager(config)
	if err != nil {
		t.Fatalf("Failed to create rotation manager: %v", err)
	}
	defer rm.Close()

	// Create main log file
	if err := os.WriteFile(logFile, []byte("content before rotation"), 0644); err != nil {
		t.Fatalf("Failed to create log file: %v", err)
	}

	// Force rotation
	if err := rm.ForceRotation(); err != nil {
		t.Fatalf("ForceRotation failed: %v", err)
	}

	// The exact behavior of forced rotation depends on lumberjack implementation
	// We mainly test that the method doesn't return an error
}

func TestRotationManagerDirectoryHandling(t *testing.T) {
	// Test with various invalid paths
	testCases := []struct {
		name       string
		path       string
		shouldFail bool
	}{
		{"non_existent_absolute", "/tmp/nonexistent/test.log", false}, // lumberjack will create
		{"invalid_extension", "/tmp/test.txt", true},
		{"current_dir_relative", "./test.log", true},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			config := logging.Config{
				LogFile:        tc.path,
				LogRotateSize:  100,
				LogRotateCount: 5,
				LogRotateAge:   1,
			}

			_, err := logging.NewRotationManager(config)
			if tc.shouldFail && err == nil {
				t.Errorf("Expected error for path %s", tc.path)
			}
			if !tc.shouldFail && err != nil {
				t.Errorf("Unexpected error for path %s: %v", tc.path, err)
			}
		})
	}
}
