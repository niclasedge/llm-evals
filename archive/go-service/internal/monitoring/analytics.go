package monitoring

import (
	"context"
	"database/sql"
	"fmt"
	"time"
)

// PerformanceMetrics represents performance metrics for a specific timeframe
type PerformanceMetrics struct {
	Timestamp       time.Time              `json:"timestamp"`
	ModelName       string                 `json:"model_name"`
	ModelProvider   string                 `json:"model_provider"`
	TestType        string                 `json:"test_type"`
	AvgResponseTime float64                `json:"avg_response_time"`
	SuccessRate     float64                `json:"success_rate"`
	TotalRequests   int64                  `json:"total_requests"`
	ErrorRate       float64                `json:"error_rate"`
	Throughput      float64                `json:"throughput"` // requests per second
	P95ResponseTime float64                `json:"p95_response_time"`
	P99ResponseTime float64                `json:"p99_response_time"`
	AvgScore        float64                `json:"avg_score"`
	Metadata        map[string]interface{} `json:"metadata"`
}

// SystemAnalytics represents system-wide analytics
type SystemAnalytics struct {
	RequestVolume    map[string]int64   `json:"request_volume"`    // requests per hour
	ResponseTimes    map[string]float64 `json:"response_times"`    // avg response time by endpoint
	ErrorRates       map[string]float64 `json:"error_rates"`       // error rate by model
	ThroughputTrends []ThroughputPoint  `json:"throughput_trends"` // throughput over time
	ModelComparison  []ModelStats       `json:"model_comparison"`  // comparative model performance
	SystemHealth     HealthMetrics      `json:"system_health"`     // overall system status
}

// ThroughputPoint represents a point in throughput trends
type ThroughputPoint struct {
	Timestamp  time.Time `json:"timestamp"`
	Throughput float64   `json:"throughput"`
	Requests   int64     `json:"requests"`
}

// ModelStats represents statistics for a model
type ModelStats struct {
	ModelName        string    `json:"model_name"`
	ModelProvider    string    `json:"model_provider"`
	TotalEvaluations int64     `json:"total_evaluations"`
	SuccessRate      float64   `json:"success_rate"`
	AvgScore         float64   `json:"avg_score"`
	AvgResponseTime  float64   `json:"avg_response_time"`
	ErrorCount       int64     `json:"error_count"`
	LastEvaluation   time.Time `json:"last_evaluation"`
}

// HealthMetrics represents overall system health
type HealthMetrics struct {
	Status            string        `json:"status"`
	Uptime            time.Duration `json:"uptime"`
	TotalRequests     int64         `json:"total_requests"`
	ActiveConnections int           `json:"active_connections"`
	DBConnections     int           `json:"db_connections"`
	CacheHitRate      float64       `json:"cache_hit_rate"`
	LastUpdated       time.Time     `json:"last_updated"`
}

// AnalyticsService provides analytics functionality
type AnalyticsService struct {
	db        *sql.DB
	metrics   *MetricsCollector
	startTime time.Time
}

// NewAnalyticsService creates a new analytics service
func NewAnalyticsService(db *sql.DB, metrics *MetricsCollector) *AnalyticsService {
	return &AnalyticsService{
		db:        db,
		metrics:   metrics,
		startTime: time.Now(),
	}
}

