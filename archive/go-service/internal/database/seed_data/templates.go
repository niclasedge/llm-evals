package seed_data

import (
	"context"
	"fmt"
	"strings"

	"go-service/internal/database"
	"go-service/internal/models"
)

// PromptTemplate represents a test category prompt template with variables
type PromptTemplate struct {
	Template  string            `json:"template"`
	Variables map[string]string `json:"variables"`
	Examples  []TemplateExample `json:"examples"`
}

// TemplateExample shows how to use a template with example variables
type TemplateExample struct {
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Variables   map[string]string `json:"variables"`
	Expected    string            `json:"expected"`
}

// ProcessTemplate processes a template string with variables and returns the final prompt
func ProcessTemplate(templateStr string, variables map[string]interface{}) (string, error) {
	// Use simple string replacement for variable substitution
	result := templateStr
	for key, value := range variables {
		placeholder := "{" + key + "}"
		replacement := fmt.Sprintf("%v", value)
		result = strings.ReplaceAll(result, placeholder, replacement)
	}
	return result, nil
}

// GeneratePrompt generates a prompt for a specific category with variables
func GeneratePrompt(ctx context.Context, repo *database.Repository, categoryID int64, variables map[string]interface{}) (string, error) {
	category, err := repo.GetTestCategory(ctx, categoryID)
	if err != nil {
		return "", fmt.Errorf("failed to get test category %d: %w", categoryID, err)
	}

	if category.TemplatePrompt == nil || *category.TemplatePrompt == "" {
		return "", fmt.Errorf("category %s has no template prompt", category.Name)
	}

	return ProcessTemplate(*category.TemplatePrompt, variables)
}

// ValidateSeedData validates that all required seed data categories are present
func ValidateSeedData(ctx context.Context, repo *database.Repository) error {
	categories, err := repo.GetTestCategories(ctx)
	if err != nil {
		return fmt.Errorf("failed to get test categories: %w", err)
	}

	expectedCategories := []string{"coding", "reasoning", "creative", "tool-calling"}

	for _, expected := range expectedCategories {
		found := false
		for _, category := range categories {
			if category.Name == expected {
				found = true

				// Validate required fields
				if category.TemplatePrompt == nil || *category.TemplatePrompt == "" {
					return fmt.Errorf("category %s missing template prompt", expected)
				}

				if category.DefaultParameters == nil {
					return fmt.Errorf("category %s missing default parameters", expected)
				}

				if category.ScoringCriteria == nil {
					return fmt.Errorf("category %s missing scoring criteria", expected)
				}

				break
			}
		}

		if !found {
			return fmt.Errorf("required category %s not found", expected)
		}
	}

	return nil
}

// GetCodingPromptExample returns example variables for coding category templates
func GetCodingPromptExample() map[string]interface{} {
	return map[string]interface{}{
		"language":               "Python",
		"task_description":       "sorts an array of integers using merge sort algorithm",
		"function_name":          "merge_sort",
		"additional_requirements": "Handle empty arrays and arrays with one element",
		"usage_example":          "result = merge_sort([3, 1, 4, 1, 5, 9, 2, 6])\nprint(result)  # [1, 1, 2, 3, 4, 5, 6, 9]",
	}
}

// GetReasoningPromptExample returns example variables for reasoning category templates
func GetReasoningPromptExample() map[string]interface{} {
	return map[string]interface{}{
		"scenario": "A company has 100 employees and wants to implement a 4-day work week. Productivity studies show that shorter work weeks can increase efficiency by 20%, but some tasks require longer continuous focus periods.",
		"question": "Should the company implement the 4-day work week? What factors should they consider?",
	}
}

// GetCreativePromptExample returns example variables for creative category templates
func GetCreativePromptExample() map[string]interface{} {
	return map[string]interface{}{
		"content_type":       "short story",
		"theme":              "time travel",
		"style":              "science fiction",
		"audience":           "young adults",
		"length_requirement": "approximately 500 words",
		"constraints":        "The protagonist must make a difficult moral choice",
	}
}

// GetToolCallingPromptExample returns example variables for tool-calling category templates
func GetToolCallingPromptExample() map[string]interface{} {
	return map[string]interface{}{
		"available_tools": `1. weather_api(location: string) -> WeatherData
2. currency_converter(amount: float, from_currency: string, to_currency: string) -> float
3. search_web(query: string) -> SearchResults`,
		"task_description": "Help a user plan a trip to Tokyo next week by checking the weather forecast and converting $1000 USD to Japanese Yen",
	}
}

// CreateTestExecution creates a test execution record from a category and variables
func CreateTestExecution(ctx context.Context, repo *database.Repository, categoryID int64, modelName string, variables map[string]interface{}) (*models.TestExecution, error) {
	category, err := repo.GetTestCategory(ctx, categoryID)
	if err != nil {
		return nil, fmt.Errorf("failed to get category: %w", err)
	}

	prompt, err := GeneratePrompt(ctx, repo, categoryID, variables)
	if err != nil {
		return nil, fmt.Errorf("failed to generate prompt: %w", err)
	}

	execution := &models.TestExecution{
		TestType:      category.Name,
		TestCategory:  &category.DisplayName,
		TestName:      nil, // Can be set by caller
		ModelName:     modelName,
		ModelProvider: nil, // Will be determined by model name
		Prompt:        prompt,
		Parameters:    category.DefaultParameters,
		Status:        "pending",
		Environment:   "development",
	}

	err = repo.CreateTestExecution(ctx, execution)
	if err != nil {
		return nil, fmt.Errorf("failed to create test execution: %w", err)
	}

	return execution, nil
}