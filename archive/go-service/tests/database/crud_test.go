package database

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"go-service/internal/database"
	"go-service/internal/logging"
	"go-service/internal/models"
)

func setupTestDB(t *testing.T) (*database.DB, *database.Repository) {
	tempDir := t.TempDir()
	dbPath := filepath.Join(tempDir, "test_crud.db")

	config := database.Config{
		Path:           dbPath,
		MaxConnections: 5,
		AutoMigrate:    true,
	}

	db, err := database.NewDB(config)
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	logger, _ := logging.NewLogger(logging.Config{
		LogFile: "logs/test.log",
		DevMode: false,
	})
	repo := database.NewRepository(db, logger)
	return db, repo
}

func createTestResult() *models.EvaluationResult {
	now := time.Now()
	return &models.EvaluationResult{
		Timestamp:        &now,
		ModelProvider:    "openrouter",
		ModelName:        "llama3.2:3b",
		TestName:         "test_fibonacci",
		TestType:         "coding",
		Query:            "Write a function to calculate fibonacci numbers",
		Response:         "def fibonacci(n): ...",
		ExpectedResponse: stringPtr("def fibonacci(n): ..."),
		Metrics:          map[string]float64{"accuracy": 0.95, "completeness": 0.9},
		Score:            0.925,
		Passed:           true,
		ExecutionTime:    1.5,
		ErrorMessage:     nil,
		Metadata:         map[string]interface{}{"language": "python", "difficulty": "easy"},
	}
}

func stringPtr(s string) *string {
	return &s
}

func TestSaveAndGetResult(t *testing.T) {
	db, repo := setupTestDB(t)
	defer db.Close()

	// Create test result
	result := createTestResult()

	// Save result
	if err := repo.SaveResult(context.Background(), result); err != nil {
		t.Fatalf("Failed to save result: %v", err)
	}

	// Check that ID was set
	if result.ID == nil {
		t.Fatal("Result ID was not set after save")
	}

	// Get result by ID
	retrieved, err := repo.GetResult(context.Background(), *result.ID)
	if err != nil {
		t.Fatalf("Failed to get result: %v", err)
	}

	if retrieved == nil {
		t.Fatal("Retrieved result is nil")
	}

	// Compare results
	if retrieved.ModelProvider != result.ModelProvider {
		t.Errorf("ModelProvider mismatch: got %s, want %s", retrieved.ModelProvider, result.ModelProvider)
	}

	if retrieved.ModelName != result.ModelName {
		t.Errorf("ModelName mismatch: got %s, want %s", retrieved.ModelName, result.ModelName)
	}

	if retrieved.Score != result.Score {
		t.Errorf("Score mismatch: got %f, want %f", retrieved.Score, result.Score)
	}

	if retrieved.Passed != result.Passed {
		t.Errorf("Passed mismatch: got %t, want %t", retrieved.Passed, result.Passed)
	}

	// Check metrics
	if len(retrieved.Metrics) != len(result.Metrics) {
		t.Errorf("Metrics length mismatch: got %d, want %d", len(retrieved.Metrics), len(result.Metrics))
	}

	for key, expected := range result.Metrics {
		if actual, exists := retrieved.Metrics[key]; !exists {
			t.Errorf("Missing metric: %s", key)
		} else if actual != expected {
			t.Errorf("Metric %s mismatch: got %f, want %f", key, actual, expected)
		}
	}

	// Check metadata
	if len(retrieved.Metadata) != len(result.Metadata) {
		t.Errorf("Metadata length mismatch: got %d, want %d", len(retrieved.Metadata), len(result.Metadata))
	}
}