// GetPerformanceMetrics returns performance metrics for the specified timeframe
func (a *AnalyticsService) GetPerformanceMetrics(ctx context.Context, timeframe string) ([]PerformanceMetrics, error) {
	var startTime time.Time

	switch timeframe {
	case "1h":
		startTime = time.Now().Add(-time.Hour)
	case "24h":
		startTime = time.Now().Add(-24 * time.Hour)
	case "7d":
		startTime = time.Now().Add(-7 * 24 * time.Hour)
	case "30d":
		startTime = time.Now().Add(-30 * 24 * time.Hour)
	default:
		startTime = time.Now().Add(-time.Hour)
	}

	query := `
		SELECT 
			DATE(timestamp) as date,
			model_name,
			model_provider,
			test_type,
			AVG(execution_time) as avg_response_time,
			COUNT(*) as total_requests,
			SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
			SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as error_rate,
			AVG(score) as avg_score,
			COUNT(*) * 1.0 / 3600 as throughput
		FROM evaluation_results 
		WHERE timestamp >= ?
		GROUP BY DATE(timestamp), model_name, model_provider, test_type
		ORDER BY date DESC
	`

	rows, err := a.db.QueryContext(ctx, query, startTime)
	if err != nil {
		return nil, fmt.Errorf("failed to query performance metrics: %w", err)
	}
	defer rows.Close()

	var metrics []PerformanceMetrics
	for rows.Next() {
		var metric PerformanceMetrics
		var dateStr string

		err := rows.Scan(
			&dateStr,
			&metric.ModelName,
			&metric.ModelProvider,
			&metric.TestType,
			&metric.AvgResponseTime,
			&metric.TotalRequests,
			&metric.SuccessRate,
			&metric.ErrorRate,
			&metric.AvgScore,
			&metric.Throughput,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan performance metrics: %w", err)
		}

		// Parse date
		metric.Timestamp, err = time.Parse("2006-01-02", dateStr)
		if err != nil {
			return nil, fmt.Errorf("failed to parse date: %w", err)
		}

		// Calculate percentiles (simplified - in real implementation, you'd need more sophisticated calculation)
		metric.P95ResponseTime = metric.AvgResponseTime * 1.5
		metric.P99ResponseTime = metric.AvgResponseTime * 2.0

		// Add metadata
		metric.Metadata = map[string]interface{}{
			"calculated_at": time.Now(),
			"timeframe":     timeframe,
		}

		metrics = append(metrics, metric)
	}

	return metrics, nil
}

// GetSystemAnalytics returns comprehensive system analytics
func (a *AnalyticsService) GetSystemAnalytics(ctx context.Context) (*SystemAnalytics, error) {
	analytics := &SystemAnalytics{
		RequestVolume:    make(map[string]int64),
		ResponseTimes:    make(map[string]float64),
		ErrorRates:       make(map[string]float64),
		ThroughputTrends: []ThroughputPoint{},
		ModelComparison:  []ModelStats{},
		SystemHealth:     HealthMetrics{},
	}

	// Get request volume (last 24 hours, grouped by hour)
	err := a.getRequestVolume(ctx, analytics)
	if err != nil {
		return nil, fmt.Errorf("failed to get request volume: %w", err)
	}

	// Get response times by endpoint
	err = a.getResponseTimes(ctx, analytics)
	if err != nil {
		return nil, fmt.Errorf("failed to get response times: %w", err)
	}

	// Get error rates by model
	err = a.getErrorRates(ctx, analytics)
	if err != nil {
		return nil, fmt.Errorf("failed to get error rates: %w", err)
	}

	// Get throughput trends
	err = a.getThroughputTrends(ctx, analytics)
	if err != nil {
		return nil, fmt.Errorf("failed to get throughput trends: %w", err)
	}

	// Get model comparison
	err = a.getModelComparison(ctx, analytics)
	if err != nil {
		return nil, fmt.Errorf("failed to get model comparison: %w", err)
	}

	// Get system health
	err = a.getSystemHealth(ctx, analytics)
	if err != nil {
		return nil, fmt.Errorf("failed to get system health: %w", err)
	}

	return analytics, nil
}

// getRequestVolume populates request volume data
func (a *AnalyticsService) getRequestVolume(ctx context.Context, analytics *SystemAnalytics) error {
	query := `
		SELECT 
			strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
			COUNT(*) as requests
		FROM evaluation_results 
		WHERE timestamp >= datetime('now', '-24 hours')
		GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
		ORDER BY hour
	`

	rows, err := a.db.QueryContext(ctx, query)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var hour string
		var requests int64
		if err := rows.Scan(&hour, &requests); err != nil {
			return err
		}
		analytics.RequestVolume[hour] = requests
	}

	return nil
}

// getResponseTimes populates response times data
func (a *AnalyticsService) getResponseTimes(ctx context.Context, analytics *SystemAnalytics) error {
	query := `
		SELECT 
			test_type,
			AVG(execution_time) as avg_response_time
		FROM evaluation_results 
		WHERE timestamp >= datetime('now', '-24 hours')
		GROUP BY test_type
	`

	rows, err := a.db.QueryContext(ctx, query)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var testType string
		var avgResponseTime float64
		if err := rows.Scan(&testType, &avgResponseTime); err != nil {
			return err
		}
		analytics.ResponseTimes[testType] = avgResponseTime
	}

	return nil
}

