package validation

import (
	"errors"
	"strings"

	"go-service/internal/models"
)

// ValidateTestResult validates a test result before database operations
func ValidateTestResult(result *models.TestResult) error {
	if result == nil {
		return errors.New("test result cannot be nil")
	}

	if result.ExecutionID <= 0 {
		return errors.New("execution ID must be a positive integer")
	}

	if strings.TrimSpace(result.ResultType) == "" {
		return errors.New("result type is required")
	}

	if result.Score != nil && (*result.Score < 0.0 || *result.Score > 1.0) {
		return errors.New("score must be between 0.0 and 1.0")
	}

	validResultTypes := []string{"accuracy", "speed", "quality", "coherence", "relevance", "completeness"}
	if !isValidResultType(result.ResultType, validResultTypes) {
		return errors.New("invalid result type")
	}

	// TestResult doesn't have ExecutionTimeMS field - it's in TestExecution
	// Remove this validation or add it to a different validator if needed

	return nil
}

// isValidResultType checks if a result type is valid
func isValidResultType(resultType string, valid []string) bool {
	for _, v := range valid {
		if resultType == v {
			return true
		}
	}
	return false
}