func TestSaveResultsBatch(t *testing.T) {
	db, repo := setupTestDB(t)
	defer db.Close()

	// Create multiple test results
	results := []*models.EvaluationResult{
		createTestResult(),
		createTestResult(),
		createTestResult(),
	}

	// Modify some fields to make them different
	results[1].ModelName = "gemma3:27b"
	results[1].Score = 0.85
	results[2].TestType = "vision"
	results[2].Passed = false

	// Save batch
	if err := repo.SaveResultsBatch(context.Background(), results); err != nil {
		t.Fatalf("Failed to save results batch: %v", err)
	}

	// Check that all IDs were set
	for i, result := range results {
		if result.ID == nil {
			t.Errorf("Result %d ID was not set after batch save", i)
		}
	}

	// Verify all results can be retrieved
	for i, result := range results {
		retrieved, err := repo.GetResult(context.Background(), *result.ID)
		if err != nil {
			t.Fatalf("Failed to get result %d: %v", i, err)
		}

		if retrieved == nil {
			t.Fatalf("Retrieved result %d is nil", i)
		}

		if retrieved.Score != result.Score {
			t.Errorf("Result %d score mismatch: got %f, want %f", i, retrieved.Score, result.Score)
		}
	}
}

func TestGetResults(t *testing.T) {
	db, repo := setupTestDB(t)
	defer db.Close()

	// Create test results with different properties
	results := []*models.EvaluationResult{
		createTestResult(),
		createTestResult(),
		createTestResult(),
	}

	results[0].ModelProvider = "ollama"
	results[0].ModelName = "llama3.2:3b"
	results[0].TestType = "coding"

	results[1].ModelProvider = "openrouter"
	results[1].ModelName = "gemma3:27b"
	results[1].TestType = "vision"

	results[2].ModelProvider = "ollama"
	results[2].ModelName = "phi4"
	results[2].TestType = "coding"

	// Save all results
	for _, result := range results {
		if err := repo.SaveResult(context.Background(), result); err != nil {
			t.Fatalf("Failed to save result: %v", err)
		}
	}

	// Test filtering by model provider
	ollamaProvider := "ollama"
	filter := database.GetResultsFilter{
		ModelProvider: &ollamaProvider,
		Limit:         100,
	}

	ollamaResults, err := repo.GetResults(context.Background(), filter)
	if err != nil {
		t.Fatalf("Failed to get ollama results: %v", err)
	}

	if len(ollamaResults) != 2 {
		t.Errorf("Expected 2 ollama results, got %d", len(ollamaResults))
	}

	// Test filtering by test type
	codingType := "coding"
	filter = database.GetResultsFilter{
		TestType: &codingType,
		Limit:    100,
	}

	codingResults, err := repo.GetResults(context.Background(), filter)
	if err != nil {
		t.Fatalf("Failed to get coding results: %v", err)
	}

	if len(codingResults) != 2 {
		t.Errorf("Expected 2 coding results, got %d", len(codingResults))
	}

	// Test limit and offset
	filter = database.GetResultsFilter{
		Limit:  1,
		Offset: 0,
	}

	limitedResults, err := repo.GetResults(context.Background(), filter)
	if err != nil {
		t.Fatalf("Failed to get limited results: %v", err)
	}

	if len(limitedResults) != 1 {
		t.Errorf("Expected 1 limited result, got %d", len(limitedResults))
	}

	// Test time filtering
	now := time.Now()
	past := now.Add(-1 * time.Hour)
	future := now.Add(1 * time.Hour)

	filter = database.GetResultsFilter{
		StartTime: &past,
		EndTime:   &future,
		Limit:     100,
	}

	timeResults, err := repo.GetResults(context.Background(), filter)
	if err != nil {
		t.Fatalf("Failed to get time-filtered results: %v", err)
	}

	if len(timeResults) != 3 {
		t.Errorf("Expected 3 time-filtered results, got %d", len(timeResults))
	}
}

