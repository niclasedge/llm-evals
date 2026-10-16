package monitoring

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"sync/atomic"
	"time"
)

// LoadTestConfig defines configuration for load testing
type LoadTestConfig struct {
	ConcurrentUsers int           `json:"concurrent_users"`
	TestDuration    time.Duration `json:"test_duration"`
	RequestRate     int           `json:"request_rate"` // requests per second
	RampUpDuration  time.Duration `json:"ramp_up_duration"`
	Models          []string      `json:"models"`
	TestScenarios   []string      `json:"test_scenarios"`
	TargetEndpoint  string        `json:"target_endpoint"`
	RequestPayload  interface{}   `json:"request_payload"`
}

// LoadTestResults contains the results of a load test
type LoadTestResults struct {
	TotalRequests   int64            `json:"total_requests"`
	SuccessfulReqs  int64            `json:"successful_requests"`
	FailedRequests  int64            `json:"failed_requests"`
	AvgResponseTime float64          `json:"avg_response_time"`
	MaxResponseTime float64          `json:"max_response_time"`
	MinResponseTime float64          `json:"min_response_time"`
	P95ResponseTime float64          `json:"p95_response_time"`
	P99ResponseTime float64          `json:"p99_response_time"`
	ThroughputRPS   float64          `json:"throughput_rps"`
	ErrorRate       float64          `json:"error_rate"`
	StartTime       time.Time        `json:"start_time"`
	EndTime         time.Time        `json:"end_time"`
	Duration        time.Duration    `json:"duration"`
	RequestTimes    []float64        `json:"request_times"`
	ErrorTypes      map[string]int64 `json:"error_types"`
	Concurrency     int              `json:"concurrency"`
	RampUpDuration  time.Duration    `json:"ramp_up_duration"`
}

// LoadTestRunner manages and executes load tests
type LoadTestRunner struct {
	config          *LoadTestConfig
	metrics         *MetricsCollector
	responseTimes   []float64
	responseTimesMu sync.RWMutex
	totalRequests   int64
	successfulReqs  int64
	failedRequests  int64
	errorTypes      map[string]int64
	errorTypesMu    sync.RWMutex
	startTime       time.Time
	endTime         time.Time
}

// NewLoadTestRunner creates a new load test runner
func NewLoadTestRunner(config *LoadTestConfig, metrics *MetricsCollector) *LoadTestRunner {
	return &LoadTestRunner{
		config:        config,
		metrics:       metrics,
		responseTimes: make([]float64, 0),
		errorTypes:    make(map[string]int64),
	}
}

// RunLoadTest executes a load test with the given configuration
func (r *LoadTestRunner) RunLoadTest(ctx context.Context) (*LoadTestResults, error) {
	r.startTime = time.Now()

	// Create context with timeout
	testCtx, cancel := context.WithTimeout(ctx, r.config.TestDuration)
	defer cancel()

	// Channel to control request rate
	rateLimiter := make(chan struct{}, r.config.RequestRate)

	// Start rate limiter goroutine
	go r.rateLimiterLoop(testCtx, rateLimiter)

	// Create worker goroutines
	var wg sync.WaitGroup
	for i := 0; i < r.config.ConcurrentUsers; i++ {
		wg.Add(1)
		go r.worker(testCtx, &wg, rateLimiter, i)
	}

	// Wait for all workers to complete
	wg.Wait()
	r.endTime = time.Now()

	// Calculate and return results
	return r.calculateResults(), nil
}

// rateLimiterLoop controls the rate of requests
func (r *LoadTestRunner) rateLimiterLoop(ctx context.Context, rateLimiter chan struct{}) {
	ticker := time.NewTicker(time.Second / time.Duration(r.config.RequestRate))
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			select {
			case rateLimiter <- struct{}{}:
			default:
				// Skip if channel is full
			}
		}
	}
}

// worker performs the actual load testing requests
func (r *LoadTestRunner) worker(ctx context.Context, wg *sync.WaitGroup, rateLimiter chan struct{}, workerID int) {
	defer wg.Done()

	for {
		select {
		case <-ctx.Done():
			return
		case <-rateLimiter:
			r.makeRequest(ctx, workerID)
		}
	}
}

