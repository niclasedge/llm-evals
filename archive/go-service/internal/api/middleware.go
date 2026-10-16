package api

import (
	"net/http"
	"time"

	"go-service/internal/logging"
)

// CorrelationIDMiddleware injects correlation IDs into request context
func CorrelationIDMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Check for existing correlation ID in headers
		correlationID := r.Header.Get("X-Correlation-ID")
		if correlationID == "" {
			correlationID = logging.NewCorrelationID()
		}

		// Add to request context
		ctx := logging.WithCorrelationID(r.Context(), correlationID)
		r = r.WithContext(ctx)

		// Add to response headers
		w.Header().Set("X-Correlation-ID", correlationID)

		next.ServeHTTP(w, r)
	})
}

// LoggingMiddleware logs HTTP requests with correlation context
func LoggingMiddleware(logger *logging.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()

			// Create a response writer wrapper to capture status code
			wrapper := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

			// Create context-aware logger
			contextLogger := logging.LogWithContext(r.Context(), logger.Logger)

			// Log request start
			contextLogger.Info("HTTP request started",
				"component", "api.middleware",
				"method", r.Method,
				"path", r.URL.Path,
				"remote_addr", r.RemoteAddr,
				"user_agent", r.UserAgent(),
			)

			next.ServeHTTP(wrapper, r)

			duration := time.Since(start)

			// Log request completion
			contextLogger.Info("HTTP request completed",
				"component", "api.middleware",
				"method", r.Method,
				"path", r.URL.Path,
				"status_code", wrapper.statusCode,
				"duration_ms", duration.Milliseconds(),
			)
		})
	}
}

// CORSMiddleware handles CORS headers
func CORSMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// ContentTypeMiddleware ensures proper content type for API endpoints
func ContentTypeMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Set JSON content type for API responses
		if isAPIEndpoint(r.URL.Path) {
			w.Header().Set("Content-Type", "application/json")
		}

		next.ServeHTTP(w, r)
	})
}

// RecoveryMiddleware recovers from panics and returns a proper error response
func RecoveryMiddleware(logger *logging.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if err := recover(); err != nil {
					// Create context-aware logger
					contextLogger := logging.LogWithContext(r.Context(), logger.Logger)
					contextLogger.Error("Panic recovered",
						"component", "api.middleware",
						"error", err,
						"path", r.URL.Path,
						"method", r.Method,
					)
					writeErrorResponse(w, "Internal server error", http.StatusInternalServerError)
				}
			}()

			next.ServeHTTP(w, r)
		})
	}
}

// responseWriter wraps http.ResponseWriter to capture status code
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

// isAPIEndpoint checks if the path is an API endpoint
func isAPIEndpoint(path string) bool {
	return len(path) > 4 && path[:4] == "/api"
}
