package validation

import (
	"errors"
	"strings"

	"go-service/internal/models"
)

// ValidateTestExecution validates a test execution before database operations
func ValidateTestExecution(execution *models.TestExecution) error {
	if execution == nil {
		return errors.New("test execution cannot be nil")
	}

	if strings.TrimSpace(execution.TestType) == "" {
		return errors.New("test type is required")
	}

	if strings.TrimSpace(execution.ModelName) == "" {
		return errors.New("model name is required")
	}

	if strings.TrimSpace(execution.Prompt) == "" {
		return errors.New("prompt is required")
	}

	if len(execution.Prompt) > 10000 {
		return errors.New("prompt exceeds maximum length of 10000 characters")
	}

	validStatuses := []string{"pending", "running", "completed", "failed", "cancelled"}
	if !isValidStatus(execution.Status, validStatuses) {
		return errors.New("invalid status value")
	}

	if execution.Score != nil && (*execution.Score < 0.0 || *execution.Score > 1.0) {
		return errors.New("score must be between 0.0 and 1.0")
	}

	if execution.ExecutionTimeMS != nil && *execution.ExecutionTimeMS < 0 {
		return errors.New("execution time cannot be negative")
	}

	return nil
}

// isValidStatus checks if a status is in the list of valid statuses
func isValidStatus(status string, valid []string) bool {
	for _, v := range valid {
		if status == v {
			return true
		}
	}
	return false
}