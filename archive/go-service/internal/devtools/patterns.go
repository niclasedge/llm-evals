package devtools

import (
	"path/filepath"
	"strings"
)

// DefaultWatchPatterns defines the default file patterns to watch
var DefaultWatchPatterns = []string{
	"**/*.go",   // All Go source files
	"**/go.mod", // Go module files
	"**/go.sum", // Go sum files
}

// DefaultExcludePatterns defines the default exclusion patterns
var DefaultExcludePatterns = []string{
	"**/*_test.go",       // Test files (optional exclusion)
	"**/*.tmp",           // Temporary files
	"**/*~",              // Editor backup files
	"**/.#*",             // Emacs lock files
	"**/bin/**",          // Build output
	"**/tmp/**",          // Temporary directories
	"**/.git/**",         // Git files
	"**/vendor/**",       // Vendor directories
	"**/*.swp",           // Vim swap files
	"**/*.swo",           // Vim swap files
	"**/node_modules/**", // Node.js modules (if present)
	"**/.DS_Store",       // macOS system files
}

// PatternMatcher provides enhanced pattern matching functionality
type PatternMatcher struct {
	patterns []string
}

// NewPatternMatcher creates a new pattern matcher with the given patterns
func NewPatternMatcher(patterns []string) *PatternMatcher {
	return &PatternMatcher{
		patterns: patterns,
	}
}

// Matches checks if a path matches any of the patterns
func (pm *PatternMatcher) Matches(path string) bool {
	for _, pattern := range pm.patterns {
		if pm.matchPattern(path, pattern) {
			return true
		}
	}
	return false
}

// matchPattern checks if a path matches a specific pattern
func (pm *PatternMatcher) matchPattern(path, pattern string) bool {
	// Handle simple glob patterns first
	if !strings.Contains(pattern, "**") {
		matched, _ := filepath.Match(pattern, filepath.Base(path))
		return matched
	}

	// Handle ** patterns for recursive matching
	return pm.matchRecursivePattern(path, pattern)
}

// matchRecursivePattern handles ** glob patterns for recursive directory matching
func (pm *PatternMatcher) matchRecursivePattern(path, pattern string) bool {
	// Normalize paths for comparison
	path = filepath.ToSlash(path)
	pattern = filepath.ToSlash(pattern)

	// Handle patterns with ** in the middle first (like **/vendor/**)
	if strings.Contains(pattern, "**") {
		parts := strings.Split(pattern, "**")

		// Handle patterns like **/vendor/** which split into ["", "/vendor/", ""]
		if len(parts) == 3 && parts[0] == "" && parts[2] == "" {
			dirName := strings.Trim(parts[1], "/")
			if dirName != "" {
				return pm.matchesPathComponent(path, dirName)
			}
		}

		// Handle patterns with two parts like **/ or /**
		if len(parts) == 2 {
			prefix := parts[0]
			suffix := parts[1]

			// For patterns like **/*.go, use suffix matching
			if prefix == "" && suffix != "" {
				return pm.matchesSuffix(path, suffix)
			}

			// For patterns like vendor/**, use prefix matching
			if suffix == "" && prefix != "" {
				return pm.matchesPrefix(path, prefix)
			}

			return pm.matchesPrefixAndSuffix(path, prefix, suffix)
		}
	}

	// Handle patterns starting with **/
	if strings.HasPrefix(pattern, "**/") {
		suffix := strings.TrimPrefix(pattern, "**/")
		return pm.matchesSuffix(path, suffix)
	}

	// Handle patterns ending with /**
	if strings.HasSuffix(pattern, "/**") {
		prefix := strings.TrimSuffix(pattern, "/**")
		return pm.matchesPrefix(path, prefix) || pm.matchesPathComponent(path, prefix)
	}

	// Fallback to simple glob matching
	matched, _ := filepath.Match(pattern, path)
	return matched
}

