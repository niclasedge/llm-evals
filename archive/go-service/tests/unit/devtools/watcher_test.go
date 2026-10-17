package devtools_test

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"go-service/internal/devtools"
	"go-service/internal/logging"
)

func TestFileWatcher_NewFileWatcher(t *testing.T) {
	tests := []struct {
		name   string
		config *devtools.WatchConfig
		logger *logging.Logger
		want   error
	}{
		{
			name:   "default config",
			config: nil,
			logger: nil,
			want:   nil,
		},
		{
			name: "custom config",
			config: &devtools.WatchConfig{
				RootDir:    "./test",
				Patterns:   []string{"*.go"},
				Excludes:   []string{"*.tmp"},
				DebounceMs: 1000,
			},
			logger: logging.NewDefaultLogger(),
			want:   nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			watcher, err := devtools.NewFileWatcher(tt.config, tt.logger)
			if (err != nil) != (tt.want != nil) {
				t.Errorf("NewFileWatcher() error = %v, want %v", err, tt.want)
				return
			}
			if watcher == nil {
				t.Error("NewFileWatcher() returned nil watcher")
			}
			if watcher != nil {
				watcher.Stop()
			}
		})
	}
}

func TestFileWatcher_StartStop(t *testing.T) {
	// Create temporary directory for testing
	tempDir, err := os.MkdirTemp("", "watcher_test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	config := &devtools.WatchConfig{
		RootDir:    tempDir,
		Patterns:   []string{"*.go"},
		Excludes:   []string{"*.tmp"},
		DebounceMs: 100,
	}

	logger := logging.NewDefaultLogger()
	watcher, err := devtools.NewFileWatcher(config, logger)
	if err != nil {
		t.Fatalf("Failed to create watcher: %v", err)
	}

	// Test initial state
	if watcher.IsRunning() {
		t.Error("Watcher should not be running initially")
	}

	// Test starting
	err = watcher.Start()
	if err != nil {
		t.Fatalf("Failed to start watcher: %v", err)
	}

	if !watcher.IsRunning() {
		t.Error("Watcher should be running after Start()")
	}

	// Test starting again (should fail)
	err = watcher.Start()
	if err == nil {
		t.Error("Starting already running watcher should return error")
	}

	// Test stopping
	err = watcher.Stop()
	if err != nil {
		t.Errorf("Failed to stop watcher: %v", err)
	}

	if watcher.IsRunning() {
		t.Error("Watcher should not be running after Stop()")
	}

	// Test stopping again (should be safe)
	err = watcher.Stop()
	if err != nil {
		t.Errorf("Stopping already stopped watcher should not return error: %v", err)
	}
}

func TestFileWatcher_FileChanges(t *testing.T) {
	// Create temporary directory for testing
	tempDir, err := os.MkdirTemp("", "watcher_test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	config := &devtools.WatchConfig{
		RootDir:    tempDir,
		Patterns:   []string{"*.go"},
		Excludes:   []string{"*.tmp"},
		DebounceMs: 100,
	}

	logger := logging.NewDefaultLogger()
	watcher, err := devtools.NewFileWatcher(config, logger)
	if err != nil {
		t.Fatalf("Failed to create watcher: %v", err)
	}

	err = watcher.Start()
	if err != nil {
		t.Fatalf("Failed to start watcher: %v", err)
	}
	defer watcher.Stop()

	// Wait a moment for watcher to initialize
	time.Sleep(50 * time.Millisecond)

	// Create a Go file
	testFile := filepath.Join(tempDir, "test.go")
	err = os.WriteFile(testFile, []byte("package main"), 0644)
	if err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	// Wait for changes to be detected and debounced
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	select {
	case changes := <-watcher.Changes():
		if len(changes) == 0 {
			t.Error("Expected changes to be detected")
		}

		found := false
		for _, change := range changes {
			if change == testFile {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected %s to be in changes: %v", testFile, changes)
		}
	case <-ctx.Done():
		t.Error("Timeout waiting for file changes to be detected")
	}
}

func TestFileWatcher_ExcludedFiles(t *testing.T) {
	// Create temporary directory for testing
	tempDir, err := os.MkdirTemp("", "watcher_test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	config := &devtools.WatchConfig{
		RootDir:    tempDir,
		Patterns:   []string{"*.go", "*.tmp"},
		Excludes:   []string{"*.tmp"},
		DebounceMs: 100,
	}

	logger := logging.NewDefaultLogger()
	watcher, err := devtools.NewFileWatcher(config, logger)
	if err != nil {
		t.Fatalf("Failed to create watcher: %v", err)
	}

	err = watcher.Start()
	if err != nil {
		t.Fatalf("Failed to start watcher: %v", err)
	}
	defer watcher.Stop()

	// Wait a moment for watcher to initialize
	time.Sleep(50 * time.Millisecond)

	// Create a temporary file (should be excluded)
	tmpFile := filepath.Join(tempDir, "test.tmp")
	err = os.WriteFile(tmpFile, []byte("temp content"), 0644)
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}

	// Create a Go file (should be included)
	goFile := filepath.Join(tempDir, "test.go")
	err = os.WriteFile(goFile, []byte("package main"), 0644)
	if err != nil {
		t.Fatalf("Failed to create Go file: %v", err)
	}

	// Wait for changes to be detected and debounced
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	select {
	case changes := <-watcher.Changes():
		// Check that Go file is included
		goFound := false
		tmpFound := false

		for _, change := range changes {
			if change == goFile {
				goFound = true
			}
			if change == tmpFile {
				tmpFound = true
			}
		}

		if !goFound {
			t.Error("Expected Go file to be detected")
		}
		if tmpFound {
			t.Error("Temporary file should be excluded")
		}
	case <-ctx.Done():
		t.Error("Timeout waiting for file changes to be detected")
	}
}

func TestDefaultWatchConfig(t *testing.T) {
	config := devtools.DefaultWatchConfig()

	if config == nil {
		t.Fatal("DefaultWatchConfig() returned nil")
	}

	if config.RootDir != "." {
		t.Errorf("Expected RootDir to be '.', got %s", config.RootDir)
	}

	if config.DebounceMs != 500 {
		t.Errorf("Expected DebounceMs to be 500, got %d", config.DebounceMs)
	}

	if len(config.Patterns) == 0 {
		t.Error("Expected patterns to be set")
	}

	if len(config.Excludes) == 0 {
		t.Error("Expected excludes to be set")
	}
}
