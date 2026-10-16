package unit

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"go-service/internal/api"
	"go-service/internal/logging"
	"go-service/internal/models"
)

func TestHealthHandler(t *testing.T) {
	req, err := http.NewRequest("GET", "/health", nil)
	if err != nil {
		t.Fatal(err)
	}

	rr := httptest.NewRecorder()
	logger, _ := logging.NewLogger(logging.Config{LogLevel: "info", DevMode: false})
	router := api.NewRouter(logger)
	router.ServeHTTP(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	var response models.HealthResponse
	err = json.Unmarshal(rr.Body.Bytes(), &response)
	if err != nil {
		t.Errorf("failed to unmarshal response: %v", err)
	}

	if response.Status != "healthy" {
		t.Errorf("expected status 'healthy', got '%s'", response.Status)
	}
}

func TestVersionHandler(t *testing.T) {
	req, err := http.NewRequest("GET", "/api/version", nil)
	if err != nil {
		t.Fatal(err)
	}

	rr := httptest.NewRecorder()
	logger, _ := logging.NewLogger(logging.Config{LogLevel: "info", DevMode: false})
	router := api.NewRouter(logger)
	router.ServeHTTP(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	var response models.VersionResponse
	err = json.Unmarshal(rr.Body.Bytes(), &response)
	if err != nil {
		t.Errorf("failed to unmarshal response: %v", err)
	}

	if response.Version != "1.0.0" {
		t.Errorf("expected version '1.0.0', got '%s'", response.Version)
	}
}

func TestStatusHandler(t *testing.T) {
	req, err := http.NewRequest("GET", "/api/status", nil)
	if err != nil {
		t.Fatal(err)
	}

	rr := httptest.NewRecorder()
	logger, _ := logging.NewLogger(logging.Config{LogLevel: "info", DevMode: false})
	router := api.NewRouter(logger)
	router.ServeHTTP(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	var response models.StatusResponse
	err = json.Unmarshal(rr.Body.Bytes(), &response)
	if err != nil {
		t.Errorf("failed to unmarshal response: %v", err)
	}

	if response.Service != "llm-eval-go-service" {
		t.Errorf("expected service 'llm-eval-go-service', got '%s'", response.Service)
	}

	if response.Status != "running" {
		t.Errorf("expected status 'running', got '%s'", response.Status)
	}
}