// getErrorRates populates error rates data
func (a *AnalyticsService) getErrorRates(ctx context.Context, analytics *SystemAnalytics) error {
	query := `
		SELECT 
			model_name || '/' || model_provider as model,
			(SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as error_rate
		FROM evaluation_results 
		WHERE timestamp >= datetime('now', '-24 hours')
		GROUP BY model_name, model_provider
	`

	rows, err := a.db.QueryContext(ctx, query)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var model string
		var errorRate float64
		if err := rows.Scan(&model, &errorRate); err != nil {
			return err
		}
		analytics.ErrorRates[model] = errorRate
	}

	return nil
}

// getThroughputTrends populates throughput trends data
func (a *AnalyticsService) getThroughputTrends(ctx context.Context, analytics *SystemAnalytics) error {
	query := `
		SELECT 
			strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
			COUNT(*) as requests,
			COUNT(*) * 1.0 / 3600 as throughput
		FROM evaluation_results 
		WHERE timestamp >= datetime('now', '-24 hours')
		GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
		ORDER BY hour
	`

	rows, err := a.db.QueryContext(ctx, query)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var hourStr string
		var requests int64
		var throughput float64
		if err := rows.Scan(&hourStr, &requests, &throughput); err != nil {
			return err
		}

		hour, err := time.Parse("2006-01-02 15:04:05", hourStr)
		if err != nil {
			return err
		}

		analytics.ThroughputTrends = append(analytics.ThroughputTrends, ThroughputPoint{
			Timestamp:  hour,
			Throughput: throughput,
			Requests:   requests,
		})
	}

	return nil
}

// getModelComparison populates model comparison data
func (a *AnalyticsService) getModelComparison(ctx context.Context, analytics *SystemAnalytics) error {
	query := `
		SELECT 
			model_name,
			model_provider,
			COUNT(*) as total_evaluations,
			SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
			AVG(score) as avg_score,
			AVG(execution_time) as avg_response_time,
			SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) as error_count,
			MAX(timestamp) as last_evaluation
		FROM evaluation_results 
		WHERE timestamp >= datetime('now', '-7 days')
		GROUP BY model_name, model_provider
		ORDER BY avg_score DESC
	`

	rows, err := a.db.QueryContext(ctx, query)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var stats ModelStats
		var lastEvalStr string

		err := rows.Scan(
			&stats.ModelName,
			&stats.ModelProvider,
			&stats.TotalEvaluations,
			&stats.SuccessRate,
			&stats.AvgScore,
			&stats.AvgResponseTime,
			&stats.ErrorCount,
			&lastEvalStr,
		)
		if err != nil {
			return err
		}

		stats.LastEvaluation, err = time.Parse("2006-01-02 15:04:05", lastEvalStr)
		if err != nil {
			return err
		}

		analytics.ModelComparison = append(analytics.ModelComparison, stats)
	}

	return nil
}

// getSystemHealth populates system health data
func (a *AnalyticsService) getSystemHealth(ctx context.Context, analytics *SystemAnalytics) error {
	// Get total requests
	var totalRequests int64
	err := a.db.QueryRowContext(ctx, "SELECT COUNT(*) FROM evaluation_results").Scan(&totalRequests)
	if err != nil {
		return err
	}

	analytics.SystemHealth = HealthMetrics{
		Status:            "healthy",
		Uptime:            time.Since(a.startTime),
		TotalRequests:     totalRequests,
		ActiveConnections: 0,   // This would be set by the metrics collector
		DBConnections:     1,   // This would be set by the database connection pool
		CacheHitRate:      0.0, // This would be calculated from cache metrics
		LastUpdated:       time.Now(),
	}

	return nil
}

