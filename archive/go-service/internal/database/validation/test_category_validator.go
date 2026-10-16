package validation

import (
	"errors"
	"strings"

	"go-service/internal/models"
)

// ValidateTestCategory validates a test category before database operations
func ValidateTestCategory(category *models.TestCategory) error {
	if category == nil {
		return errors.New("test category cannot be nil")
	}

	if strings.TrimSpace(category.Name) == "" {
		return errors.New("category name is required")
	}

	if len(category.Name) > 100 {
		return errors.New("category name exceeds maximum length of 100 characters")
	}

	if category.Description != nil && len(*category.Description) > 500 {
		return errors.New("category description exceeds maximum length of 500 characters")
	}

	if category.ParentCategoryID != nil && *category.ParentCategoryID <= 0 {
		return errors.New("parent category ID must be a positive integer if specified")
	}

	return nil
}