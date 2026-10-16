package monitoring

import (
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// MetricsCollector holds all Prometheus metrics for the application
type MetricsCollector struct {
	// Request metrics
	RequestDuration   *prometheus.HistogramVec
	RequestCount      *prometheus.CounterVec
	ActiveConnections prometheus.Gauge

	// Model performance metrics
	ModelPerformance *prometheus.HistogramVec
	ModelAccuracy    *prometheus.GaugeVec
	ModelErrorRate   *prometheus.CounterVec

	// System metrics
	DBConnections   prometheus.Gauge
	DBQueryDuration *prometheus.HistogramVec
	CacheHitRate    prometheus.Gauge

	// Evaluation metrics
	EvaluationCount   *prometheus.CounterVec
	EvaluationScore   *prometheus.HistogramVec
	EvaluationSuccess *prometheus.CounterVec
}

// NewMetricsCollector creates a new metrics collector
func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		RequestDuration: promauto.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "llm_evaluation_request_duration_seconds",
				Help:    "Duration of HTTP requests in seconds",
				Buckets: prometheus.DefBuckets,
			},
			[]string{"method", "endpoint", "status_code"},
		),

		RequestCount: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "llm_evaluation_requests_total",
				Help: "Total number of HTTP requests",
			},
			[]string{"method", "endpoint", "status_code"},
		),

		ActiveConnections: promauto.NewGauge(
			prometheus.GaugeOpts{
				Name: "llm_evaluation_active_connections",
				Help: "Number of active connections",
			},
		),

		ModelPerformance: promauto.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "llm_evaluation_model_response_time_seconds",
				Help:    "Response time for LLM model calls in seconds",
				Buckets: []float64{0.1, 0.5, 1, 2, 5, 10, 30, 60, 120},
			},
			[]string{"model_name", "model_provider", "test_type"},
		),

		ModelAccuracy: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "llm_evaluation_model_accuracy",
				Help: "Current accuracy score for each model",
			},
			[]string{"model_name", "model_provider", "test_type"},
		),

		ModelErrorRate: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "llm_evaluation_model_errors_total",
				Help: "Total number of model errors",
			},
			[]string{"model_name", "model_provider", "error_type"},
		),

		DBConnections: promauto.NewGauge(
			prometheus.GaugeOpts{
				Name: "llm_evaluation_db_connections",
				Help: "Number of active database connections",
			},
		),

		DBQueryDuration: promauto.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "llm_evaluation_db_query_duration_seconds",
				Help:    "Duration of database queries in seconds",
				Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5},
			},
			[]string{"query_type", "table"},
		),

		CacheHitRate: promauto.NewGauge(
			prometheus.GaugeOpts{
				Name: "llm_evaluation_cache_hit_rate",
				Help: "Cache hit rate percentage",
			},
		),

		EvaluationCount: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "llm_evaluation_evaluations_total",
				Help: "Total number of evaluations performed",
			},
			[]string{"model_name", "model_provider", "test_type", "status"},
		),

		EvaluationScore: promauto.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "llm_evaluation_score",
				Help:    "Evaluation scores distribution",
				Buckets: []float64{0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0},
			},
			[]string{"model_name", "model_provider", "test_type"},
		),

		EvaluationSuccess: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "llm_evaluation_success_total",
				Help: "Total number of successful evaluations",
			},
			[]string{"model_name", "model_provider", "test_type"},
		),
	}
}

// RecordRequest records metrics for an HTTP request
func (m *MetricsCollector) RecordRequest(method, endpoint, statusCode string, duration time.Duration) {
	m.RequestDuration.WithLabelValues(method, endpoint, statusCode).Observe(duration.Seconds())
	m.RequestCount.WithLabelValues(method, endpoint, statusCode).Inc()
}

// RecordModelPerformance records metrics for model performance
func (m *MetricsCollector) RecordModelPerformance(modelName, modelProvider, testType string, responseTime time.Duration) {
	m.ModelPerformance.WithLabelValues(modelName, modelProvider, testType).Observe(responseTime.Seconds())
}

// RecordModelAccuracy records the accuracy score for a model
func (m *MetricsCollector) RecordModelAccuracy(modelName, modelProvider, testType string, accuracy float64) {
	m.ModelAccuracy.WithLabelValues(modelName, modelProvider, testType).Set(accuracy)
}

// RecordModelError records an error for a model
func (m *MetricsCollector) RecordModelError(modelName, modelProvider, errorType string) {
	m.ModelErrorRate.WithLabelValues(modelName, modelProvider, errorType).Inc()
}

// RecordEvaluation records metrics for an evaluation
func (m *MetricsCollector) RecordEvaluation(modelName, modelProvider, testType, status string, score float64) {
	m.EvaluationCount.WithLabelValues(modelName, modelProvider, testType, status).Inc()
	m.EvaluationScore.WithLabelValues(modelName, modelProvider, testType).Observe(score)

	if status == "success" {
		m.EvaluationSuccess.WithLabelValues(modelName, modelProvider, testType).Inc()
	}
}

// RecordDBQuery records metrics for database queries
func (m *MetricsCollector) RecordDBQuery(queryType, table string, duration time.Duration) {
	m.DBQueryDuration.WithLabelValues(queryType, table).Observe(duration.Seconds())
}

// SetActiveConnections sets the number of active connections
func (m *MetricsCollector) SetActiveConnections(count int) {
	m.ActiveConnections.Set(float64(count))
}

// SetDBConnections sets the number of active database connections
func (m *MetricsCollector) SetDBConnections(count int) {
	m.DBConnections.Set(float64(count))
}

// SetCacheHitRate sets the cache hit rate percentage
func (m *MetricsCollector) SetCacheHitRate(hitRate float64) {
	m.CacheHitRate.Set(hitRate)
}

// GetMetricsSummary returns a summary of current metrics
func (m *MetricsCollector) GetMetricsSummary() (map[string]interface{}, error) {
	// In a real implementation, you would gather metrics from Prometheus
	// For now, we'll return a basic summary structure
	summary := map[string]interface{}{
		"requests": map[string]interface{}{
			"total":             "counter_value",
			"avg_response_time": "histogram_avg",
			"error_rate":        "calculated_percentage",
		},
		"models": map[string]interface{}{
			"total_models":      "gauge_value",
			"avg_accuracy":      "gauge_avg",
			"total_evaluations": "counter_value",
		},
		"system": map[string]interface{}{
			"active_connections": "gauge_value",
			"db_connections":     "gauge_value",
			"cache_hit_rate":     "gauge_value",
		},
	}

	return summary, nil
}

// HealthCheck returns the health status of the metrics system
func (m *MetricsCollector) HealthCheck() error {
	// Basic health check - in a real implementation, you might check
	// if Prometheus is reachable, metrics are being recorded, etc.
	return nil
}