// makeRequest makes a single request and records metrics
func (r *LoadTestRunner) makeRequest(ctx context.Context, workerID int) {
	startTime := time.Now()
	atomic.AddInt64(&r.totalRequests, 1)

	// Simulate request execution
	// In a real implementation, this would make actual HTTP requests
	success := r.simulateRequest(ctx)

	responseTime := time.Since(startTime).Seconds()

	// Record response time
	r.responseTimesMu.Lock()
	r.responseTimes = append(r.responseTimes, responseTime)
	r.responseTimesMu.Unlock()

	// Record success/failure
	if success {
		atomic.AddInt64(&r.successfulReqs, 1)
		r.metrics.RecordRequest("POST", r.config.TargetEndpoint, "200", time.Since(startTime))
	} else {
		atomic.AddInt64(&r.failedRequests, 1)
		r.metrics.RecordRequest("POST", r.config.TargetEndpoint, "500", time.Since(startTime))

		// Record error type
		r.errorTypesMu.Lock()
		r.errorTypes["request_failed"]++
		r.errorTypesMu.Unlock()
	}
}

// simulateRequest simulates a request execution
func (r *LoadTestRunner) simulateRequest(ctx context.Context) bool {
	// Simulate request processing time
	processingTime := time.Duration(50+atomic.LoadInt64(&r.totalRequests)%200) * time.Millisecond

	select {
	case <-ctx.Done():
		return false
	case <-time.After(processingTime):
		// Simulate 95% success rate
		return atomic.LoadInt64(&r.totalRequests)%20 != 0
	}
}

// calculateResults calculates and returns the load test results
func (r *LoadTestRunner) calculateResults() *LoadTestResults {
	r.responseTimesMu.RLock()
	defer r.responseTimesMu.RUnlock()

	totalRequests := atomic.LoadInt64(&r.totalRequests)
	successfulReqs := atomic.LoadInt64(&r.successfulReqs)
	failedRequests := atomic.LoadInt64(&r.failedRequests)

	duration := r.endTime.Sub(r.startTime)
	throughput := float64(totalRequests) / duration.Seconds()

	var avgResponseTime, minResponseTime, maxResponseTime float64
	var p95ResponseTime, p99ResponseTime float64

	if len(r.responseTimes) > 0 {
		avgResponseTime = r.calculateAverage(r.responseTimes)
		minResponseTime = r.calculateMin(r.responseTimes)
		maxResponseTime = r.calculateMax(r.responseTimes)
		p95ResponseTime = r.calculatePercentile(r.responseTimes, 95)
		p99ResponseTime = r.calculatePercentile(r.responseTimes, 99)
	}

	errorRate := 0.0
	if totalRequests > 0 {
		errorRate = float64(failedRequests) / float64(totalRequests) * 100
	}

	r.errorTypesMu.RLock()
	errorTypes := make(map[string]int64)
	for k, v := range r.errorTypes {
		errorTypes[k] = v
	}
	r.errorTypesMu.RUnlock()

	return &LoadTestResults{
		TotalRequests:   totalRequests,
		SuccessfulReqs:  successfulReqs,
		FailedRequests:  failedRequests,
		AvgResponseTime: avgResponseTime,
		MaxResponseTime: maxResponseTime,
		MinResponseTime: minResponseTime,
		P95ResponseTime: p95ResponseTime,
		P99ResponseTime: p99ResponseTime,
		ThroughputRPS:   throughput,
		ErrorRate:       errorRate,
		StartTime:       r.startTime,
		EndTime:         r.endTime,
		Duration:        duration,
		RequestTimes:    r.responseTimes,
		ErrorTypes:      errorTypes,
		Concurrency:     r.config.ConcurrentUsers,
		RampUpDuration:  r.config.RampUpDuration,
	}
}