func TestGetSummary(t *testing.T) {
	db, repo := setupTestDB(t)
	defer db.Close()

	// Create test results with different outcomes
	results := []*models.EvaluationResult{
		createTestResult(), // passed
		createTestResult(), // passed
		createTestResult(), // will be failed
		createTestResult(), // will be error
	}

	results[2].Passed = false
	results[2].Score = 0.3

	errorMsg := "Test error"
	results[3].Passed = false
	results[3].Score = 0.0
	results[3].ErrorMessage = &errorMsg

	// Save all results
	for _, result := range results {
		if err := repo.SaveResult(context.Background(), result); err != nil {
			t.Fatalf("Failed to save result: %v", err)
		}
	}

	// Get summary
	filter := database.GetResultsFilter{}
	summary, err := repo.GetSummary(context.Background(), filter)
	if err != nil {
		t.Fatalf("Failed to get summary: %v", err)
	}

	// Check summary statistics
	if summary.TotalEvaluations != 4 {
		t.Errorf("Expected 4 total evaluations, got %d", summary.TotalEvaluations)
	}

	if summary.PassedEvaluations != 2 {
		t.Errorf("Expected 2 passed evaluations, got %d", summary.PassedEvaluations)
	}

	if summary.FailedEvaluations != 1 {
		t.Errorf("Expected 1 failed evaluation, got %d", summary.FailedEvaluations)
	}

	if summary.ErrorEvaluations != 1 {
		t.Errorf("Expected 1 error evaluation, got %d", summary.ErrorEvaluations)
	}

	expectedSuccessRate := 2.0 / 4.0
	if summary.SuccessRate != expectedSuccessRate {
		t.Errorf("Expected success rate %f, got %f", expectedSuccessRate, summary.SuccessRate)
	}

	// Check that models and test types are populated
	if len(summary.ModelsTested) == 0 {
		t.Error("No models in summary")
	}

	if len(summary.TestTypes) == 0 {
		t.Error("No test types in summary")
	}
}

func TestSession(t *testing.T) {
	db, repo := setupTestDB(t)
	defer db.Close()

	// Create test session
	now := time.Now()
	session := &models.EvaluationSession{
		SessionID:      "test-session-123",
		StartedAt:      now,
		CompletedAt:    nil,
		Status:         "running",
		TotalTests:     10,
		CompletedTests: 5,
		Metadata:       map[string]interface{}{"test_suite": "integration", "version": "1.0"},
	}

	// Save session
	if err := repo.SaveSession(context.Background(), session); err != nil {
		t.Fatalf("Failed to save session: %v", err)
	}

	// Check that ID was set
	if session.ID == 0 {
		t.Fatal("Session ID was not set after save")
	}

	// Get session
	retrieved, err := repo.GetSession(context.Background(), session.SessionID)
	if err != nil {
		t.Fatalf("Failed to get session: %v", err)
	}

	if retrieved == nil {
		t.Fatal("Retrieved session is nil")
	}

	// Compare sessions
	if retrieved.SessionID != session.SessionID {
		t.Errorf("SessionID mismatch: got %s, want %s", retrieved.SessionID, session.SessionID)
	}

	if retrieved.Status != session.Status {
		t.Errorf("Status mismatch: got %s, want %s", retrieved.Status, session.Status)
	}

	if retrieved.TotalTests != session.TotalTests {
		t.Errorf("TotalTests mismatch: got %d, want %d", retrieved.TotalTests, session.TotalTests)
	}

	// Update session
	completedAt := time.Now()
	session.CompletedAt = &completedAt
	session.Status = "completed"
	session.CompletedTests = 10

	if err := repo.UpdateSession(context.Background(), session); err != nil {
		t.Fatalf("Failed to update session: %v", err)
	}

	// Get updated session
	updated, err := repo.GetSession(context.Background(), session.SessionID)
	if err != nil {
		t.Fatalf("Failed to get updated session: %v", err)
	}

	if updated.Status != "completed" {
		t.Errorf("Status not updated: got %s, want completed", updated.Status)
	}

	if updated.CompletedTests != 10 {
		t.Errorf("CompletedTests not updated: got %d, want 10", updated.CompletedTests)
	}

	if updated.CompletedAt == nil {
		t.Error("CompletedAt was not set")
	}
}
