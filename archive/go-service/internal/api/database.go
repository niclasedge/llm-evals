package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/mux"

	"go-service/internal/database"
	"go-service/internal/logging"
	"go-service/internal/models"
)

// DatabaseHandler handles database-related API endpoints
type DatabaseHandler struct {
	db     *database.DB
	repo   *database.Repository
	logger *logging.Logger
}

// NewDatabaseHandler creates a new database handler
func NewDatabaseHandler(db *database.DB) *DatabaseHandler {
	logger := logging.NewDefaultLogger()
	return &DatabaseHandler{
		db:     db,
		repo:   database.NewRepository(db, logger),
		logger: logger,
	}
}

// RegisterRoutes registers database API routes
func (h *DatabaseHandler) RegisterRoutes(router *mux.Router) {
	router.HandleFunc("/api/database/health", h.GetHealth).Methods("GET")
	router.HandleFunc("/api/database/migrate", h.RunMigrations).Methods("POST")
	router.HandleFunc("/api/database/stats", h.GetStats).Methods("GET")

	router.HandleFunc("/api/results", h.GetResults).Methods("GET")
	router.HandleFunc("/api/results", h.CreateResult).Methods("POST")
	router.HandleFunc("/api/results/batch", h.CreateResultsBatch).Methods("POST")
	router.HandleFunc("/api/results/{id}", h.GetResult).Methods("GET")

	router.HandleFunc("/api/results/session/{sessionId}", h.GetResultsBySession).Methods("GET")
	router.HandleFunc("/api/analytics/summary", h.GetSummary).Methods("GET")
	router.HandleFunc("/api/analytics/performance/{model}", h.GetPerformanceAnalytics).Methods("GET")
	router.HandleFunc("/api/analytics/comparison", h.GetModelComparison).Methods("GET")

	router.HandleFunc("/api/sessions", h.CreateSession).Methods("POST")
	router.HandleFunc("/api/sessions/{sessionId}", h.GetSession).Methods("GET")
	router.HandleFunc("/api/sessions/{sessionId}", h.UpdateSession).Methods("PUT")
}