// Helper methods for statistical calculations
func (r *LoadTestRunner) calculateAverage(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func (r *LoadTestRunner) calculateMin(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	min := values[0]
	for _, v := range values {
		if v < min {
			min = v
		}
	}
	return min
}

func (r *LoadTestRunner) calculateMax(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	max := values[0]
	for _, v := range values {
		if v > max {
			max = v
		}
	}
	return max
}

func (r *LoadTestRunner) calculatePercentile(values []float64, percentile float64) float64 {
	if len(values) == 0 {
		return 0
	}

	// Simple percentile calculation - in production, use a proper implementation
	// This is a simplified version for demonstration
	sortedValues := make([]float64, len(values))
	copy(sortedValues, values)

	// Simple bubble sort for demonstration
	for i := 0; i < len(sortedValues); i++ {
		for j := i + 1; j < len(sortedValues); j++ {
			if sortedValues[i] > sortedValues[j] {
				sortedValues[i], sortedValues[j] = sortedValues[j], sortedValues[i]
			}
		}
	}

	index := int(float64(len(sortedValues)) * percentile / 100)
	if index >= len(sortedValues) {
		index = len(sortedValues) - 1
	}

	return sortedValues[index]
}

// BenchmarkScenario defines a benchmark scenario
type BenchmarkScenario struct {
	Name            string                 `json:"name"`
	Description     string                 `json:"description"`
	Config          *LoadTestConfig        `json:"config"`
	ExpectedResults *LoadTestResults       `json:"expected_results"`
	Metadata        map[string]interface{} `json:"metadata"`
}

// BenchmarkSuite manages multiple benchmark scenarios
type BenchmarkSuite struct {
	Name      string                      `json:"name"`
	Scenarios []BenchmarkScenario         `json:"scenarios"`
	Results   map[string]*LoadTestResults `json:"results"`
	metrics   *MetricsCollector
	logger    *slog.Logger
}

// NewBenchmarkSuite creates a new benchmark suite
func NewBenchmarkSuite(name string, metrics *MetricsCollector) *BenchmarkSuite {
	return NewBenchmarkSuiteWithLogger(name, metrics, slog.Default())
}

// NewBenchmarkSuiteWithLogger creates a new benchmark suite with custom logger
func NewBenchmarkSuiteWithLogger(name string, metrics *MetricsCollector, logger *slog.Logger) *BenchmarkSuite {
	return &BenchmarkSuite{
		Name:    name,
		Results: make(map[string]*LoadTestResults),
		metrics: metrics,
		logger:  logger,
	}
}

// AddScenario adds a benchmark scenario to the suite
func (s *BenchmarkSuite) AddScenario(scenario BenchmarkScenario) {
	s.Scenarios = append(s.Scenarios, scenario)
}

// RunBenchmarks executes all benchmark scenarios
func (s *BenchmarkSuite) RunBenchmarks(ctx context.Context) error {
	s.logger.InfoContext(ctx, "Starting benchmark suite execution",
		"component", "monitoring.load_testing",
		"suite_name", s.Name,
		"scenario_count", len(s.Scenarios))

	for _, scenario := range s.Scenarios {
		s.logger.InfoContext(ctx, "Running benchmark scenario",
			"component", "monitoring.load_testing",
			"suite_name", s.Name,
			"scenario_name", scenario.Name)

		runner := NewLoadTestRunner(scenario.Config, s.metrics)
		results, err := runner.RunLoadTest(ctx)
		if err != nil {
			s.logger.ErrorContext(ctx, "Failed to run benchmark scenario",
				"component", "monitoring.load_testing",
				"suite_name", s.Name,
				"scenario_name", scenario.Name,
				"error", err.Error())
			return fmt.Errorf("failed to run benchmark scenario %s: %w", scenario.Name, err)
		}

		s.Results[scenario.Name] = results
		s.logger.InfoContext(ctx, "Benchmark scenario completed",
			"component", "monitoring.load_testing",
			"suite_name", s.Name,
			"scenario_name", scenario.Name,
			"total_requests", results.TotalRequests,
			"throughput_rps", results.ThroughputRPS,
			"error_rate_percent", results.ErrorRate,
			"avg_response_time_ms", results.AvgResponseTime)
	}

	s.logger.InfoContext(ctx, "Benchmark suite execution completed",
		"component", "monitoring.load_testing",
		"suite_name", s.Name,
		"completed_scenarios", len(s.Results))

	return nil
}

// GetBenchmarkReport generates a comprehensive benchmark report
func (s *BenchmarkSuite) GetBenchmarkReport() map[string]interface{} {
	report := map[string]interface{}{
		"suite_name":      s.Name,
		"total_scenarios": len(s.Scenarios),
		"scenarios":       s.Scenarios,
		"results":         s.Results,
		"summary":         s.calculateSummary(),
		"generated_at":    time.Now(),
	}

	return report
}

// calculateSummary calculates summary statistics across all scenarios
func (s *BenchmarkSuite) calculateSummary() map[string]interface{} {
	if len(s.Results) == 0 {
		return map[string]interface{}{
			"total_requests":    0,
			"avg_throughput":    0.0,
			"avg_response_time": 0.0,
			"avg_error_rate":    0.0,
		}
	}

	var totalRequests int64
	var totalThroughput, totalResponseTime, totalErrorRate float64

	for _, result := range s.Results {
		totalRequests += result.TotalRequests
		totalThroughput += result.ThroughputRPS
		totalResponseTime += result.AvgResponseTime
		totalErrorRate += result.ErrorRate
	}

	scenarioCount := float64(len(s.Results))

	return map[string]interface{}{
		"total_requests":    totalRequests,
		"avg_throughput":    totalThroughput / scenarioCount,
		"avg_response_time": totalResponseTime / scenarioCount,
		"avg_error_rate":    totalErrorRate / scenarioCount,
		"best_scenario":     s.getBestScenario(),
		"worst_scenario":    s.getWorstScenario(),
	}
}

// getBestScenario returns the best performing scenario
func (s *BenchmarkSuite) getBestScenario() string {
	bestScenario := ""
	bestThroughput := 0.0

	for name, result := range s.Results {
		if result.ThroughputRPS > bestThroughput {
			bestThroughput = result.ThroughputRPS
			bestScenario = name
		}
	}

	return bestScenario
}

// getWorstScenario returns the worst performing scenario
func (s *BenchmarkSuite) getWorstScenario() string {
	worstScenario := ""
	worstErrorRate := 0.0

	for name, result := range s.Results {
		if result.ErrorRate > worstErrorRate {
			worstErrorRate = result.ErrorRate
			worstScenario = name
		}
	}

	return worstScenario
}

// DefaultBenchmarkScenarios returns a set of default benchmark scenarios
func DefaultBenchmarkScenarios() []BenchmarkScenario {
	return []BenchmarkScenario{
		{
			Name:        "Light Load",
			Description: "Low concurrency, short duration test",
			Config: &LoadTestConfig{
				ConcurrentUsers: 5,
				TestDuration:    30 * time.Second,
				RequestRate:     10,
				RampUpDuration:  5 * time.Second,
				Models:          []string{"test-model"},
				TestScenarios:   []string{"basic"},
				TargetEndpoint:  "/api/evaluate",
			},
		},
		{
			Name:        "Medium Load",
			Description: "Medium concurrency, medium duration test",
			Config: &LoadTestConfig{
				ConcurrentUsers: 20,
				TestDuration:    2 * time.Minute,
				RequestRate:     50,
				RampUpDuration:  10 * time.Second,
				Models:          []string{"test-model"},
				TestScenarios:   []string{"basic", "complex"},
				TargetEndpoint:  "/api/evaluate",
			},
		},
		{
			Name:        "Heavy Load",
			Description: "High concurrency, extended duration test",
			Config: &LoadTestConfig{
				ConcurrentUsers: 50,
				TestDuration:    5 * time.Minute,
				RequestRate:     100,
				RampUpDuration:  30 * time.Second,
				Models:          []string{"test-model"},
				TestScenarios:   []string{"basic", "complex", "stress"},
				TargetEndpoint:  "/api/evaluate",
			},
		},
	}
}
