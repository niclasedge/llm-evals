package auto_reload

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"go-service/internal/devtools"
	"go-service/internal/logging"

	"github.com/stretchr/testify/require"
)

// TestHelper provides common test setup and utilities for auto-reload tests
type TestHelper struct {
	t        *testing.T
	testDir  string
	reloader *devtools.ServiceReloader
	logger   *logging.Logger
	cleanup  func()
}

// NewTestHelper creates a new test helper instance
func NewTestHelper(t *testing.T) *TestHelper {
	helper := &TestHelper{t: t}
	helper.setupTestEnvironment()
	return helper
}

// Cleanup cleans up the test environment
func (h *TestHelper) Cleanup() {
	if h.reloader != nil {
		if err := h.reloader.Stop(); err != nil {
			h.t.Logf("Error stopping reloader: %v", err)
		}
	}
	if h.logger != nil {
		h.logger.Close()
	}
	if h.cleanup != nil {
		h.cleanup()
	}
}

// setupTestEnvironment sets up the complete test environment
func (h *TestHelper) setupTestEnvironment() {
	// Create temporary directory for test service
	tempDir, err := os.MkdirTemp("", "auto-reload-test-*")
	require.NoError(h.t, err, "Failed to create temp directory")

	h.testDir = tempDir
	h.cleanup = func() {
		os.RemoveAll(tempDir)
	}

	// Copy service files to temp directory
	sourceDir := filepath.Join("..", "..", "..")
	err = h.copyServiceFiles(sourceDir, tempDir)
	require.NoError(h.t, err, "Failed to copy service files")

	// Setup logger
	logFile := filepath.Join(tempDir, "logs", "test-reloader.log")
	os.MkdirAll(filepath.Dir(logFile), 0755)

	h.logger, err = logging.NewLogger(logging.Config{
		LogLevel: "info",
		DevMode:  true,
		LogFile:  logFile,
	})
	require.NoError(h.t, err, "Failed to create test logger")

	// Create and start reloader
	h.startReloader()
}

// startReloader creates and starts the service reloader
func (h *TestHelper) startReloader() {
	config := &devtools.ReloadConfig{
		BuildCommand:    []string{"go", "build", "-o", "bin/test-server", "cmd/server/main.go"},
		StartCommand:    []string{"./bin/test-server"},
		GracefulTimeout: 15 * time.Second,
		RestartDelay:    1 * time.Second,
		WorkingDir:      h.testDir,
		ShowOutput:      false, // Quiet during tests
		BuildDir:        "bin",
		ServerBinary:    "bin/test-server",
	}

	var err error
	h.reloader, err = devtools.NewServiceReloader(config, h.logger)
	require.NoError(h.t, err, "Failed to create service reloader")

	err = h.reloader.Start()
	require.NoError(h.t, err, "Failed to start service reloader")
}

// WaitForServiceReady waits for the service to become ready
func (h *TestHelper) WaitForServiceReady() {
	h.WaitForServiceReadyWithTimeout(30 * time.Second)
}

// WaitForServiceReadyWithTimeout waits for the service to become ready with a timeout
func (h *TestHelper) WaitForServiceReadyWithTimeout(timeout time.Duration) {
	deadline := time.Now().Add(timeout)
	healthEndpoint := "http://localhost:8080/health"

	for time.Now().Before(deadline) {
		resp, err := http.Get(healthEndpoint)
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				return // Service is ready
			}
		}
		time.Sleep(500 * time.Millisecond)
	}

	h.t.Fatalf("Service did not become ready within %v", timeout)
}

// WaitForReload waits for a reload cycle to complete
func (h *TestHelper) WaitForReload() {
	h.WaitForReloadWithTimeout(30 * time.Second)
}

// WaitForReloadWithTimeout waits for a reload cycle to complete with timeout
func (h *TestHelper) WaitForReloadWithTimeout(timeout time.Duration) {
	// Give some time for the file change to be detected and reload to start
	time.Sleep(1 * time.Second)

	// Wait for service to become responsive again
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if h.IsServiceResponsive() {
			// Additional small wait to ensure reload is fully complete
			time.Sleep(500 * time.Millisecond)
			return
		}
		time.Sleep(500 * time.Millisecond)
	}

	h.t.Fatalf("Reload did not complete within %v", timeout)
}

