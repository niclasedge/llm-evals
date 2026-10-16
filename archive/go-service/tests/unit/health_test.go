package unit

import (
	"testing"

	"go-service/internal/health"
)

func TestGetHealth(t *testing.T) {
	response := health.GetHealth()

	if response.Status != "healthy" {
		t.Errorf("expected status 'healthy', got '%s'", response.Status)
	}

	if response.Timestamp.IsZero() {
		t.Error("expected timestamp to be set")
	}

	if response.Uptime == "" {
		t.Error("expected uptime to be set")
	}
}

func TestGetVersion(t *testing.T) {
	response := health.GetVersion()

	if response.Version != "1.0.0" {
		t.Errorf("expected version '1.0.0', got '%s'", response.Version)
	}

	if response.GoVersion == "" {
		t.Error("expected Go version to be set")
	}
}

func TestGetStatus(t *testing.T) {
	response := health.GetStatus()

	if response.Service != "llm-eval-go-service" {
		t.Errorf("expected service 'llm-eval-go-service', got '%s'", response.Service)
	}

	if response.Status != "running" {
		t.Errorf("expected status 'running', got '%s'", response.Status)
	}

	if response.Version != "1.0.0" {
		t.Errorf("expected version '1.0.0', got '%s'", response.Version)
	}

	if response.Timestamp.IsZero() {
		t.Error("expected timestamp to be set")
	}

	if response.Uptime == "" {
		t.Error("expected uptime to be set")
	}

	if response.Memory == "" {
		t.Error("expected memory info to be set")
	}
}
