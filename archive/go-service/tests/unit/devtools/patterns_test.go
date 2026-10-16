package devtools_test

import (
	"testing"

	"go-service/internal/devtools"
)

func TestPatternMatcher_Matches(t *testing.T) {
	tests := []struct {
		name     string
		patterns []string
		path     string
		want     bool
	}{
		{
			name:     "simple go file",
			patterns: []string{"*.go"},
			path:     "main.go",
			want:     true,
		},
		{
			name:     "non-matching file",
			patterns: []string{"*.go"},
			path:     "main.txt",
			want:     false,
		},
		{
			name:     "recursive go files",
			patterns: []string{"**/*.go"},
			path:     "src/main.go",
			want:     true,
		},
		{
			name:     "deep recursive go files",
			patterns: []string{"**/*.go"},
			path:     "src/pkg/utils/main.go",
			want:     true,
		},
		{
			name:     "go mod file",
			patterns: []string{"**/go.mod"},
			path:     "go.mod",
			want:     true,
		},
		{
			name:     "go mod in subdirectory",
			patterns: []string{"**/go.mod"},
			path:     "module/go.mod",
			want:     true,
		},
		{
			name:     "multiple patterns",
			patterns: []string{"*.go", "*.mod"},
			path:     "go.mod",
			want:     true,
		},
		{
			name:     "no match with multiple patterns",
			patterns: []string{"*.go", "*.mod"},
			path:     "readme.txt",
			want:     false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			matcher := devtools.NewPatternMatcher(tt.patterns)
			if got := matcher.Matches(tt.path); got != tt.want {
				t.Errorf("PatternMatcher.Matches() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestIsGoSourceFile(t *testing.T) {
	tests := []struct {
		name string
		path string
		want bool
	}{
		{"go file", "main.go", true},
		{"go file with path", "src/main.go", true},
		{"go test file", "main_test.go", true},
		{"text file", "readme.txt", false},
		{"no extension", "main", false},
		{"go mod file", "go.mod", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := devtools.IsGoSourceFile(tt.path); got != tt.want {
				t.Errorf("IsGoSourceFile() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestIsGoModFile(t *testing.T) {
	tests := []struct {
		name string
		path string
		want bool
	}{
		{"go.mod", "go.mod", true},
		{"go.sum", "go.sum", true},
		{"go.mod with path", "module/go.mod", true},
		{"go.sum with path", "module/go.sum", true},
		{"go file", "main.go", false},
		{"text file", "readme.txt", false},
		{"mod in name", "gomod.txt", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := devtools.IsGoModFile(tt.path); got != tt.want {
				t.Errorf("IsGoModFile() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestIsTemporaryFile(t *testing.T) {
	tests := []struct {
		name string
		path string
		want bool
	}{
		{"tmp file", "test.tmp", true},
		{"temp file", "test.temp", true},
		{"tilde backup", "test.go~", true},
		{"emacs lock", ".#test.go", true},
		{"vim swap", "test.swp", true},
		{"vim swo", "test.swo", true},
		{"backup file", "test.bak", true},
		{"normal go file", "test.go", false},
		{"normal text file", "readme.txt", false},
		{"tmp in name", "template.go", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := devtools.IsTemporaryFile(tt.path); got != tt.want {
				t.Errorf("IsTemporaryFile() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestShouldWatchDirectory(t *testing.T) {
	tests := []struct {
		name string
		path string
		want bool
	}{
		{"regular directory", "src", true},
		{"regular nested directory", "src/pkg", true},
		{"git directory", ".git", false},
		{"git subdirectory", "project/.git", false},
		{"vendor directory", "vendor", false},
		{"vendor subdirectory", "project/vendor", false},
		{"node_modules", "node_modules", false},
		{"bin directory", "bin", false},
		{"tmp directory", "tmp", false},
		{"idea directory", ".idea", false},
		{"vscode directory", ".vscode", false},
		{"pycache directory", "__pycache__", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := devtools.ShouldWatchDirectory(tt.path); got != tt.want {
				t.Errorf("ShouldWatchDirectory() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestDefaultPatterns(t *testing.T) {
	if len(devtools.DefaultWatchPatterns) == 0 {
		t.Error("DefaultWatchPatterns should not be empty")
	}

	if len(devtools.DefaultExcludePatterns) == 0 {
		t.Error("DefaultExcludePatterns should not be empty")
	}

	// Check that default patterns include essential Go files
	matcher := devtools.NewPatternMatcher(devtools.DefaultWatchPatterns)

	testCases := []string{
		"main.go",
		"src/main.go",
		"go.mod",
		"go.sum",
		"pkg/utils/helper.go",
	}

	for _, testCase := range testCases {
		if !matcher.Matches(testCase) {
			t.Errorf("DefaultWatchPatterns should match %s", testCase)
		}
	}

	// Check that default excludes work properly
	excludeMatcher := devtools.NewPatternMatcher(devtools.DefaultExcludePatterns)

	excludeTestCases := []string{
		"test.tmp",
		"main.go~",
		".#main.go",
		"bin/app",
		"vendor/pkg/lib.go",
		".git/config",
	}

	for _, testCase := range excludeTestCases {
		if !excludeMatcher.Matches(testCase) {
			t.Errorf("DefaultExcludePatterns should match %s", testCase)
		}
	}
}