// IsServiceResponsive checks if the service is responsive
func (h *TestHelper) IsServiceResponsive() bool {
	resp, err := http.Get("http://localhost:8080/health")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode >= 200 && resp.StatusCode < 300
}

// VerifyServiceResponsive verifies the service is responsive and fails test if not
func (h *TestHelper) VerifyServiceResponsive() {
	require.True(h.t, h.IsServiceResponsive(), "Service should be responsive")
}

// ModifyFile makes a benign modification to a file to trigger reload
func (h *TestHelper) ModifyFile(relativePath string) {
	filePath := filepath.Join(h.testDir, relativePath)
	h.modifyFileAtPath(filePath)
}

// modifyFileAtPath makes a modification to a file at the given path
func (h *TestHelper) modifyFileAtPath(filePath string) {
	content, err := os.ReadFile(filePath)
	require.NoError(h.t, err, "Failed to read file: %s", filePath)

	// Add a comment with timestamp to trigger change
	timestamp := time.Now().Format("2006-01-02 15:04:05.000")
	newContent := string(content) + "\n// Auto-reload test modification: " + timestamp + "\n"

	err = os.WriteFile(filePath, []byte(newContent), 0644)
	require.NoError(h.t, err, "Failed to write modified file: %s", filePath)
}

// IntroduceBuildError introduces a build error in a file
func (h *TestHelper) IntroduceBuildError(relativePath string) {
	filePath := filepath.Join(h.testDir, relativePath)
	content, err := os.ReadFile(filePath)
	require.NoError(h.t, err, "Failed to read file: %s", filePath)

	// Add invalid Go syntax
	newContent := string(content) + "\n// BUILD ERROR: invalid syntax below\nfunc invalidSyntax( {\n"

	err = os.WriteFile(filePath, []byte(newContent), 0644)
	require.NoError(h.t, err, "Failed to write file with build error: %s", filePath)
}

// FixBuildError removes build errors from a file
func (h *TestHelper) FixBuildError(relativePath string) {
	filePath := filepath.Join(h.testDir, relativePath)
	content, err := os.ReadFile(filePath)
	require.NoError(h.t, err, "Failed to read file: %s", filePath)

	// Remove lines containing build errors
	lines := []string{}
	for _, line := range strings.Split(string(content), "\n") {
		if !strings.Contains(line, "BUILD ERROR:") && !strings.Contains(line, "func invalidSyntax(") {
			lines = append(lines, line)
		}
	}

	newContent := strings.Join(lines, "\n")
	err = os.WriteFile(filePath, []byte(newContent), 0644)
	require.NoError(h.t, err, "Failed to write fixed file: %s", filePath)
}

// MakeMultipleChanges makes multiple rapid changes to test debouncing
func (h *TestHelper) MakeMultipleChanges() {
	files := []string{
		"internal/api/handlers.go",
		"internal/models/types.go",
		"go.mod",
	}

	for i, file := range files {
		h.ModifyFile(file)
		if i < len(files)-1 {
			time.Sleep(100 * time.Millisecond) // Small delay between changes
		}
	}
}

// TestEndpoint tests a specific endpoint and verifies response
func (h *TestHelper) TestEndpoint(endpoint string) {
	resp, err := http.Get("http://localhost:8080" + endpoint)
	require.NoError(h.t, err, "Request to %s should succeed", endpoint)
	defer resp.Body.Close()

	require.True(h.t, resp.StatusCode >= 200 && resp.StatusCode < 300,
		"Endpoint %s should return success status, got %d", endpoint, resp.StatusCode)
}

// GetTestDir returns the test directory path
func (h *TestHelper) GetTestDir() string {
	return h.testDir
}

// GetReloader returns the service reloader instance
func (h *TestHelper) GetReloader() *devtools.ServiceReloader {
	return h.reloader
}

