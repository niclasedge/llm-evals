package api

import (
	"encoding/json"
	"net/http"

	"github.com/gorilla/mux"
	"go-service/internal/database"
	"go-service/internal/health"
	"go-service/internal/logging"
)

// NewRouter creates and configures the HTTP router
func NewRouter(logger *logging.Logger) *mux.Router {
	router := mux.NewRouter()

	// Apply middleware in correct order
	router.Use(CorrelationIDMiddleware)    // First - inject correlation ID
	router.Use(LoggingMiddleware(logger))  // Second - context-aware logging
	router.Use(CORSMiddleware)             // Third - CORS headers
	router.Use(ContentTypeMiddleware)      // Fourth - content type
	router.Use(RecoveryMiddleware(logger)) // Last - recovery with logging

	// Initialize Ollama handler
	ollamaHandler := NewOllamaHandler()

	// Health check endpoints
	router.HandleFunc("/health", HealthHandler(logger)).Methods("GET")
	router.HandleFunc("/health/ollama", ollamaHandler.HandleHealth).Methods("GET")

	// API endpoints
	api := router.PathPrefix("/api").Subrouter()
	api.HandleFunc("/version", VersionHandler(logger)).Methods("GET")
	api.HandleFunc("/status", StatusHandler(logger)).Methods("GET")

	// Core Ollama proxy endpoints
	api.HandleFunc("/generate", ollamaHandler.HandleGenerate).Methods("POST")
	api.HandleFunc("/chat", ollamaHandler.HandleChat).Methods("POST")
	api.HandleFunc("/tags", ollamaHandler.HandleTags).Methods("GET")
	api.HandleFunc("/pull", ollamaHandler.HandlePull).Methods("POST")
	api.HandleFunc("/show", ollamaHandler.HandleShow).Methods("POST")
	api.HandleFunc("/ps", ollamaHandler.HandlePS).Methods("GET")

	// Enhanced endpoints
	api.HandleFunc("/models", ollamaHandler.HandleModels).Methods("GET")
	api.HandleFunc("/models/{model}/info", ollamaHandler.HandleModelInfo).Methods("GET")
	api.HandleFunc("/batch", ollamaHandler.HandleBatch).Methods("POST")

	// Configure method not allowed handler
	router.MethodNotAllowedHandler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		writeErrorResponse(w, "Method not allowed", http.StatusMethodNotAllowed)
	})

	// Handle OPTIONS requests for all API routes
	api.HandleFunc("/{path:.*}", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}
		writeErrorResponse(w, "Not found", http.StatusNotFound)
	}).Methods("OPTIONS")

	return router
}

// NewRouterWithDatabase creates and configures the HTTP router with database support
func NewRouterWithDatabase(db *database.DB, logger *logging.Logger) *mux.Router {
	router := NewRouter(logger)

	// Add database handler
	dbHandler := NewDatabaseHandler(db)
	dbHandler.RegisterRoutes(router)

	return router
}

// HealthHandler handles health check requests
func HealthHandler(logger *logging.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Use context-aware logging
		contextLogger := logging.LogWithContext(r.Context(), logger.Logger)
		contextLogger.Debug("Health check requested")

		healthResponse := health.GetHealth()

		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(healthResponse)

		contextLogger.Debug("Health check completed", "status", "ok")
	}
}

// VersionHandler handles version information requests
func VersionHandler(logger *logging.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Use context-aware logging
		contextLogger := logging.LogWithContext(r.Context(), logger.Logger)
		contextLogger.Debug("Version info requested")

		versionResponse := health.GetVersion()

		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(versionResponse)

		contextLogger.Debug("Version info completed")
	}
}

// StatusHandler handles detailed status requests
func StatusHandler(logger *logging.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Use context-aware logging
		contextLogger := logging.LogWithContext(r.Context(), logger.Logger)
		contextLogger.Debug("Status check requested")

		statusResponse := health.GetStatus()

		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(statusResponse)

		contextLogger.Debug("Status check completed")
	}
}