// GetHealth checks database connectivity
func (h *DatabaseHandler) GetHealth(w http.ResponseWriter, r *http.Request) {
	if err := h.db.Health(); err != nil {
		http.Error(w, fmt.Sprintf("Database health check failed: %v", err), http.StatusServiceUnavailable)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// RunMigrations runs database migrations
func (h *DatabaseHandler) RunMigrations(w http.ResponseWriter, r *http.Request) {
	if err := h.db.Migrate(); err != nil {
		http.Error(w, fmt.Sprintf("Migration failed: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "migrations completed"})
}

// GetStats returns database statistics
func (h *DatabaseHandler) GetStats(w http.ResponseWriter, r *http.Request) {
	stats, err := h.db.GetStats()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get stats: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// GetResults retrieves evaluation results with optional filtering
func (h *DatabaseHandler) GetResults(w http.ResponseWriter, r *http.Request) {
	contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
	contextLogger.Debug("Getting evaluation results")

	filter := database.GetResultsFilter{
		Limit: 100, // Default limit
	}

	// Parse query parameters
	if provider := r.URL.Query().Get("model_provider"); provider != "" {
		filter.ModelProvider = &provider
	}

	if model := r.URL.Query().Get("model_name"); model != "" {
		filter.ModelName = &model
	}

	if testType := r.URL.Query().Get("test_type"); testType != "" {
		filter.TestType = &testType
	}

	if startTime := r.URL.Query().Get("start_time"); startTime != "" {
		if t, err := time.Parse(time.RFC3339, startTime); err == nil {
			filter.StartTime = &t
		}
	}

	if endTime := r.URL.Query().Get("end_time"); endTime != "" {
		if t, err := time.Parse(time.RFC3339, endTime); err == nil {
			filter.EndTime = &t
		}
	}

	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if limit, err := strconv.Atoi(limitStr); err == nil && limit > 0 {
			filter.Limit = limit
		}
	}

	if offsetStr := r.URL.Query().Get("offset"); offsetStr != "" {
		if offset, err := strconv.Atoi(offsetStr); err == nil && offset >= 0 {
			filter.Offset = offset
		}
	}

	results, err := h.repo.GetResults(r.Context(), filter)
	if err != nil {
		contextLogger.Error("Failed to get results", "error", err, "filter", filter)
		http.Error(w, fmt.Sprintf("Failed to get results: %v", err), http.StatusInternalServerError)
		return
	}

	contextLogger.Debug("Successfully retrieved evaluation results", "count", len(results))
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(results)
}

// CreateResult creates a new evaluation result
func (h *DatabaseHandler) CreateResult(w http.ResponseWriter, r *http.Request) {
	var result models.EvaluationResult
	if err := json.NewDecoder(r.Body).Decode(&result); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	if err := h.repo.SaveResult(r.Context(), &result); err != nil {
		contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
		contextLogger.Error("Failed to save result", "error", err)
		http.Error(w, fmt.Sprintf("Failed to save result: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(result)
}

// CreateResultsBatch creates multiple evaluation results
func (h *DatabaseHandler) CreateResultsBatch(w http.ResponseWriter, r *http.Request) {
	var results []*models.EvaluationResult
	if err := json.NewDecoder(r.Body).Decode(&results); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	if err := h.repo.SaveResultsBatch(r.Context(), results); err != nil {
		contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
		contextLogger.Error("Failed to save results batch", "error", err, "count", len(results))
		http.Error(w, fmt.Sprintf("Failed to save results: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(results)
}

// GetResult retrieves a specific evaluation result by ID
func (h *DatabaseHandler) GetResult(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	idStr := vars["id"]

	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, "Invalid result ID", http.StatusBadRequest)
		return
	}

	result, err := h.repo.GetResult(r.Context(), id)
	if err != nil {
		contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
		contextLogger.Error("Failed to get result", "error", err, "id", id)
		http.Error(w, fmt.Sprintf("Failed to get result: %v", err), http.StatusInternalServerError)
		return
	}

	if result == nil {
		http.Error(w, "Result not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

// GetResultsBySession retrieves results for a specific session
func (h *DatabaseHandler) GetResultsBySession(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	sessionID := vars["sessionId"]

	// For now, this would require extending the schema to link results to sessions
	// This is a placeholder implementation that returns all results
	// In a real implementation, you would filter by session_id
	_ = sessionID // Acknowledge the sessionID variable

	filter := database.GetResultsFilter{
		Limit: 1000, // Higher limit for session results
	}

	results, err := h.repo.GetResults(r.Context(), filter)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get results: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(results)
}

// GetSummary retrieves evaluation summary statistics
func (h *DatabaseHandler) GetSummary(w http.ResponseWriter, r *http.Request) {
	filter := database.GetResultsFilter{}

	// Parse query parameters for filtering
	if provider := r.URL.Query().Get("model_provider"); provider != "" {
		filter.ModelProvider = &provider
	}

	if model := r.URL.Query().Get("model_name"); model != "" {
		filter.ModelName = &model
	}

	if testType := r.URL.Query().Get("test_type"); testType != "" {
		filter.TestType = &testType
	}

	summary, err := h.repo.GetSummary(r.Context(), filter)
	if err != nil {
		contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
		contextLogger.Error("Failed to get summary", "error", err, "filter", filter)
		http.Error(w, fmt.Sprintf("Failed to get summary: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(summary)
}

// GetPerformanceAnalytics retrieves performance analytics for a model
func (h *DatabaseHandler) GetPerformanceAnalytics(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	modelName := vars["model"]

	// Parse model name to provider and name if it contains "/"
	var filter database.GetResultsFilter
	if parts := strings.Split(modelName, "/"); len(parts) == 2 {
		filter.ModelProvider = &parts[0]
		filter.ModelName = &parts[1]
	} else {
		filter.ModelName = &modelName
	}

	summary, err := h.repo.GetSummary(r.Context(), filter)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get performance analytics: %v", err), http.StatusInternalServerError)
		return
	}

	analytics := map[string]interface{}{
		"model_name":             modelName,
		"total_evaluations":      summary.TotalEvaluations,
		"success_rate":           summary.SuccessRate,
		"average_score":          summary.AverageScore,
		"average_execution_time": summary.AverageExecutionTime,
		"passed_evaluations":     summary.PassedEvaluations,
		"failed_evaluations":     summary.FailedEvaluations,
		"error_evaluations":      summary.ErrorEvaluations,
		"test_types":             summary.TestTypes,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(analytics)
}

// GetModelComparison compares performance between multiple models
func (h *DatabaseHandler) GetModelComparison(w http.ResponseWriter, r *http.Request) {
	modelsParam := r.URL.Query().Get("models")
	if modelsParam == "" {
		http.Error(w, "Models parameter is required", http.StatusBadRequest)
		return
	}

	models := strings.Split(modelsParam, ",")
	comparison := make(map[string]interface{})

	for _, modelName := range models {
		var filter database.GetResultsFilter
		if parts := strings.Split(strings.TrimSpace(modelName), "/"); len(parts) == 2 {
			filter.ModelProvider = &parts[0]
			filter.ModelName = &parts[1]
		} else {
			modelName = strings.TrimSpace(modelName)
			filter.ModelName = &modelName
		}

		summary, err := h.repo.GetSummary(r.Context(), filter)
		if err != nil {
			http.Error(w, fmt.Sprintf("Failed to get summary for model %s: %v", modelName, err), http.StatusInternalServerError)
			return
		}

		comparison[modelName] = map[string]interface{}{
			"total_evaluations":      summary.TotalEvaluations,
			"success_rate":           summary.SuccessRate,
			"average_score":          summary.AverageScore,
			"average_execution_time": summary.AverageExecutionTime,
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(comparison)
}

// CreateSession creates a new evaluation session
func (h *DatabaseHandler) CreateSession(w http.ResponseWriter, r *http.Request) {
	var session models.EvaluationSession
	if err := json.NewDecoder(r.Body).Decode(&session); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	if err := h.repo.SaveSession(r.Context(), &session); err != nil {
		contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
		contextLogger.Error("Failed to save session", "error", err, "session_id", session.SessionID)
		http.Error(w, fmt.Sprintf("Failed to save session: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(session)
}

// GetSession retrieves an evaluation session
func (h *DatabaseHandler) GetSession(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	sessionID := vars["sessionId"]

	session, err := h.repo.GetSession(r.Context(), sessionID)
	if err != nil {
		contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
		contextLogger.Error("Failed to get session", "error", err, "session_id", sessionID)
		http.Error(w, fmt.Sprintf("Failed to get session: %v", err), http.StatusInternalServerError)
		return
	}

	if session == nil {
		http.Error(w, "Session not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(session)
}

// UpdateSession updates an evaluation session
func (h *DatabaseHandler) UpdateSession(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	sessionID := vars["sessionId"]

	var session models.EvaluationSession
	if err := json.NewDecoder(r.Body).Decode(&session); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	session.SessionID = sessionID
	if err := h.repo.UpdateSession(r.Context(), &session); err != nil {
		contextLogger := logging.LogWithContext(r.Context(), h.logger.Logger)
		contextLogger.Error("Failed to update session", "error", err, "session_id", sessionID)
		http.Error(w, fmt.Sprintf("Failed to update session: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(session)
}