// GetModelPerformanceTrends returns performance trends for specific models
func (a *AnalyticsService) GetModelPerformanceTrends(ctx context.Context, modelName, modelProvider string, timeframe string) ([]PerformanceMetrics, error) {
	var startTime time.Time

	switch timeframe {
	case "1h":
		startTime = time.Now().Add(-time.Hour)
	case "24h":
		startTime = time.Now().Add(-24 * time.Hour)
	case "7d":
		startTime = time.Now().Add(-7 * 24 * time.Hour)
	case "30d":
		startTime = time.Now().Add(-30 * 24 * time.Hour)
	default:
		startTime = time.Now().Add(-time.Hour)
	}

	query := `
		SELECT 
			timestamp,
			model_name,
			model_provider,
			test_type,
			execution_time,
			score,
			passed
		FROM evaluation_results 
		WHERE model_name = ? AND model_provider = ? AND timestamp >= ?
		ORDER BY timestamp DESC
	`

	rows, err := a.db.QueryContext(ctx, query, modelName, modelProvider, startTime)
	if err != nil {
		return nil, fmt.Errorf("failed to query model performance trends: %w", err)
	}
	defer rows.Close()

	var metrics []PerformanceMetrics
	for rows.Next() {
		var metric PerformanceMetrics
		var timestampStr string
		var passed bool

		err := rows.Scan(
			&timestampStr,
			&metric.ModelName,
			&metric.ModelProvider,
			&metric.TestType,
			&metric.AvgResponseTime,
			&metric.AvgScore,
			&passed,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan model performance trends: %w", err)
		}

		metric.Timestamp, err = time.Parse("2006-01-02 15:04:05", timestampStr)
		if err != nil {
			return nil, fmt.Errorf("failed to parse timestamp: %w", err)
		}

		metric.TotalRequests = 1
		if passed {
			metric.SuccessRate = 100.0
			metric.ErrorRate = 0.0
		} else {
			metric.SuccessRate = 0.0
			metric.ErrorRate = 100.0
		}

		metrics = append(metrics, metric)
	}

	return metrics, nil
}

// CreatePerformanceReport generates a comprehensive performance report
func (a *AnalyticsService) CreatePerformanceReport(ctx context.Context, timeframe string) (map[string]interface{}, error) {
	analytics, err := a.GetSystemAnalytics(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get system analytics: %w", err)
	}

	metrics, err := a.GetPerformanceMetrics(ctx, timeframe)
	if err != nil {
		return nil, fmt.Errorf("failed to get performance metrics: %w", err)
	}

	report := map[string]interface{}{
		"generated_at":        time.Now(),
		"timeframe":           timeframe,
		"system_analytics":    analytics,
		"performance_metrics": metrics,
		"summary": map[string]interface{}{
			"total_models":           len(analytics.ModelComparison),
			"total_evaluations":      analytics.SystemHealth.TotalRequests,
			"avg_success_rate":       a.calculateAverageSuccessRate(analytics.ModelComparison),
			"avg_response_time":      a.calculateAverageResponseTime(analytics.ModelComparison),
			"best_performing_model":  a.getBestPerformingModel(analytics.ModelComparison),
			"worst_performing_model": a.getWorstPerformingModel(analytics.ModelComparison),
		},
	}

	return report, nil
}

// Helper functions for report generation
func (a *AnalyticsService) calculateAverageSuccessRate(models []ModelStats) float64 {
	if len(models) == 0 {
		return 0.0
	}

	total := 0.0
	for _, model := range models {
		total += model.SuccessRate
	}
	return total / float64(len(models))
}

func (a *AnalyticsService) calculateAverageResponseTime(models []ModelStats) float64 {
	if len(models) == 0 {
		return 0.0
	}

	total := 0.0
	for _, model := range models {
		total += model.AvgResponseTime
	}
	return total / float64(len(models))
}

func (a *AnalyticsService) getBestPerformingModel(models []ModelStats) string {
	if len(models) == 0 {
		return ""
	}

	best := models[0]
	for _, model := range models {
		if model.AvgScore > best.AvgScore {
			best = model
		}
	}

	return fmt.Sprintf("%s/%s (%.2f)", best.ModelProvider, best.ModelName, best.AvgScore)
}

func (a *AnalyticsService) getWorstPerformingModel(models []ModelStats) string {
	if len(models) == 0 {
		return ""
	}

	worst := models[0]
	for _, model := range models {
		if model.AvgScore < worst.AvgScore {
			worst = model
		}
	}

	return fmt.Sprintf("%s/%s (%.2f)", worst.ModelProvider, worst.ModelName, worst.AvgScore)
}
