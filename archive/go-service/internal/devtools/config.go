package devtools

import (
	"os"
	"strconv"
	"strings"
	"time"
)

// DevConfig holds development-specific configuration
type DevConfig struct {
	// From previous stories (logging system)
	LogLevel string `env:"LOG_LEVEL" default:"info"`
	DevMode  bool   `env:"DEV_MODE" default:"false"`

	// File watching configuration
	WatchEnabled  bool   `env:"WATCH_ENABLED" default:"true"`
	WatchDir      string `env:"WATCH_DIR" default:"go-service"`
	WatchDebounce int    `env:"WATCH_DEBOUNCE_MS" default:"500"`
	WatchExcludes string `env:"WATCH_EXCLUDES" default:"*.tmp,*~,.#*,*.swp,*.swo"`
	WatchPatterns string `env:"WATCH_PATTERNS" default:"**/*.go,**/go.mod,**/go.sum"`

	// Reload configuration
	GracefulTimeoutSec int `env:"GRACEFUL_TIMEOUT_SEC" default:"10"`
	RestartDelayMs     int `env:"RESTART_DELAY_MS" default:"1000"`
}

// LoadDevConfig loads development configuration from environment variables
func LoadDevConfig() *DevConfig {
	config := &DevConfig{
		LogLevel:           getEnvString("LOG_LEVEL", "info"),
		DevMode:            getEnvBool("DEV_MODE", false),
		WatchEnabled:       getEnvBool("WATCH_ENABLED", true),
		WatchDir:           getEnvString("WATCH_DIR", "go-service"),
		WatchDebounce:      getEnvInt("WATCH_DEBOUNCE_MS", 500),
		WatchExcludes:      getEnvString("WATCH_EXCLUDES", "*.tmp,*~,.#*,*.swp,*.swo,**/bin/**,**/tmp/**,**/.git/**,**/vendor/**"),
		WatchPatterns:      getEnvString("WATCH_PATTERNS", "**/*.go,**/go.mod,**/go.sum"),
		GracefulTimeoutSec: getEnvInt("GRACEFUL_TIMEOUT_SEC", 10),
		RestartDelayMs:     getEnvInt("RESTART_DELAY_MS", 1000),
	}

	return config
}

// ToWatchConfig converts DevConfig to WatchConfig for the file watcher
func (dc *DevConfig) ToWatchConfig() *WatchConfig {
	return &WatchConfig{
		RootDir:    dc.WatchDir,
		Patterns:   strings.Split(dc.WatchPatterns, ","),
		Excludes:   strings.Split(dc.WatchExcludes, ","),
		DebounceMs: dc.WatchDebounce,
	}
}

// getEnvString returns environment variable value or default
func getEnvString(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getEnvBool returns environment variable as boolean or default
func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if parsed, err := strconv.ParseBool(value); err == nil {
			return parsed
		}
	}
	return defaultValue
}

// getEnvInt returns environment variable as integer or default
func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if parsed, err := strconv.Atoi(value); err == nil {
			return parsed
		}
	}
	return defaultValue
}

// GetGracefulTimeout returns graceful timeout as duration
func (dc *DevConfig) GetGracefulTimeout() time.Duration {
	return time.Duration(dc.GracefulTimeoutSec) * time.Second
}

// GetRestartDelay returns restart delay as duration
func (dc *DevConfig) GetRestartDelay() time.Duration {
	return time.Duration(dc.RestartDelayMs) * time.Millisecond
}
