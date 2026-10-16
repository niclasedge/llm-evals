package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"go-service/internal/api"
	"go-service/internal/logging"
	"go-service/internal/models"
	"go-service/internal/ollama"
)

func TestOllamaProxyIntegration(t *testing.T) {
	// Skip if ENABLE_LOCAL_MODELS is not set
	if os.Getenv("ENABLE_LOCAL_MODELS") != "true" {
		t.Skip("Integration tests require ENABLE_LOCAL_MODELS=true")
	}

	// Create router with Ollama handlers
	logger, _ := logging.NewLogger(logging.Config{LogLevel: "info", DevMode: false})
	router := api.NewRouter(logger)
	server := httptest.NewServer(router)
	defer server.Close()

	// Test health check first
	t.Run("HealthCheck", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/health/ollama")
		if err != nil {
			t.Fatalf("Health check failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}

		var healthResp models.HealthResponse
		if err := json.NewDecoder(resp.Body).Decode(&healthResp); err != nil {
			t.Fatalf("Failed to decode health response: %v", err)
		}

		if healthResp.Status != "healthy" {
			t.Errorf("Expected healthy status, got %s", healthResp.Status)
		}
	})

	// Test listing models
	t.Run("ListModels", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/api/tags")
		if err != nil {
			t.Fatalf("List models failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}

		var tagsResp models.TagsResponse
		if err := json.NewDecoder(resp.Body).Decode(&tagsResp); err != nil {
			t.Fatalf("Failed to decode tags response: %v", err)
		}

		// Should have at least one model for testing
		if len(tagsResp.Models) == 0 {
			t.Error("Expected at least one model to be available")
		}
	})

	// Test enhanced models endpoint
	t.Run("EnhancedModels", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/api/models")
		if err != nil {
			t.Fatalf("Enhanced models failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}

		var enhancedResp map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&enhancedResp); err != nil {
			t.Fatalf("Failed to decode enhanced models response: %v", err)
		}

		// Check for enhanced fields
		if _, exists := enhancedResp["total_count"]; !exists {
			t.Error("Expected total_count field in enhanced response")
		}
		if _, exists := enhancedResp["service"]; !exists {
			t.Error("Expected service field in enhanced response")
		}
	})
}

func TestOllamaClientDirect(t *testing.T) {
	// Skip if ENABLE_LOCAL_MODELS is not set
	if os.Getenv("ENABLE_LOCAL_MODELS") != "true" {
		t.Skip("Integration tests require ENABLE_LOCAL_MODELS=true")
	}

	client := ollama.NewClient()
	ctx := context.Background()

	t.Run("DirectHealthCheck", func(t *testing.T) {
		err := client.HealthCheck(ctx)
		if err != nil {
			t.Fatalf("Direct health check failed: %v", err)
		}
	})

	t.Run("DirectListModels", func(t *testing.T) {
		response, err := client.ListModels(ctx)
		if err != nil {
			t.Fatalf("Direct list models failed: %v", err)
		}

		if len(response.Models) == 0 {
			t.Error("Expected at least one model to be available")
		}

		// Try to find a small test model
		var testModel string
		for _, model := range response.Models {
			if model.Name != "" {
				testModel = model.Name
				break
			}
		}

		if testModel == "" {
			t.Skip("No available models for testing")
		}

		// Test generation with the found model
		t.Run("DirectGenerate", func(t *testing.T) {
			genReq := models.GenerateRequest{
				Model:  testModel,
				Prompt: "Hello",
				Stream: false,
			}

			ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
			defer cancel()

			response, err := client.Generate(ctx, genReq)
			if err != nil {
				t.Fatalf("Direct generate failed: %v", err)
			}

			if response.Response == "" {
				t.Error("Expected non-empty response")
			}

			// Check timing information
			if response.Timing.ResponseTime <= 0 {
				t.Error("Expected positive response time")
			}
			if response.Timing.Timestamp <= 0 {
				t.Error("Expected valid timestamp")
			}
		})

		// Test chat with the found model
		t.Run("DirectChat", func(t *testing.T) {
			chatReq := models.ChatRequest{
				Model: testModel,
				Messages: []models.ChatMessage{
					{Role: "user", Content: "Hello"},
				},
				Stream: false,
			}

			ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
			defer cancel()

			response, err := client.Chat(ctx, chatReq)
			if err != nil {
				t.Fatalf("Direct chat failed: %v", err)
			}

			if response.Message.Content == "" {
				t.Error("Expected non-empty response content")
			}
			if response.Message.Role != "assistant" {
				t.Errorf("Expected assistant role, got %s", response.Message.Role)
			}

			// Check timing information
			if response.Timing.ResponseTime <= 0 {
				t.Error("Expected positive response time")
			}
		})
	})
}

func TestBatchProcessing(t *testing.T) {
	// Skip if ENABLE_LOCAL_MODELS is not set
	if os.Getenv("ENABLE_LOCAL_MODELS") != "true" {
		t.Skip("Integration tests require ENABLE_LOCAL_MODELS=true")
	}

	// Create router and server
	logger, _ := logging.NewLogger(logging.Config{LogLevel: "info", DevMode: false})
	router := api.NewRouter(logger)
	server := httptest.NewServer(router)
	defer server.Close()

	// First get available models
	resp, err := http.Get(server.URL + "/api/tags")
	if err != nil {
		t.Fatalf("Failed to get models: %v", err)
	}
	defer resp.Body.Close()

	var tagsResp models.TagsResponse
	if err := json.NewDecoder(resp.Body).Decode(&tagsResp); err != nil {
		t.Fatalf("Failed to decode tags: %v", err)
	}

	if len(tagsResp.Models) == 0 {
		t.Skip("No models available for batch testing")
	}

	testModel := tagsResp.Models[0].Name

	// Test batch processing
	t.Run("BatchMixedRequests", func(t *testing.T) {
		batchReq := models.BatchRequest{
			Requests: []models.BatchItem{
				{
					ID:   "gen1",
					Type: "generate",
					Payload: models.GenerateRequest{
						Model:  testModel,
						Prompt: "Hello from generate",
						Stream: false,
					},
				},
				{
					ID:   "chat1",
					Type: "chat",
					Payload: models.ChatRequest{
						Model: testModel,
						Messages: []models.ChatMessage{
							{Role: "user", Content: "Hello from chat"},
						},
						Stream: false,
					},
				},
			},
		}

		reqBody, err := json.Marshal(batchReq)
		if err != nil {
			t.Fatalf("Failed to marshal batch request: %v", err)
		}

		resp, err := http.Post(
			server.URL+"/api/batch",
			"application/json",
			bytes.NewBuffer(reqBody),
		)
		if err != nil {
			t.Fatalf("Batch request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}

		var batchResp models.BatchResponse
		if err := json.NewDecoder(resp.Body).Decode(&batchResp); err != nil {
			t.Fatalf("Failed to decode batch response: %v", err)
		}

		if len(batchResp.Results) != 2 {
			t.Errorf("Expected 2 results, got %d", len(batchResp.Results))
		}

		// Check each result
		for _, result := range batchResp.Results {
			if result.Status != "success" {
				t.Errorf("Expected success status, got %s: %s", result.Status, result.Error)
			}
			if result.Result == nil {
				t.Error("Expected non-nil result")
			}
		}
	})
}

func TestErrorHandling(t *testing.T) {
	logger, _ := logging.NewLogger(logging.Config{LogLevel: "info", DevMode: false})
	router := api.NewRouter(logger)
	server := httptest.NewServer(router)
	defer server.Close()

	t.Run("InvalidGenerateRequest", func(t *testing.T) {
		invalidReq := models.GenerateRequest{
			// Missing model and prompt
			Stream: false,
		}

		reqBody, _ := json.Marshal(invalidReq)
		resp, err := http.Post(
			server.URL+"/api/generate",
			"application/json",
			bytes.NewBuffer(reqBody),
		)
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("Expected status 400, got %d", resp.StatusCode)
		}
	})

	t.Run("InvalidChatRequest", func(t *testing.T) {
		invalidReq := models.ChatRequest{
			Model:    "", // Empty model
			Messages: []models.ChatMessage{},
			Stream:   false,
		}

		reqBody, _ := json.Marshal(invalidReq)
		resp, err := http.Post(
			server.URL+"/api/chat",
			"application/json",
			bytes.NewBuffer(reqBody),
		)
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("Expected status 400, got %d", resp.StatusCode)
		}
	})

	t.Run("MethodNotAllowed", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/api/generate")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusMethodNotAllowed {
			t.Errorf("Expected status 405, got %d", resp.StatusCode)
		}
	})
}
