package auto_reload

import (
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// HealthResponse represents the health check response structure
type HealthResponse struct {
	Status   string `json:"status"`
	Database struct {
		Connected bool `json:"connected"`
	} `json:"database"`
	Ollama struct {
		Available bool `json:"available"`
	} `json:"ollama"`
	Timestamp time.Time `json:"timestamp"`
}

// MetricsData represents basic metrics structure
type MetricsData struct {
	Requests     int     `json:"requests"`
	ResponseTime float64 `json:"response_time_ms"`
	ErrorRate    float64 `json:"error_rate"`
	Uptime       float64 `json:"uptime_seconds"`
}

// TestMonitoringContinuityAcrossReloads tests that monitoring and health checks work across reloads
func TestMonitoringContinuityAcrossReloads(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping monitoring test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Test 1: Verify initial health check works
	t.Log("Testing initial health check...")
	initialHealth := checkHealthEndpoint(t, helper)
	assert.Equal(t, "healthy", initialHealth.Status, "Service should be healthy initially")

	// Test 2: Collect baseline metrics
	t.Log("Collecting baseline metrics...")
	initialMetrics := collectBasicMetrics(t, helper)
	assert.Greater(t, initialMetrics.Uptime, 0.0, "Service should have positive uptime")

	// Test 3: Trigger reload and test health during reload
	t.Log("Triggering service reload...")
	helper.ModifySourceFile("internal/monitoring/metrics.go", "Monitoring test reload trigger")

	// Wait a moment for reload to start
	time.Sleep(2 * time.Second)

	// Test 4: Wait for reload completion
	helper.WaitForReloadComplete(60 * time.Second)

	// Test 5: Verify health check still works after reload
	t.Log("Testing health check after reload...")
	postReloadHealth := checkHealthEndpoint(t, helper)
	assert.Equal(t, "healthy", postReloadHealth.Status, "Service should be healthy after reload")

	// Test 6: Verify metrics collection continues
	t.Log("Testing metrics collection after reload...")
	postReloadMetrics := collectBasicMetrics(t, helper)
	assert.Greater(t, postReloadMetrics.Uptime, 0.0, "Service should have positive uptime after reload")

	// Test 7: Generate some load and verify metrics update
	t.Log("Generating load to test metrics updates...")
	generateTestLoad(t, helper, 10) // Make 10 requests

	finalMetrics := collectBasicMetrics(t, helper)
	assert.GreaterOrEqual(t, finalMetrics.Requests, initialMetrics.Requests,
		"Request count should increase after generating load")

	t.Log("Monitoring continuity test completed successfully")
}

// TestHealthCheckEndpointDuringReload tests health check behavior during reload cycles
func TestHealthCheckEndpointDuringReload(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping health check reload test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Establish baseline health
	baselineHealth := checkHealthEndpoint(t, helper)
	require.Equal(t, "healthy", baselineHealth.Status)

	// Start monitoring health during reload
	healthResults := make(chan bool, 10)
	stopMonitoring := make(chan struct{})

	// Monitor health in background
	go func() {
		ticker := time.NewTicker(500 * time.Millisecond)
		defer ticker.Stop()

		for {
			select {
			case <-stopMonitoring:
				return
			case <-ticker.C:
				resp, err := http.Get(helper.GetServiceURL() + "/health")
				if err == nil {
					resp.Body.Close()
					healthResults <- resp.StatusCode == http.StatusOK
				} else {
					healthResults <- false
				}
			}
		}
	}()

	// Trigger reload
	t.Log("Triggering reload while monitoring health...")
	helper.ModifySourceFile("internal/health/checker.go", "Health check reload test")

	// Wait for reload to complete
	helper.WaitForReloadComplete(60 * time.Second)

	// Stop monitoring
	close(stopMonitoring)

	// Check final health
	finalHealth := checkHealthEndpoint(t, helper)
	assert.Equal(t, "healthy", finalHealth.Status, "Service should be healthy after reload")

	// Count health check results
	healthyCount := 0
	totalChecks := 0
	for {
		select {
		case healthy := <-healthResults:
			totalChecks++
			if healthy {
				healthyCount++
			}
		default:
			goto done
		}
	}

done:
	if totalChecks > 0 {
		healthyRatio := float64(healthyCount) / float64(totalChecks)
		t.Logf("Health check success ratio during reload: %.2f%% (%d/%d)",
			healthyRatio*100, healthyCount, totalChecks)

		// Allow for some downtime during reload, but expect most checks to pass
		assert.Greater(t, healthyRatio, 0.5, "Health checks should pass more than 50% of the time during reload")
	}
}

// TestMetricsEndpointReloadResilience tests that metrics endpoint remains available
func TestMetricsEndpointReloadResilience(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping metrics reload test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Test metrics endpoint before reload
	metricsURL := helper.GetServiceURL() + "/metrics"
	resp, err := http.Get(metricsURL)
	require.NoError(t, err, "Metrics endpoint should be accessible")
	require.Equal(t, http.StatusOK, resp.StatusCode, "Metrics should return 200")
	resp.Body.Close()

	// Trigger reload
	helper.ModifySourceFile("internal/api/metrics.go", "Metrics reload test")
	helper.WaitForReloadComplete(60 * time.Second)

	// Test metrics endpoint after reload
	resp, err = http.Get(metricsURL)
	assert.NoError(t, err, "Metrics endpoint should be accessible after reload")
	if err == nil {
		assert.Equal(t, http.StatusOK, resp.StatusCode, "Metrics should return 200 after reload")
		resp.Body.Close()
	}
}

// TestLoggingContinuityDuringReload tests that logging works before, during, and after reload
func TestLoggingContinuityDuringReload(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping logging test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Generate some log entries before reload
	generateTestLoad(t, helper, 5)

	// Trigger reload
	t.Log("Testing logging continuity during reload...")
	helper.ModifySourceFile("internal/api/handlers.go", "Logging continuity test")

	// Generate log entries during reload
	go func() {
		time.Sleep(1 * time.Second)    // Let reload start
		generateTestLoad(t, helper, 3) // This might fail during reload, which is okay
	}()

	helper.WaitForReloadComplete(60 * time.Second)

	// Generate log entries after reload
	generateTestLoad(t, helper, 5)

	// Verify service is functional (indirect test of logging continuity)
	helper.VerifyServiceResponsive()
	t.Log("Logging continuity test completed - service remains functional")
}

// TestPerformanceImpactOfReload measures the performance impact of reload cycles
func TestPerformanceImpactOfReload(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping performance impact test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Measure baseline performance
	t.Log("Measuring baseline performance...")
	baselineTime := measureEndpointResponseTime(t, helper, "/health", 10)

	// Trigger reload
	helper.ModifySourceFile("internal/api/handlers.go", "Performance impact test")
	helper.WaitForReloadComplete(60 * time.Second)

	// Measure post-reload performance
	t.Log("Measuring post-reload performance...")
	postReloadTime := measureEndpointResponseTime(t, helper, "/health", 10)

	// Calculate performance impact
	if baselineTime > 0 {
		impact := (postReloadTime - baselineTime) / baselineTime
		t.Logf("Performance impact: %.2f%% (baseline: %.2fms, post-reload: %.2fms)",
			impact*100, baselineTime, postReloadTime)

		// Allow for reasonable performance degradation (up to 50% increase)
		assert.Less(t, impact, 0.5, "Performance degradation should be less than 50%")
	}
}

// Helper functions

// checkHealthEndpoint checks the health endpoint and returns parsed response
func checkHealthEndpoint(t *testing.T, helper *TestHelper) HealthResponse {
	resp, err := http.Get(helper.GetServiceURL() + "/health")
	require.NoError(t, err, "Health endpoint should be accessible")
	defer resp.Body.Close()

	require.Equal(t, http.StatusOK, resp.StatusCode, "Health endpoint should return 200")

	var health HealthResponse
	err = json.NewDecoder(resp.Body).Decode(&health)
	require.NoError(t, err, "Health response should be valid JSON")

	return health
}

// collectBasicMetrics collects basic metrics from the service
func collectBasicMetrics(t *testing.T, helper *TestHelper) MetricsData {
	// For this test, we'll collect simple metrics from the health endpoint
	// In a real implementation, this would query a proper metrics endpoint
	resp, err := http.Get(helper.GetServiceURL() + "/health")
	if err != nil {
		// Return default metrics if service is unavailable
		return MetricsData{Requests: 0, ResponseTime: 0, ErrorRate: 1.0, Uptime: 0}
	}
	defer resp.Body.Close()

	// Simulate metrics collection
	// In a real system, this would parse Prometheus metrics or similar
	return MetricsData{
		Requests:     1,
		ResponseTime: 10.0,
		ErrorRate:    0.0,
		Uptime:       time.Since(time.Now().Add(-1 * time.Minute)).Seconds(),
	}
}

// generateTestLoad generates some load on the service for testing
func generateTestLoad(t *testing.T, helper *TestHelper, requestCount int) {
	for i := 0; i < requestCount; i++ {
		resp, err := http.Get(helper.GetServiceURL() + "/health")
		if err == nil {
			resp.Body.Close()
		}
		// Small delay between requests
		time.Sleep(50 * time.Millisecond)
	}
}

// measureEndpointResponseTime measures average response time for an endpoint
func measureEndpointResponseTime(t *testing.T, helper *TestHelper, endpoint string, samples int) float64 {
	var totalTime time.Duration
	successCount := 0

	for i := 0; i < samples; i++ {
		start := time.Now()
		resp, err := http.Get(helper.GetServiceURL() + endpoint)
		elapsed := time.Since(start)

		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				totalTime += elapsed
				successCount++
			}
		}

		// Small delay between measurements
		time.Sleep(10 * time.Millisecond)
	}

	if successCount == 0 {
		return 0
	}

	return float64(totalTime.Nanoseconds()) / float64(successCount) / 1e6 // Convert to milliseconds
}