// matchesSuffix checks if path ends with the given suffix pattern
func (pm *PatternMatcher) matchesSuffix(path, suffix string) bool {
	// Remove leading slash from suffix if present
	suffix = strings.TrimPrefix(suffix, "/")

	// Check direct suffix match
	if strings.HasSuffix(path, suffix) {
		return true
	}

	// Check if any directory component matches
	pathParts := strings.Split(path, "/")
	for i := 0; i < len(pathParts); i++ {
		subPath := strings.Join(pathParts[i:], "/")
		if matched, _ := filepath.Match(suffix, subPath); matched {
			return true
		}
	}

	return false
}

// matchesPrefix checks if path starts with the given prefix pattern
func (pm *PatternMatcher) matchesPrefix(path, prefix string) bool {
	// Remove trailing slash from prefix if present
	prefix = strings.TrimSuffix(prefix, "/")

	return strings.HasPrefix(path, prefix) ||
		strings.HasPrefix(path, prefix+"/")
}

// matchesPrefixAndSuffix checks if path matches both prefix and suffix
func (pm *PatternMatcher) matchesPrefixAndSuffix(path, prefix, suffix string) bool {
	// Remove trailing slash from prefix and leading slash from suffix
	prefix = strings.TrimSuffix(prefix, "/")
	suffix = strings.TrimPrefix(suffix, "/")

	// For patterns like **/vendor/**, prefix is empty and suffix is empty
	// We need to check if the middle part (vendor) is in the path
	if prefix == "" && suffix == "" {
		// Extract the middle part from the original pattern
		// This is a bit of a hack, but for **/vendor/** we want to match vendor
		return false // Will be handled by the broader pattern matching
	}

	// Handle prefix matching
	if prefix != "" && !strings.HasPrefix(path, prefix) {
		return false
	}

	// Handle suffix matching
	if suffix != "" && !strings.HasSuffix(path, suffix) {
		return false
	}

	return true
}

// IsGoSourceFile checks if a file is a Go source file
func IsGoSourceFile(path string) bool {
	return strings.HasSuffix(path, ".go")
}

// IsGoModFile checks if a file is a Go module file
func IsGoModFile(path string) bool {
	base := filepath.Base(path)
	return base == "go.mod" || base == "go.sum"
}

// IsTemporaryFile checks if a file appears to be temporary
func IsTemporaryFile(path string) bool {
	base := filepath.Base(path)

	// Common temporary file patterns
	temporaryPatterns := []string{
		"*.tmp", "*.temp", "*~", ".#*", "*.swp", "*.swo",
		"#*#", "*.bak", "*.backup",
	}

	matcher := NewPatternMatcher(temporaryPatterns)
	return matcher.Matches(base)
}

// ShouldWatchDirectory checks if a directory should be watched
func ShouldWatchDirectory(path string) bool {
	// Normalize path
	path = filepath.ToSlash(path)

	// Get the base directory name
	base := filepath.Base(path)

	// Exclude common directories that shouldn't be watched
	excludeDirs := []string{
		".git", "vendor", "node_modules", "bin", "tmp",
		".idea", ".vscode", "__pycache__",
	}

	for _, dir := range excludeDirs {
		if base == dir {
			return false
		}
		if strings.Contains(path, "/"+dir+"/") || strings.HasSuffix(path, "/"+dir) {
			return false
		}
	}

	return true
}

// matchesPathComponent checks if any path component matches the pattern
func (pm *PatternMatcher) matchesPathComponent(path, pattern string) bool {
	pathParts := strings.Split(path, "/")
	for _, part := range pathParts {
		if part == pattern {
			return true
		}
	}
	return false
}

// MatchesPathComponent is a public helper for debugging
func MatchesPathComponent(path, pattern string) bool {
	pathParts := strings.Split(path, "/")
	for _, part := range pathParts {
		if part == pattern {
			return true
		}
	}
	return false
}
