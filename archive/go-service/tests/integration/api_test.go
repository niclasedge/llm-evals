package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"go-service/internal/api"
	"go-service/internal/logging"
	"go-service/internal/models"
)

func TestAPIEndpoints(t *testing.T) {
	logger, _ := logging.NewLogger(logging.Config{
		LogFile: "logs/test.log",
		DevMode: false,
	})
	router := api.NewRouter(logger)
	server := httptest.NewServer(router)
	defer server.Close()

	t.Run("HealthEndpoint", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/health")
		if err != nil {
			t.Fatalf("Health request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}

		contentType := resp.Header.Get("Content-Type")
		if contentType != "application/json" {
			t.Errorf("Expected content type application/json, got %s", contentType)
		}
	})

	t.Run("VersionEndpoint", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/api/version")
		if err != nil {
			t.Fatalf("Version request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}
	})

	t.Run("StatusEndpoint", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/api/status")
		if err != nil {
			t.Fatalf("Status request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}
	})

	t.Run("CORSHeaders", func(t *testing.T) {
		req, _ := http.NewRequest("OPTIONS", server.URL+"/api/generate", nil)
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("OPTIONS request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200 for OPTIONS, got %d", resp.StatusCode)
		}

		corsOrigin := resp.Header.Get("Access-Control-Allow-Origin")
		if corsOrigin != "*" {
			t.Errorf("Expected CORS origin *, got %s", corsOrigin)
		}
	})
}

func TestModelInfoEndpoint(t *testing.T) {
	// Skip if ENABLE_LOCAL_MODELS is not set
	if os.Getenv("ENABLE_LOCAL_MODELS") != "true" {
		t.Skip("Integration tests require ENABLE_LOCAL_MODELS=true")
	}

	logger, _ := logging.NewLogger(logging.Config{
		LogFile: "logs/test.log",
		DevMode: false,
	})
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
		t.Skip("No models available for model info testing")
	}

	testModel := tagsResp.Models[0].Name

	t.Run("ModelInfoSuccess", func(t *testing.T) {
		url := server.URL + "/api/models/" + testModel + "/info"
		resp, err := http.Get(url)
		if err != nil {
			t.Fatalf("Model info request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}

		var infoResp map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&infoResp); err != nil {
			t.Fatalf("Failed to decode model info: %v", err)
		}

		// Check required fields
		if name, exists := infoResp["name"]; !exists || name != testModel {
			t.Errorf("Expected name %s, got %v", testModel, name)
		}
	})

	t.Run("ModelInfoNotFound", func(t *testing.T) {
		url := server.URL + "/api/models/nonexistent-model/info"
		resp, err := http.Get(url)
		if err != nil {
			t.Fatalf("Model info request failed: %v", err)
		}
		defer resp.Body.Close()

		// Should return an error (not necessarily 404, might be 500 from Ollama)
		if resp.StatusCode == http.StatusOK {
			t.Error("Expected error status for nonexistent model")
		}
	})
}

func TestRequestValidation(t *testing.T) {
	logger, _ := logging.NewLogger(logging.Config{
		LogFile: "logs/test.log",
		DevMode: false,
	})
	router := api.NewRouter(logger)
	server := httptest.NewServer(router)
	defer server.Close()

	t.Run("EmptyGenerateRequest", func(t *testing.T) {
		resp, err := http.Post(
			server.URL+"/api/generate",
			"application/json",
			bytes.NewBuffer([]byte("{}")),
		)
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("Expected status 400, got %d", resp.StatusCode)
		}
	})

	t.Run("InvalidJSON", func(t *testing.T) {
		resp, err := http.Post(
			server.URL+"/api/generate",
			"application/json",
			bytes.NewBuffer([]byte("invalid json")),
		)
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("Expected status 400, got %d", resp.StatusCode)
		}
	})

	t.Run("MissingContentType", func(t *testing.T) {
		req, _ := http.NewRequest("POST", server.URL+"/api/generate", bytes.NewBuffer([]byte("{}")))
		// Don't set Content-Type
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		// Should still handle the request, might decode as empty JSON
		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("Expected status 400, got %d", resp.StatusCode)
		}
	})
}

func TestMiddleware(t *testing.T) {
	logger, _ := logging.NewLogger(logging.Config{
		LogFile: "logs/test.log",
		DevMode: false,
	})
	router := api.NewRouter(logger)
	server := httptest.NewServer(router)
	defer server.Close()

	t.Run("LoggingMiddleware", func(t *testing.T) {
		// Just test that requests complete without error
		resp, err := http.Get(server.URL + "/health")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}
	})

	t.Run("ContentTypeMiddleware", func(t *testing.T) {
		resp, err := http.Get(server.URL + "/api/tags")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		contentType := resp.Header.Get("Content-Type")
		if contentType != "application/json" {
			t.Errorf("Expected content type application/json, got %s", contentType)
		}
	})

	t.Run("RecoveryMiddleware", func(t *testing.T) {
		// This is harder to test without triggering an actual panic
		// For now, just verify the middleware doesn't break normal operation
		resp, err := http.Get(server.URL + "/health")
		if err != nil {
			t.Fatalf("Request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("Expected status 200, got %d", resp.StatusCode)
		}
	})
}
