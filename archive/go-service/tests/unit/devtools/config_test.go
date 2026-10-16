package devtools_test

import (
	"os"
	"testing"

	"go-service/internal/devtools"
)

func TestLoadDevConfig(t *testing.T) {
	// Save original environment
	originalEnv := make(map[string]string)
	envKeys := []string{
		"LOG_LEVEL", "DEV_MODE", "WATCH_ENABLED", "WATCH_DIR",
		"WATCH_DEBOUNCE_MS", "WATCH_EXCLUDES", "WATCH_PATTERNS",
	}

	for _, key := range envKeys {
		originalEnv[key] = os.Getenv(key)
		os.Unsetenv(key)
	}

	defer func() {
		for key, value := range originalEnv {
			if value != "" {
				os.Setenv(key, value)
			} else {
				os.Unsetenv(key)
			}
		}
	}()

	// Test default values
	config := devtools.LoadDevConfig()

	if config.LogLevel != "info" {
		t.Errorf("Expected LogLevel to be 'info', got %s", config.LogLevel)
	}

	if config.DevMode != false {
		t.Errorf("Expected DevMode to be false, got %v", config.DevMode)
	}

	if config.WatchEnabled != true {
		t.Errorf("Expected WatchEnabled to be true, got %v", config.WatchEnabled)
	}

	if config.WatchDir != "go-service" {
		t.Errorf("Expected WatchDir to be 'go-service', got %s", config.WatchDir)
	}

	if config.WatchDebounce != 500 {
		t.Errorf("Expected WatchDebounce to be 500, got %d", config.WatchDebounce)
	}

	// Test environment variable overrides
	os.Setenv("LOG_LEVEL", "debug")
	os.Setenv("DEV_MODE", "true")
	os.Setenv("WATCH_ENABLED", "false")
	os.Setenv("WATCH_DIR", "./custom")
	os.Setenv("WATCH_DEBOUNCE_MS", "1000")
	os.Setenv("WATCH_EXCLUDES", "*.test,*.bak")
	os.Setenv("WATCH_PATTERNS", "*.go,*.yaml")

	config = devtools.LoadDevConfig()

	if config.LogLevel != "debug" {
		t.Errorf("Expected LogLevel to be 'debug', got %s", config.LogLevel)
	}

	if config.DevMode != true {
		t.Errorf("Expected DevMode to be true, got %v", config.DevMode)
	}

	if config.WatchEnabled != false {
		t.Errorf("Expected WatchEnabled to be false, got %v", config.WatchEnabled)
	}

	if config.WatchDir != "./custom" {
		t.Errorf("Expected WatchDir to be './custom', got %s", config.WatchDir)
	}

	if config.WatchDebounce != 1000 {
		t.Errorf("Expected WatchDebounce to be 1000, got %d", config.WatchDebounce)
	}

	if config.WatchExcludes != "*.test,*.bak" {
		t.Errorf("Expected WatchExcludes to be '*.test,*.bak', got %s", config.WatchExcludes)
	}

	if config.WatchPatterns != "*.go,*.yaml" {
		t.Errorf("Expected WatchPatterns to be '*.go,*.yaml', got %s", config.WatchPatterns)
	}
}

func TestDevConfig_ToWatchConfig(t *testing.T) {
	devConfig := &devtools.DevConfig{
		WatchDir:      "./test",
		WatchDebounce: 1000,
		WatchExcludes: "*.tmp,*.bak",
		WatchPatterns: "*.go,*.mod",
	}

	watchConfig := devConfig.ToWatchConfig()

	if watchConfig.RootDir != "./test" {
		t.Errorf("Expected RootDir to be './test', got %s", watchConfig.RootDir)
	}

	if watchConfig.DebounceMs != 1000 {
		t.Errorf("Expected DebounceMs to be 1000, got %d", watchConfig.DebounceMs)
	}

	expectedPatterns := []string{"*.go", "*.mod"}
	if len(watchConfig.Patterns) != len(expectedPatterns) {
		t.Errorf("Expected %d patterns, got %d", len(expectedPatterns), len(watchConfig.Patterns))
	}

	for i, pattern := range expectedPatterns {
		if i >= len(watchConfig.Patterns) || watchConfig.Patterns[i] != pattern {
			t.Errorf("Expected pattern[%d] to be %s, got %s", i, pattern, watchConfig.Patterns[i])
		}
	}

	expectedExcludes := []string{"*.tmp", "*.bak"}
	if len(watchConfig.Excludes) != len(expectedExcludes) {
		t.Errorf("Expected %d excludes, got %d", len(expectedExcludes), len(watchConfig.Excludes))
	}

	for i, exclude := range expectedExcludes {
		if i >= len(watchConfig.Excludes) || watchConfig.Excludes[i] != exclude {
			t.Errorf("Expected exclude[%d] to be %s, got %s", i, exclude, watchConfig.Excludes[i])
		}
	}
}

func TestEnvironmentVariableParsing(t *testing.T) {
	// Save original environment
	originalEnv := make(map[string]string)
	envKeys := []string{"TEST_BOOL", "TEST_INT", "TEST_STRING"}

	for _, key := range envKeys {
		originalEnv[key] = os.Getenv(key)
		os.Unsetenv(key)
	}

	defer func() {
		for key, value := range originalEnv {
			if value != "" {
				os.Setenv(key, value)
			} else {
				os.Unsetenv(key)
			}
		}
	}()

	// Test boolean parsing
	testCases := []struct {
		name     string
		envValue string
		expected bool
	}{
		{"true", "true", true},
		{"false", "false", false},
		{"1", "1", true},
		{"0", "0", false},
		{"TRUE", "TRUE", true},
		{"FALSE", "FALSE", false},
	}

	for _, tc := range testCases {
		t.Run("bool_"+tc.name, func(t *testing.T) {
			os.Setenv("DEV_MODE", tc.envValue)
			config := devtools.LoadDevConfig()
			if config.DevMode != tc.expected {
				t.Errorf("Expected DevMode to be %v for value %s, got %v", tc.expected, tc.envValue, config.DevMode)
			}
		})
	}

	// Test integer parsing
	intTestCases := []struct {
		name     string
		envValue string
		expected int
	}{
		{"valid_number", "1000", 1000},
		{"zero", "0", 0},
		{"negative", "-1", -1},
	}

	for _, tc := range intTestCases {
		t.Run("int_"+tc.name, func(t *testing.T) {
			os.Setenv("WATCH_DEBOUNCE_MS", tc.envValue)
			config := devtools.LoadDevConfig()
			if config.WatchDebounce != tc.expected {
				t.Errorf("Expected WatchDebounce to be %d for value %s, got %d", tc.expected, tc.envValue, config.WatchDebounce)
			}
		})
	}

	// Test invalid values fall back to defaults
	os.Setenv("DEV_MODE", "invalid")
	os.Setenv("WATCH_DEBOUNCE_MS", "invalid")

	config := devtools.LoadDevConfig()
	if config.DevMode != false {
		t.Error("Invalid boolean should fall back to default false")
	}
	if config.WatchDebounce != 500 {
		t.Error("Invalid integer should fall back to default 500")
	}
}
