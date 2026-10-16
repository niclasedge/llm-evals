package logging_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"go-service/internal/api"
	"go-service/internal/logging"
)

func TestCorrelationIDMiddleware(t *testing.T) {
	tests := []struct {
		name        string
		headerValue string
		expectNew   bool
	}{
		{
			name:        "no_correlation_id_header",
			headerValue: "",
			expectNew:   true,
		},
		{
			name:        "existing_correlation_id_header",
			headerValue: "existing-correlation-123",
			expectNew:   false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create a test handler that captures the correlation ID
			var capturedCorrelationID string
			testHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				capturedCorrelationID = logging.GetCorrelationID(r.Context())
				w.WriteHeader(http.StatusOK)
			})

			// Wrap with correlation middleware
			handler := api.CorrelationIDMiddleware(testHandler)

			// Create test request
			req := httptest.NewRequest("GET", "/test", nil)
			if tt.headerValue != "" {
				req.Header.Set("X-Correlation-ID", tt.headerValue)
			}

			// Create response recorder
			w := httptest.NewRecorder()

			// Execute request
			handler.ServeHTTP(w, req)

			// Verify correlation ID was set in context
			if capturedCorrelationID == "" {
				t.Error("Correlation ID should be set in context")
			}

			// Verify correlation ID handling
			if tt.expectNew {
				if capturedCorrelationID == tt.headerValue {
					t.Error("Should generate new correlation ID when none provided")
				}
			} else {
				if capturedCorrelationID != tt.headerValue {
					t.Errorf("Should use existing correlation ID. Expected: %s, Got: %s",
						tt.headerValue, capturedCorrelationID)
				}
			}

			// Verify correlation ID is set in response header
			responseCorrelationID := w.Header().Get("X-Correlation-ID")
			if responseCorrelationID == "" {
				t.Error("Correlation ID should be set in response header")
			}

			if responseCorrelationID != capturedCorrelationID {
				t.Errorf("Response header correlation ID should match context. Expected: %s, Got: %s",
					capturedCorrelationID, responseCorrelationID)
			}
		})
	}
}

func TestLoggingMiddleware(t *testing.T) {
	// Create temporary logger for testing
	config := logging.Config{
		LogLevel: "info",
		DevMode:  true, // Use stdout for testing
	}
	logger := logging.NewStdoutLogger(config)

	// Create test handler
	testHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// Create correlation context
	ctx := context.Background()
	ctx = logging.WithCorrelationID(ctx, "test-correlation-456")

	// Wrap with logging middleware
	handler := api.LoggingMiddleware(logger)(testHandler)

	// Create test request with context
	req := httptest.NewRequest("GET", "/test", nil)
	req = req.WithContext(ctx)

	// Create response recorder
	w := httptest.NewRecorder()

	// Execute request - this should log with correlation ID
	handler.ServeHTTP(w, req)

	// Verify response
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	if w.Body.String() != "OK" {
		t.Errorf("Expected body 'OK', got %s", w.Body.String())
	}
}

func TestMiddlewareIntegration(t *testing.T) {
	config := logging.Config{
		LogLevel: "info",
		DevMode:  true,
	}
	logger := logging.NewStdoutLogger(config)

	// Create test handler
	testHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Get correlation ID from context
		correlationID := logging.GetCorrelationID(r.Context())
		if correlationID == "" {
			t.Error("Correlation ID should be available in handler context")
		}

		// Use context-aware logging
		contextLogger := logging.LogWithContext(r.Context(), logger.Logger)
		contextLogger.Info("Handler processing request", "path", r.URL.Path)

		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// Chain middlewares: correlation -> logging -> handler
	handler := api.CorrelationIDMiddleware(
		api.LoggingMiddleware(logger)(testHandler),
	)

	// Create test request
	req := httptest.NewRequest("GET", "/api/test", nil)
	w := httptest.NewRecorder()

	// Execute request
	handler.ServeHTTP(w, req)

	// Verify response
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	// Verify correlation ID is in response headers
	correlationID := w.Header().Get("X-Correlation-ID")
	if correlationID == "" {
		t.Error("Correlation ID should be in response headers")
	}
}

func TestRecoveryMiddleware(t *testing.T) {
	config := logging.Config{
		LogLevel: "info",
		DevMode:  true,
	}
	logger := logging.NewStdoutLogger(config)

	// Create panic handler
	panicHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic("test panic")
	})

	// Wrap with recovery middleware
	handler := api.RecoveryMiddleware(logger)(panicHandler)

	// Create test request with correlation ID
	req := httptest.NewRequest("GET", "/test", nil)
	ctx := logging.WithCorrelationID(req.Context(), "panic-test-789")
	req = req.WithContext(ctx)

	w := httptest.NewRecorder()

	// Execute request - should recover from panic
	handler.ServeHTTP(w, req)

	// Verify recovery worked (should return 500 instead of panicking)
	if w.Code != http.StatusInternalServerError {
		t.Errorf("Expected status 500 after panic recovery, got %d", w.Code)
	}
}
