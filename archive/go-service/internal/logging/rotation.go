package logging

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"gopkg.in/natefinch/lumberjack.v2"
)

// RotationManager handles log file rotation and management
type RotationManager struct {
	rotator *lumberjack.Logger
	config  Config
}

// NewRotationManager creates a new rotation manager
func NewRotationManager(config Config) (*RotationManager, error) {
	// Validate log file path
	if err := validateLogPath(config.LogFile); err != nil {
		return nil, fmt.Errorf("invalid log file path: %w", err)
	}

	rotator := &lumberjack.Logger{
		Filename:   config.LogFile,
		MaxSize:    config.LogRotateSize,
		MaxBackups: config.LogRotateCount,
		MaxAge:     config.LogRotateAge,
		Compress:   true,
	}

	return &RotationManager{
		rotator: rotator,
		config:  config,
	}, nil
}

// validateLogPath validates the log file path and directory
func validateLogPath(logFile string) error {
	// Check for valid file extension
	if !strings.HasSuffix(logFile, ".log") {
		return fmt.Errorf("log file must have .log extension")
	}

	// Reject current directory references
	if strings.HasPrefix(logFile, "./") || logFile == "." {
		return fmt.Errorf("log file cannot be in current directory")
	}

	// Ensure absolute path or relative to project root
	if !filepath.IsAbs(logFile) {
		// Make relative to current working directory
		abs, err := filepath.Abs(logFile)
		if err != nil {
			return fmt.Errorf("failed to resolve absolute path: %w", err)
		}
		logFile = abs
	}

	// Check directory is valid
	dir := filepath.Dir(logFile)
	if dir == "." || dir == "/" {
		return fmt.Errorf("log file cannot be in root or current directory")
	}

	return nil
}

// GetRotatedFiles returns list of rotated log files
func (rm *RotationManager) GetRotatedFiles() ([]string, error) {
	dir := filepath.Dir(rm.config.LogFile)
	baseName := filepath.Base(rm.config.LogFile)

	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("failed to read log directory: %w", err)
	}

	var rotatedFiles []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		name := entry.Name()
		// Match pattern: go-service.log.1, go-service.log.2, etc. (numeric suffix only)
		if strings.HasPrefix(name, baseName+".") && name != baseName {
			// Verify it's a numeric suffix (rotated file)
			suffix := name[len(baseName)+1:]
			if len(suffix) > 0 && isNumeric(suffix) {
				rotatedFiles = append(rotatedFiles, filepath.Join(dir, name))
			}
		}
	}

	return rotatedFiles, nil
}

// CleanupOldFiles removes rotated files older than MaxAge
func (rm *RotationManager) CleanupOldFiles() error {
	rotatedFiles, err := rm.GetRotatedFiles()
	if err != nil {
		return err
	}

	cutoff := time.Now().AddDate(0, 0, -rm.config.LogRotateAge)

	for _, file := range rotatedFiles {
		info, err := os.Stat(file)
		if err != nil {
			continue // Skip files we can't stat
		}

		if info.ModTime().Before(cutoff) {
			if err := os.Remove(file); err != nil {
				// Log error but continue cleanup
				continue
			}
		}
	}

	return nil
}

// GetLogFileInfo returns information about current and rotated log files
func (rm *RotationManager) GetLogFileInfo() (map[string]interface{}, error) {
	info := make(map[string]interface{})

	// Current log file info
	if stat, err := os.Stat(rm.config.LogFile); err == nil {
		info["current_file"] = map[string]interface{}{
			"path":     rm.config.LogFile,
			"size":     stat.Size(),
			"modified": stat.ModTime(),
		}
	}

	// Rotated files info
	rotatedFiles, err := rm.GetRotatedFiles()
	if err == nil {
		info["rotated_files_count"] = len(rotatedFiles)
		info["rotated_files"] = rotatedFiles
	}

	// Configuration
	info["config"] = map[string]interface{}{
		"max_size":     rm.config.LogRotateSize,
		"max_backups":  rm.config.LogRotateCount,
		"max_age_days": rm.config.LogRotateAge,
		"compress":     true,
	}

	return info, nil
}

// ForceRotation manually triggers log rotation
func (rm *RotationManager) ForceRotation() error {
	return rm.rotator.Rotate()
}

// Close closes the rotation manager
func (rm *RotationManager) Close() error {
	if rm.rotator != nil {
		return rm.rotator.Close()
	}
	return nil
}

// isNumeric checks if a string contains only digits
func isNumeric(s string) bool {
	_, err := strconv.Atoi(s)
	return err == nil
}