// copyServiceFiles copies necessary service files to the test directory
func (h *TestHelper) copyServiceFiles(src, dst string) error {
	// Create basic directory structure
	dirs := []string{
		"cmd/server",
		"internal/api",
		"internal/models",
		"internal/database",
		"internal/devtools",
		"internal/logging",
		"internal/ollama",
		"internal/monitoring",
		"internal/health",
		"bin",
		"logs",
	}

	for _, dir := range dirs {
		err := os.MkdirAll(filepath.Join(dst, dir), 0755)
		if err != nil {
			return err
		}
	}

	// Copy essential files
	filesToCopy := []string{
		"go.mod",
		"go.sum",
		"cmd/server/main.go",
	}

	for _, file := range filesToCopy {
		srcPath := filepath.Join(src, file)
		dstPath := filepath.Join(dst, file)

		if err := h.copyFile(srcPath, dstPath); err != nil {
			return err
		}
	}

	// Copy internal packages
	internalDirs := []string{
		"internal/api",
		"internal/models",
		"internal/database",
		"internal/devtools",
		"internal/logging",
		"internal/ollama",
		"internal/monitoring",
		"internal/health",
	}

	for _, dir := range internalDirs {
		srcPath := filepath.Join(src, dir)
		dstPath := filepath.Join(dst, dir)

		if err := h.copyDirectoryContents(srcPath, dstPath); err != nil {
			return err
		}
	}

	return nil
}

// copyFile copies a single file
func (h *TestHelper) copyFile(src, dst string) error {
	// Check if source file exists
	if _, err := os.Stat(src); os.IsNotExist(err) {
		// Create a minimal file if it doesn't exist
		return h.createMinimalFile(dst)
	}

	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destFile.Close()

	_, err = io.Copy(destFile, sourceFile)
	return err
}

// copyDirectoryContents copies the contents of a directory
func (h *TestHelper) copyDirectoryContents(src, dst string) error {
	// Check if source directory exists
	if _, err := os.Stat(src); os.IsNotExist(err) {
		// Create minimal go files for missing packages
		return h.createMinimalPackage(dst)
	}

	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Skip test files and certain directories
		if strings.HasSuffix(path, "_test.go") {
			return nil
		}

		relPath, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}

		dstPath := filepath.Join(dst, relPath)

		if info.IsDir() {
			return os.MkdirAll(dstPath, info.Mode())
		}

		return h.copyFile(path, dstPath)
	})
}

// createMinimalFile creates a minimal Go file
func (h *TestHelper) createMinimalFile(path string) error {
	if strings.HasSuffix(path, ".go") {
		content := `package main

import "fmt"

func main() {
	fmt.Println("Test service")
}
`
		return os.WriteFile(path, []byte(content), 0644)
	}

	if strings.HasSuffix(path, "go.mod") {
		content := `module go-service

go 1.21
`
		return os.WriteFile(path, []byte(content), 0644)
	}

	return os.WriteFile(path, []byte(""), 0644)
}

// createMinimalPackage creates minimal Go package files
func (h *TestHelper) createMinimalPackage(pkgPath string) error {
	pkgName := filepath.Base(pkgPath)
	if pkgName == "main" {
		pkgName = "main"
	}

	content := fmt.Sprintf(`package %s

// Minimal package for testing
var TestVar = "test"
`, pkgName)

	fileName := filepath.Join(pkgPath, pkgName+".go")
	return os.WriteFile(fileName, []byte(content), 0644)
}

// Additional helper methods for WebSocket tests

// StartReloader starts the auto-reload service
func (h *TestHelper) StartReloader() {
	if h.reloader == nil {
		h.startReloader()
	}
}

// GetServiceURL returns the base URL for the test service
func (h *TestHelper) GetServiceURL() string {
	return "http://localhost:8080"
}

// ModifySourceFile modifies a source file with an optional comment
func (h *TestHelper) ModifySourceFile(relativePath, comment string) {
	filePath := filepath.Join(h.testDir, relativePath)
	content, err := os.ReadFile(filePath)
	require.NoError(h.t, err, "Failed to read file: %s", filePath)

	// Add the comment with timestamp to trigger change
	timestamp := time.Now().Format("2006-01-02 15:04:05.000")
	newContent := string(content) + "\n// " + comment + " - " + timestamp + "\n"

	err = os.WriteFile(filePath, []byte(newContent), 0644)
	require.NoError(h.t, err, "Failed to write modified file: %s", filePath)
}

// WaitForReloadComplete waits for a reload cycle to complete
func (h *TestHelper) WaitForReloadComplete(timeout time.Duration) {
	h.WaitForReloadWithTimeout(timeout)
}

// WaitForServiceReadyWithCustomTimeout waits for service to be ready with custom timeout
func (h *TestHelper) WaitForServiceReadyWithCustomTimeout(timeout time.Duration) {
	h.WaitForServiceReadyWithTimeout(timeout)
}
