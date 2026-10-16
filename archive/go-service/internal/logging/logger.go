package logging

import (
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"gopkg.in/natefinch/lumberjack.v2"
)

// Config holds logging configuration
type Config struct {
	LogLevel       string `env:"LOG_LEVEL" default:"info"`
	DevMode        bool   `env:"DEV_MODE" default:"false"`
	LogFile        string `env:"LOG_FILE" default:"logs/go-service.log"`
	LogRotateSize  int    `env:"LOG_ROTATE_SIZE" default:"100"` // MB
	LogRotateCount int    `env:"LOG_ROTATE_COUNT" default:"10"` // backup files
	LogRotateAge   int    `env:"LOG_ROTATE_AGE" default:"1"`    // days
}

// Logger wraps slog.Logger with file rotation capabilities
type Logger struct {
	*slog.Logger
	rotator *lumberjack.Logger
	config  Config
}

// NewLogger creates a new logger with file rotation
func NewLogger(config Config) (*Logger, error) {
	// Validate and create log directory
	if err := ensureLogDirectory(config.LogFile); err != nil {
		// Fallback to stdout-only logging
		return NewStdoutLogger(config), nil
	}

	// Create lumberjack rotator
	rotator := &lumberjack.Logger{
		Filename:   config.LogFile,
		MaxSize:    config.LogRotateSize,
		MaxBackups: config.LogRotateCount,
		MaxAge:     config.LogRotateAge,
		Compress:   true,
	}

	// Determine output writer
	var writer io.Writer
	if config.DevMode {
		// Development: file + stdout
		writer = io.MultiWriter(rotator, os.Stdout)
	} else {
		// Production: file only
		writer = rotator
	}

	// Parse log level
	level, err := parseLogLevel(config.LogLevel)
	if err != nil {
		level = slog.LevelInfo
	}

	// Create structured logger
	logger := slog.New(slog.NewJSONHandler(writer, &slog.HandlerOptions{
		Level: level,
	}))

	return &Logger{
		Logger:  logger,
		rotator: rotator,
		config:  config,
	}, nil
}

// NewDefaultLogger creates a logger with default configuration
func NewDefaultLogger() *Logger {
	config := Config{
		LogLevel: "info",
		DevMode:  true,
	}
	return NewStdoutLogger(config)
}

// NewStdoutLogger creates a fallback logger that only outputs to stdout
func NewStdoutLogger(config Config) *Logger {
	level, err := parseLogLevel(config.LogLevel)
	if err != nil {
		level = slog.LevelInfo
	}

	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: level,
	}))

	return &Logger{
		Logger:  logger,
		rotator: nil,
		config:  config,
	}
}

// ensureLogDirectory creates log directory if it doesn't exist
func ensureLogDirectory(logFile string) error {
	dir := filepath.Dir(logFile)

	// Check if directory exists
	if _, err := os.Stat(dir); os.IsNotExist(err) {
		// Create directory with proper permissions
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create log directory %s: %w", dir, err)
		}
	}

	// Test write access
	testFile := filepath.Join(dir, ".write_test")
	if err := os.WriteFile(testFile, []byte("test"), 0644); err != nil {
		return fmt.Errorf("log directory %s is not writable: %w", dir, err)
	}
	os.Remove(testFile)

	return nil
}

// parseLogLevel converts string level to slog.Level
func parseLogLevel(level string) (slog.Level, error) {
	switch level {
	case "debug":
		return slog.LevelDebug, nil
	case "info":
		return slog.LevelInfo, nil
	case "warn", "warning":
		return slog.LevelWarn, nil
	case "error":
		return slog.LevelError, nil
	default:
		return slog.LevelInfo, fmt.Errorf("invalid log level: %s", level)
	}
}

// Close closes the log rotator
func (l *Logger) Close() error {
	if l.rotator != nil {
		return l.rotator.Close()
	}
	return nil
}

// Rotate manually triggers log rotation
func (l *Logger) Rotate() error {
	if l.rotator != nil {
		return l.rotator.Rotate()
	}
	return nil
}
