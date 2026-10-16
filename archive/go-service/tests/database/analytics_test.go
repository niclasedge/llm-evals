package database

import (
	"context"
	"fmt"
	"path/filepath"
	"testing"
	"time"

	"go-service/internal/database"
	"go-service/internal/logging"
	"go-service/internal/models"
)

func TestAnalyticsQueries(t *testing.T) {
	db, repo := setupAnalyticsTestDB(t)
	defer db.Close()

	// Test summary with filtering
	t.Run("Summary with model filtering", func(t *testing.T) {
		llama := "llama3.2:3b"
		filter := database.GetResultsFilter{
			ModelName: &llama,
		}

		summary, err := repo.GetSummary(context.Background(), filter)
		if err != nil {
			t.Fatalf("Failed to get summary: %v", err)
		}

		// Should only include llama results
		if summary.TotalEvaluations != 2 {
			t.Errorf("Expected 2 evaluations for llama, got %d", summary.TotalEvaluations)
		}

		if summary.PassedEvaluations != 2 {
			t.Errorf("Expected 2 passed evaluations for llama, got %d", summary.PassedEvaluations)
		}
	})

	t.Run("Summary with test type filtering", func(t *testing.T) {
		coding := "coding"
		filter := database.GetResultsFilter{
			TestType: &coding,
		}

		summary, err := repo.GetSummary(context.Background(), filter)
		if err != nil {
			t.Fatalf("Failed to get summary: %v", err)
		}

		// Should only include coding results
		if summary.TotalEvaluations != 3 {
			t.Errorf("Expected 3 coding evaluations, got %d", summary.TotalEvaluations)
		}
	})

	t.Run("Summary with time filtering", func(t *testing.T) {
		now := time.Now()
		oneHourAgo := now.Add(-1 * time.Hour)

		filter := database.GetResultsFilter{
			StartTime: &oneHourAgo,
		}

		summary, err := repo.GetSummary(context.Background(), filter)
		if err != nil {
			t.Fatalf("Failed to get summary: %v", err)
		}

		// Should include all recent results
		if summary.TotalEvaluations != 4 {
			t.Errorf("Expected 4 recent evaluations, got %d", summary.TotalEvaluations)
		}
	})

	t.Run("Average calculations", func(t *testing.T) {
		filter := database.GetResultsFilter{}
		summary, err := repo.GetSummary(context.Background(), filter)
		if err != nil {
			t.Fatalf("Failed to get summary: %v", err)
		}

		// Check that averages are calculated correctly
		expectedAvgScore := (0.95 + 0.85 + 0.7 + 0.3) / 4.0
		if summary.AverageScore != expectedAvgScore {
			t.Errorf("Expected average score %f, got %f", expectedAvgScore, summary.AverageScore)
		}

		expectedAvgTime := (1.5 + 2.0 + 1.0 + 0.5) / 4.0
		if summary.AverageExecutionTime != expectedAvgTime {
			t.Errorf("Expected average execution time %f, got %f", expectedAvgTime, summary.AverageExecutionTime)
		}

		expectedSuccessRate := 2.0 / 4.0
		if summary.SuccessRate != expectedSuccessRate {
			t.Errorf("Expected success rate %f, got %f", expectedSuccessRate, summary.SuccessRate)
		}
	})

	t.Run("Models and test types lists", func(t *testing.T) {
		filter := database.GetResultsFilter{}
		summary, err := repo.GetSummary(context.Background(), filter)
		if err != nil {
			t.Fatalf("Failed to get summary: %v", err)
		}

		// Check that unique models are listed
		expectedModels := []string{"ollama/llama3.2:3b", "openrouter/gemma3:27b"}
		if len(summary.ModelsTested) != len(expectedModels) {
			t.Errorf("Expected %d models, got %d", len(expectedModels), len(summary.ModelsTested))
		}

		// Check that unique test types are listed
		expectedTypes := []string{"coding", "vision"}
		if len(summary.TestTypes) != len(expectedTypes) {
			t.Errorf("Expected %d test types, got %d", len(expectedTypes), len(summary.TestTypes))
		}
	})
}

func TestConcurrentAccess(t *testing.T) {
	db, repo := setupAnalyticsTestDB(t)
	defer db.Close()

	// Test concurrent read/write operations
	done := make(chan bool)
	errors := make(chan error, 10)

	// Start multiple goroutines writing data
	for i := 0; i < 5; i++ {
		go func(id int) {
			defer func() { done <- true }()

			result := createTestResult()
			result.TestName = fmt.Sprintf("concurrent_test_%d", id)
			result.Score = float64(id) * 0.1

			if err := repo.SaveResult(context.Background(), result); err != nil {
				errors <- fmt.Errorf("goroutine %d save error: %w", id, err)
				return
			}

			// Try to read the result back
			if result.ID != nil {
				_, err := repo.GetResult(context.Background(), *result.ID)
				if err != nil {
					errors <- fmt.Errorf("goroutine %d read error: %w", id, err)
				}
			}
		}(i)
	}

	// Start multiple goroutines reading data
	for i := 0; i < 3; i++ {
		go func(id int) {
			defer func() { done <- true }()

			filter := database.GetResultsFilter{Limit: 10}
			_, err := repo.GetResults(context.Background(), filter)
			if err != nil {
				errors <- fmt.Errorf("reader %d error: %w", id, err)
			}

			// Get summary
			_, err = repo.GetSummary(context.Background(), filter)
			if err != nil {
				errors <- fmt.Errorf("reader %d summary error: %w", id, err)
			}
		}(i)
	}

	// Wait for all goroutines to complete
	completed := 0
	for completed < 8 {
		select {
		case <-done:
			completed++
		case err := <-errors:
			t.Errorf("Concurrent access error: %v", err)
		case <-time.After(10 * time.Second):
			t.Fatal("Timeout waiting for concurrent operations")
		}
	}

	// Check for any remaining errors
	select {
	case err := <-errors:
		t.Errorf("Additional concurrent access error: %v", err)
	default:
		// No more errors
	}
}

