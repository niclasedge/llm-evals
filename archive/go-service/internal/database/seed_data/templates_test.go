package seed_data

import (
	"context"
	"testing"

	"go-service/internal/database"
)

func TestValidateSeedData(t *testing.T) {
	// Create test database
	config := database.Config{
		Path:           ":memory:",
		MaxConnections: 1,
		AutoMigrate:    true,
	}

	db, err := database.NewDB(config)
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}
	defer db.Close()

	repo := database.NewRepository(db, nil)
	ctx := context.Background()

	// Test validation - should pass after migrations
	err = ValidateSeedData(ctx, repo)
	if err != nil {
		t.Errorf("Seed data validation failed: %v", err)
	}
}

func TestProcessTemplate(t *testing.T) {
	template := "Write a {language} function that {task_description}."
	variables := map[string]interface{}{
		"language":         "Python",
		"task_description": "sorts an array",
	}

	result, err := ProcessTemplate(template, variables)
	if err != nil {
		t.Fatalf("ProcessTemplate failed: %v", err)
	}

	expected := "Write a Python function that sorts an array."
	if result != expected {
		t.Errorf("Expected %q, got %q", expected, result)
	}
}

func TestGetCodingPromptExample(t *testing.T) {
	variables := GetCodingPromptExample()
	
	// Check that all required variables are present
	requiredKeys := []string{"language", "task_description", "function_name", "additional_requirements", "usage_example"}
	for _, key := range requiredKeys {
		if _, exists := variables[key]; !exists {
			t.Errorf("Missing required variable: %s", key)
		}
	}
}

func TestGeneratePrompt(t *testing.T) {
	// Create test database
	config := database.Config{
		Path:           ":memory:",
		MaxConnections: 1,
		AutoMigrate:    true,
	}

	db, err := database.NewDB(config)
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}
	defer db.Close()

	repo := database.NewRepository(db, nil)
	ctx := context.Background()

	// Test generating prompt for coding category (ID 1)
	variables := GetCodingPromptExample()
	prompt, err := GeneratePrompt(ctx, repo, 1, variables)
	if err != nil {
		t.Fatalf("GeneratePrompt failed: %v", err)
	}

	// Verify the prompt contains substituted variables
	if len(prompt) == 0 {
		t.Error("Generated prompt is empty")
	}

	// Check that variables were substituted
	expectedSubstitutions := []string{"Python", "merge_sort", "sorts an array"}
	for _, expected := range expectedSubstitutions {
		if !contains(prompt, expected) {
			t.Errorf("Generated prompt missing expected substitution: %s", expected)
		}
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && 
		(s[:len(substr)] == substr || s[len(s)-len(substr):] == substr || 
		 indexOf(s, substr) >= 0))
}

func indexOf(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}