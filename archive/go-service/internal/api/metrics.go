package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gorilla/mux"
	"go-service/internal/monitoring"
)

// MetricsHandler handles metrics-related API endpoints
type MetricsHandler struct {
	metrics   *monitoring.MetricsCollector
	analytics *monitoring.AnalyticsService
}

// NewMetricsHandler creates a new metrics handler
func NewMetricsHandler(metrics *monitoring.MetricsCollector, analytics *monitoring.AnalyticsService) *MetricsHandler {
	return &MetricsHandler{
		metrics:   metrics,
		analytics: analytics,
	}
}

// GetMetricsSummary returns a summary of current metrics
func (h *MetricsHandler) GetMetricsSummary(w http.ResponseWriter, r *http.Request) {
	summary, err := h.metrics.GetMetricsSummary()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get metrics summary: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(summary)
}

// GetPerformanceMetrics returns performance metrics for a specific timeframe
func (h *MetricsHandler) GetPerformanceMetrics(w http.ResponseWriter, r *http.Request) {
	timeframe := r.URL.Query().Get("timeframe")
	if timeframe == "" {
		timeframe = "24h"
	}

	metrics, err := h.analytics.GetPerformanceMetrics(r.Context(), timeframe)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get performance metrics: %v", err), http.StatusInternalServerError)
		return
	}

	response := map[string]interface{}{
		"timeframe": timeframe,
		"metrics":   metrics,
		"count":     len(metrics),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// GetSystemAnalytics returns comprehensive system analytics
func (h *MetricsHandler) GetSystemAnalytics(w http.ResponseWriter, r *http.Request) {
	analytics, err := h.analytics.GetSystemAnalytics(r.Context())
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get system analytics: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(analytics)
}

// GetModelPerformance returns performance metrics for specific models
func (h *MetricsHandler) GetModelPerformance(w http.ResponseWriter, r *http.Request) {
	modelName := r.URL.Query().Get("model_name")
	modelProvider := r.URL.Query().Get("model_provider")
	timeframe := r.URL.Query().Get("timeframe")

	if modelName == "" || modelProvider == "" {
		http.Error(w, "model_name and model_provider are required", http.StatusBadRequest)
		return
	}

	if timeframe == "" {
		timeframe = "24h"
	}

	metrics, err := h.analytics.GetModelPerformanceTrends(r.Context(), modelName, modelProvider, timeframe)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get model performance: %v", err), http.StatusInternalServerError)
		return
	}

	response := map[string]interface{}{
		"model_name":     modelName,
		"model_provider": modelProvider,
		"timeframe":      timeframe,
		"metrics":        metrics,
		"count":          len(metrics),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// GetPerformanceReport generates a comprehensive performance report
func (h *MetricsHandler) GetPerformanceReport(w http.ResponseWriter, r *http.Request) {
	timeframe := r.URL.Query().Get("timeframe")
	if timeframe == "" {
		timeframe = "24h"
	}

	report, err := h.analytics.CreatePerformanceReport(r.Context(), timeframe)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to generate performance report: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(report)
}

// GetRealTimeMetrics returns real-time metrics (basic implementation)
func (h *MetricsHandler) GetRealTimeMetrics(w http.ResponseWriter, r *http.Request) {
	// This would typically connect to a real-time metrics stream
	// For now, we'll return current metrics
	summary, err := h.metrics.GetMetricsSummary()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get real-time metrics: %v", err), http.StatusInternalServerError)
		return
	}

	// Add timestamp and real-time flag
	realTimeMetrics := map[string]interface{}{
		"timestamp": time.Now(),
		"real_time": true,
		"metrics":   summary,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(realTimeMetrics)
}

// GetMetricsHealth returns the health status of the metrics system
func (h *MetricsHandler) GetMetricsHealth(w http.ResponseWriter, r *http.Request) {
	err := h.metrics.HealthCheck()
	if err != nil {
		http.Error(w, fmt.Sprintf("Metrics system unhealthy: %v", err), http.StatusServiceUnavailable)
		return
	}

	health := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now(),
		"uptime":    time.Since(time.Now()), // This would be actual uptime
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(health)
}

// RegisterMetricsRoutes registers all metrics-related routes
func (h *MetricsHandler) RegisterMetricsRoutes(router *mux.Router) {
	// Metrics endpoints
	router.HandleFunc("/api/metrics", h.GetMetricsSummary).Methods("GET")
	router.HandleFunc("/api/metrics/summary", h.GetMetricsSummary).Methods("GET")
	router.HandleFunc("/api/metrics/performance", h.GetPerformanceMetrics).Methods("GET")
	router.HandleFunc("/api/metrics/models", h.GetModelPerformance).Methods("GET")
	router.HandleFunc("/api/metrics/realtime", h.GetRealTimeMetrics).Methods("GET")
	router.HandleFunc("/api/metrics/health", h.GetMetricsHealth).Methods("GET")

	// Analytics endpoints
	router.HandleFunc("/api/analytics/performance", h.GetSystemAnalytics).Methods("GET")
	router.HandleFunc("/api/analytics/models/comparison", h.GetSystemAnalytics).Methods("GET") // Returns model comparison within analytics
	router.HandleFunc("/api/analytics/reports/{type}", h.GetPerformanceReport).Methods("GET")
	router.HandleFunc("/api/analytics/trends/{timeframe}", h.GetPerformanceMetrics).Methods("GET")
}

// MetricsMiddleware wraps handlers to record metrics
func (h *MetricsHandler) MetricsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Wrap the ResponseWriter to capture status code
		wrapper := &responseWriter{
			ResponseWriter: w,
			statusCode:     http.StatusOK,
		}

		// Process the request
		next.ServeHTTP(wrapper, r)

		// Record metrics
		duration := time.Since(start)
		statusCode := strconv.Itoa(wrapper.statusCode)

		h.metrics.RecordRequest(r.Method, r.URL.Path, statusCode, duration)
	})
}

// responseWriter is defined in middleware.go

// LoadTestEndpoint provides an endpoint for load testing
func (h *MetricsHandler) LoadTestEndpoint(w http.ResponseWriter, r *http.Request) {
	// Parse query parameters
	durationParam := r.URL.Query().Get("duration")
	concurrencyParam := r.URL.Query().Get("concurrency")

	duration := 60 * time.Second // default 60 seconds
	concurrency := 10            // default 10 concurrent users

	if durationParam != "" {
		if d, err := time.ParseDuration(durationParam); err == nil {
			duration = d
		}
	}

	if concurrencyParam != "" {
		if c, err := strconv.Atoi(concurrencyParam); err == nil {
			concurrency = c
		}
	}

	// This would typically trigger a load test
	// For now, we'll just return the configuration
	response := map[string]interface{}{
		"status":      "load_test_initiated",
		"duration":    duration.String(),
		"concurrency": concurrency,
		"timestamp":   time.Now(),
		"message":     "Load test configuration received - actual load testing would be implemented here",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}