func TestPerformanceUnderLoad(t *testing.T) {
	db, repo := setupAnalyticsTestDB(t)
	defer db.Close()

	// Test performance with larger data set
	numResults := 100
	results := make([]*models.EvaluationResult, numResults)

	for i := 0; i < numResults; i++ {
		result := createTestResult()
		result.TestName = fmt.Sprintf("load_test_%d", i)
		result.Score = float64(i) / float64(numResults)
		results[i] = result
	}

	// Time batch save
	start := time.Now()
	if err := repo.SaveResultsBatch(context.Background(), results); err != nil {
		t.Fatalf("Failed to save batch: %v", err)
	}
	batchSaveTime := time.Since(start)

	t.Logf("Batch save of %d results took: %v", numResults, batchSaveTime)

	// Time summary calculation
	start = time.Now()
	filter := database.GetResultsFilter{}
	summary, err := repo.GetSummary(context.Background(), filter)
	if err != nil {
		t.Fatalf("Failed to get summary: %v", err)
	}
	summaryTime := time.Since(start)

	t.Logf("Summary calculation took: %v", summaryTime)

	// Verify the summary is correct
	expectedTotal := numResults + 4 // 4 from setup
	if summary.TotalEvaluations != expectedTotal {
		t.Errorf("Expected %d total evaluations, got %d", expectedTotal, summary.TotalEvaluations)
	}

	// Time filtered queries
	start = time.Now()
	coding := "coding"
	filter = database.GetResultsFilter{
		TestType: &coding,
		Limit:    50,
	}
	_, err = repo.GetResults(context.Background(), filter)
	if err != nil {
		t.Fatalf("Failed to get filtered results: %v", err)
	}
	queryTime := time.Since(start)

	t.Logf("Filtered query took: %v", queryTime)

	// Performance thresholds (adjust based on requirements)
	if batchSaveTime > 5*time.Second {
		t.Errorf("Batch save too slow: %v", batchSaveTime)
	}

	if summaryTime > 1*time.Second {
		t.Errorf("Summary calculation too slow: %v", summaryTime)
	}

	if queryTime > 500*time.Millisecond {
		t.Errorf("Query too slow: %v", queryTime)
	}
}

func setupAnalyticsTestDB(t *testing.T) (*database.DB, *database.Repository) {
	tempDir := t.TempDir()
	dbPath := filepath.Join(tempDir, "test_analytics.db")

	config := database.Config{
		Path:           dbPath,
		MaxConnections: 10,
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

	// Insert test data
	testResults := []*models.EvaluationResult{
		{
			ModelProvider: "ollama",
			ModelName:     "llama3.2:3b",
			TestName:      "test_1",
			TestType:      "coding",
			Query:         "Test query 1",
			Response:      "Test response 1",
			Score:         0.95,
			Passed:        true,
			ExecutionTime: 1.5,
			Metrics:       map[string]float64{"accuracy": 0.95},
			Metadata:      map[string]interface{}{"language": "python"},
		},
		{
			ModelProvider: "ollama",
			ModelName:     "llama3.2:3b",
			TestName:      "test_2",
			TestType:      "vision",
			Query:         "Test query 2",
			Response:      "Test response 2",
			Score:         0.85,
			Passed:        true,
			ExecutionTime: 2.0,
			Metrics:       map[string]float64{"accuracy": 0.85},
			Metadata:      map[string]interface{}{"image_type": "jpg"},
		},
		{
			ModelProvider: "openrouter",
			ModelName:     "gemma3:27b",
			TestName:      "test_3",
			TestType:      "coding",
			Query:         "Test query 3",
			Response:      "Test response 3",
			Score:         0.7,
			Passed:        false,
			ExecutionTime: 1.0,
			Metrics:       map[string]float64{"accuracy": 0.7},
			Metadata:      map[string]interface{}{"language": "javascript"},
		},
		{
			ModelProvider: "openrouter",
			ModelName:     "gemma3:27b",
			TestName:      "test_4",
			TestType:      "coding",
			Query:         "Test query 4",
			Response:      "Test response 4",
			Score:         0.3,
			Passed:        false,
			ExecutionTime: 0.5,
			Metrics:       map[string]float64{"accuracy": 0.3},
			Metadata:      map[string]interface{}{"language": "go"},
		},
	}

	for _, result := range testResults {
		now := time.Now()
		result.Timestamp = &now
		if err := repo.SaveResult(context.Background(), result); err != nil {
			t.Fatalf("Failed to save test result: %v", err)
		}
	}

	return db, repo
}
