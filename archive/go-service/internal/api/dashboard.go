package api

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/gorilla/websocket"
	"go-service/internal/monitoring"
)

// DashboardHandler handles dashboard-related API endpoints
type DashboardHandler struct {
	metrics     *monitoring.MetricsCollector
	analytics   *monitoring.AnalyticsService
	upgrader    websocket.Upgrader
	connections map[*websocket.Conn]bool
}

// NewDashboardHandler creates a new dashboard handler
func NewDashboardHandler(metrics *monitoring.MetricsCollector, analytics *monitoring.AnalyticsService) *DashboardHandler {
	return &DashboardHandler{
		metrics:   metrics,
		analytics: analytics,
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				return true // Allow all origins for development
			},
		},
		connections: make(map[*websocket.Conn]bool),
	}
}

// GetDashboardData returns comprehensive dashboard data
func (h *DashboardHandler) GetDashboardData(w http.ResponseWriter, r *http.Request) {
	timeframe := r.URL.Query().Get("timeframe")
	if timeframe == "" {
		timeframe = "24h"
	}

	// Get system analytics
	analytics, err := h.analytics.GetSystemAnalytics(r.Context())
	if err != nil {
		http.Error(w, "Failed to get system analytics", http.StatusInternalServerError)
		return
	}

	// Get performance metrics
	metrics, err := h.analytics.GetPerformanceMetrics(r.Context(), timeframe)
	if err != nil {
		http.Error(w, "Failed to get performance metrics", http.StatusInternalServerError)
		return
	}

	// Prepare dashboard data
	dashboardData := map[string]interface{}{
		"timestamp":           time.Now(),
		"timeframe":           timeframe,
		"system_analytics":    analytics,
		"performance_metrics": metrics,
		"summary": map[string]interface{}{
			"total_evaluations":  analytics.SystemHealth.TotalRequests,
			"success_rate":       h.calculateOverallSuccessRate(analytics.ModelComparison),
			"average_score":      h.calculateOverallAverageScore(analytics.ModelComparison),
			"models_tested":      len(analytics.ModelComparison),
			"active_connections": analytics.SystemHealth.ActiveConnections,
			"system_status":      analytics.SystemHealth.Status,
		},
		"charts": map[string]interface{}{
			"model_performance": h.prepareModelPerformanceChart(analytics.ModelComparison),
			"throughput_trends": h.prepareThroughputChart(analytics.ThroughputTrends),
			"error_rates":       h.prepareErrorRateChart(analytics.ErrorRates),
			"response_times":    h.prepareResponseTimeChart(analytics.ResponseTimes),
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(dashboardData)
}

// GetDashboardConfig returns dashboard configuration
func (h *DashboardHandler) GetDashboardConfig(w http.ResponseWriter, r *http.Request) {
	config := map[string]interface{}{
		"refresh_interval": 30, // seconds
		"chart_types": []string{
			"model_performance",
			"throughput_trends",
			"error_rates",
			"response_times",
		},
		"timeframe_options": []string{
			"1h", "24h", "7d", "30d",
		},
		"available_metrics": []string{
			"accuracy", "response_time", "throughput", "error_rate",
		},
		"websocket_endpoint": "/ws/dashboard",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(config)
}

// WebSocketHandler handles WebSocket connections for real-time updates
func (h *DashboardHandler) WebSocketHandler(w http.ResponseWriter, r *http.Request) {
	conn, err := h.upgrader.Upgrade(w, r, nil)
	if err != nil {
		http.Error(w, "Failed to upgrade connection", http.StatusBadRequest)
		return
	}
	defer conn.Close()

	// Register connection
	h.connections[conn] = true
	defer delete(h.connections, conn)

	// Send initial data
	h.sendDashboardUpdate(conn)

	// Handle incoming messages and keep connection alive
	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			break
		}

		// Send updated data
		h.sendDashboardUpdate(conn)
	}
}

// sendDashboardUpdate sends dashboard data to a WebSocket connection
func (h *DashboardHandler) sendDashboardUpdate(conn *websocket.Conn) {
	analytics, err := h.analytics.GetSystemAnalytics(context.Background())
	if err != nil {
		return
	}

	update := map[string]interface{}{
		"type":      "dashboard_update",
		"timestamp": time.Now(),
		"data": map[string]interface{}{
			"system_health":     analytics.SystemHealth,
			"model_comparison":  analytics.ModelComparison,
			"throughput_trends": analytics.ThroughputTrends,
			"error_rates":       analytics.ErrorRates,
		},
	}

	conn.WriteJSON(update)
}

// BroadcastUpdate broadcasts an update to all connected WebSocket clients
func (h *DashboardHandler) BroadcastUpdate(updateType string, data interface{}) {
	message := map[string]interface{}{
		"type":      updateType,
		"timestamp": time.Now(),
		"data":      data,
	}

	for conn := range h.connections {
		if err := conn.WriteJSON(message); err != nil {
			// Remove failed connection
			delete(h.connections, conn)
			conn.Close()
		}
	}
}

// GetDashboardHTML serves the dashboard HTML page
func (h *DashboardHandler) GetDashboardHTML(w http.ResponseWriter, r *http.Request) {
	html := `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Evaluation Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            margin: 0;
            font-size: 1.8rem;
        }
        
        .subtitle {
            opacity: 0.9;
            margin-top: 0.5rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 2rem;
        }
        
        .controls {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            display: flex;
            gap: 1rem;
            align-items: center;
        }
        
        .controls select, .controls button {
            padding: 0.5rem 1rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
        }
        
        .controls button {
            background: #667eea;
            color: white;
            border: none;
        }
        
        .controls button:hover {
            background: #5a6fd8;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-left: auto;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4caf50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .metric-title {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 0.5rem;
        }
        
        .metric-change {
            font-size: 0.8rem;
            color: #4caf50;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .chart-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #333;
        }
        
        .chart-container {
            height: 300px;
            position: relative;
        }
        
        .models-table {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .table-header {
            background: #f8f9fa;
            padding: 1rem;
            border-bottom: 1px solid #dee2e6;
        }
        
        .table-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin: 0;
        }
        
        .table-container {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        
        .score-bar {
            width: 100px;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            position: relative;
            overflow: hidden;
        }
        
        .score-fill {
            height: 100%;
            background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 0 1rem;
            }
            
            .controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .status-indicator {
                margin-left: 0;
                margin-top: 1rem;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>LLM Evaluation Performance Dashboard</h1>
        <div class="subtitle">Real-time monitoring and analytics for model evaluation performance</div>
    </div>
    
    <div class="container">
        <div class="controls">
            <label for="timeframe">Timeframe:</label>
            <select id="timeframe">
                <option value="1h">Last Hour</option>
                <option value="24h" selected>Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
            </select>
            
            <button onclick="refreshDashboard()">Refresh</button>
            
            <label>
                <input type="checkbox" id="auto-refresh" checked> Auto-refresh
            </label>
            
            <div class="status-indicator">
                <div class="status-dot"></div>
                <span id="connection-status">Connected</span>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Total Evaluations</div>
                <div class="metric-value" id="total-evaluations">-</div>
                <div class="metric-change" id="evaluations-change">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Success Rate</div>
                <div class="metric-value" id="success-rate">-</div>
                <div class="metric-change" id="success-change">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Average Score</div>
                <div class="metric-value" id="average-score">-</div>
                <div class="metric-change" id="score-change">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Models Tested</div>
                <div class="metric-value" id="models-tested">-</div>
                <div class="metric-change" id="models-change">-</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">Model Performance Comparison</div>
                <div class="chart-container">
                    <canvas id="model-performance-chart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">Throughput Trends</div>
                <div class="chart-container">
                    <canvas id="throughput-chart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">Error Rates by Model</div>
                <div class="chart-container">
                    <canvas id="error-rate-chart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">Response Times by Test Type</div>
                <div class="chart-container">
                    <canvas id="response-time-chart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="models-table">
            <div class="table-header">
                <h3 class="table-title">Model Performance Details</h3>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Model</th>
                            <th>Provider</th>
                            <th>Evaluations</th>
                            <th>Success Rate</th>
                            <th>Avg Score</th>
                            <th>Response Time</th>
                            <th>Last Evaluation</th>
                        </tr>
                    </thead>
                    <tbody id="models-table-body">
                        <tr>
                            <td colspan="7" class="loading">Loading model data...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        let charts = {};
        let websocket;
        let autoRefreshInterval;
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeDashboard();
            connectWebSocket();
            setupEventListeners();
        });
        
        function initializeDashboard() {
            loadDashboardData();
            setupAutoRefresh();
        }
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            websocket = new WebSocket(protocol + '//' + window.location.host + '/ws/dashboard');
            
            websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'dashboard_update') {
                    updateDashboard(data.data);
                }
            };
            
            websocket.onopen = function() {
                document.getElementById('connection-status').textContent = 'Connected';
            };
            
            websocket.onclose = function() {
                document.getElementById('connection-status').textContent = 'Disconnected';
                // Reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };
        }
        
        function setupEventListeners() {
            document.getElementById('timeframe').addEventListener('change', function() {
                loadDashboardData();
            });
            
            document.getElementById('auto-refresh').addEventListener('change', function() {
                if (this.checked) {
                    setupAutoRefresh();
                } else {
                    clearInterval(autoRefreshInterval);
                }
            });
        }
        
        function setupAutoRefresh() {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(loadDashboardData, 30000); // 30 seconds
        }
        
        async function loadDashboardData() {
            try {
                const timeframe = document.getElementById('timeframe').value;
                const response = await fetch('/dashboard/api/data?timeframe=' + timeframe);
                const data = await response.json();
                
                updateDashboard(data);
            } catch (error) {
                console.error('Error loading dashboard data:', error);
                showError('Failed to load dashboard data');
            }
        }
        
        function updateDashboard(data) {
            updateMetrics(data.summary);
            updateCharts(data.charts);
            updateModelsTable(data.system_analytics.model_comparison);
        }
        
        function updateMetrics(summary) {
            document.getElementById('total-evaluations').textContent = summary.total_evaluations || 0;
            document.getElementById('success-rate').textContent = summary.success_rate ? (summary.success_rate * 100).toFixed(1) + '%' : '0%';
            document.getElementById('average-score').textContent = summary.average_score ? summary.average_score.toFixed(2) : '0.00';
            document.getElementById('models-tested').textContent = summary.models_tested || 0;
        }
        
        function updateCharts(chartData) {
            if (chartData.model_performance) {
                updateModelPerformanceChart(chartData.model_performance);
            }
            if (chartData.throughput_trends) {
                updateThroughputChart(chartData.throughput_trends);
            }
            if (chartData.error_rates) {
                updateErrorRateChart(chartData.error_rates);
            }
            if (chartData.response_times) {
                updateResponseTimeChart(chartData.response_times);
            }
        }
        
        function updateModelPerformanceChart(data) {
            const ctx = document.getElementById('model-performance-chart').getContext('2d');
            
            if (charts.modelPerformance) {
                charts.modelPerformance.destroy();
            }
            
            charts.modelPerformance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        label: 'Average Score',
                        data: data.scores || [],
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 1
                        }
                    }
                }
            });
        }
        
        function updateThroughputChart(data) {
            const ctx = document.getElementById('throughput-chart').getContext('2d');
            
            if (charts.throughput) {
                charts.throughput.destroy();
            }
            
            charts.throughput = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        label: 'Requests/Second',
                        data: data.throughput || [],
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        function updateErrorRateChart(data) {
            const ctx = document.getElementById('error-rate-chart').getContext('2d');
            
            if (charts.errorRate) {
                charts.errorRate.destroy();
            }
            
            charts.errorRate = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        data: data.rates || [],
                        backgroundColor: [
                            '#ff6384',
                            '#36a2eb',
                            '#cc65fe',
                            '#ffce56',
                            '#4bc0c0',
                            '#9966ff',
                            '#ff9f40'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
        
        function updateResponseTimeChart(data) {
            const ctx = document.getElementById('response-time-chart').getContext('2d');
            
            if (charts.responseTime) {
                charts.responseTime.destroy();
            }
            
            charts.responseTime = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        label: 'Response Time (seconds)',
                        data: data.times || [],
                        backgroundColor: 'rgba(255, 159, 64, 0.8)',
                        borderColor: 'rgba(255, 159, 64, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        function updateModelsTable(models) {
            const tbody = document.getElementById('models-table-body');
            tbody.innerHTML = '';
            
            if (!models || models.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="loading">No model data available</td></tr>';
                return;
            }
            
            models.forEach(model => {
                const row = document.createElement('tr');
                row.innerHTML = 
                    '<td>' + model.model_name + '</td>' +
                    '<td>' + model.model_provider + '</td>' +
                    '<td>' + model.total_evaluations + '</td>' +
                    '<td>' +
                        '<div class="score-bar">' +
                            '<div class="score-fill" style="width: ' + model.success_rate + '%"></div>' +
                        '</div>' +
                        model.success_rate.toFixed(1) + '%' +
                    '</td>' +
                    '<td>' + model.avg_score.toFixed(2) + '</td>' +
                    '<td>' + model.avg_response_time.toFixed(2) + 's</td>' +
                    '<td>' + new Date(model.last_evaluation).toLocaleString() + '</td>';
                tbody.appendChild(row);
            });
        }
        
        function refreshDashboard() {
            loadDashboardData();
        }
        
        function showError(message) {
            const container = document.querySelector('.container');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            container.insertBefore(errorDiv, container.firstChild);
            
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }
    </script>
</body>
</html>
    `

	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html))
}

// RegisterDashboardRoutes registers all dashboard-related routes
func (h *DashboardHandler) RegisterDashboardRoutes(router *mux.Router) {
	// Dashboard UI
	router.HandleFunc("/dashboard", h.GetDashboardHTML).Methods("GET")

	// Dashboard API endpoints
	router.HandleFunc("/dashboard/api/data", h.GetDashboardData).Methods("GET")
	router.HandleFunc("/dashboard/api/config", h.GetDashboardConfig).Methods("GET")

	// WebSocket endpoint
	router.HandleFunc("/ws/dashboard", h.WebSocketHandler)
}

// Helper methods for chart data preparation
func (h *DashboardHandler) prepareModelPerformanceChart(models []monitoring.ModelStats) map[string]interface{} {
	labels := make([]string, len(models))
	scores := make([]float64, len(models))

	for i, model := range models {
		labels[i] = model.ModelProvider + "/" + model.ModelName
		scores[i] = model.AvgScore
	}

	return map[string]interface{}{
		"labels": labels,
		"scores": scores,
	}
}

func (h *DashboardHandler) prepareThroughputChart(trends []monitoring.ThroughputPoint) map[string]interface{} {
	labels := make([]string, len(trends))
	throughput := make([]float64, len(trends))

	for i, trend := range trends {
		labels[i] = trend.Timestamp.Format("15:04")
		throughput[i] = trend.Throughput
	}

	return map[string]interface{}{
		"labels":     labels,
		"throughput": throughput,
	}
}

func (h *DashboardHandler) prepareErrorRateChart(errorRates map[string]float64) map[string]interface{} {
	labels := make([]string, 0, len(errorRates))
	rates := make([]float64, 0, len(errorRates))

	for model, rate := range errorRates {
		labels = append(labels, model)
		rates = append(rates, rate)
	}

	return map[string]interface{}{
		"labels": labels,
		"rates":  rates,
	}
}

func (h *DashboardHandler) prepareResponseTimeChart(responseTimes map[string]float64) map[string]interface{} {
	labels := make([]string, 0, len(responseTimes))
	times := make([]float64, 0, len(responseTimes))

	for testType, time := range responseTimes {
		labels = append(labels, testType)
		times = append(times, time)
	}

	return map[string]interface{}{
		"labels": labels,
		"times":  times,
	}
}

// Helper methods for calculations
func (h *DashboardHandler) calculateOverallSuccessRate(models []monitoring.ModelStats) float64 {
	if len(models) == 0 {
		return 0.0
	}

	total := 0.0
	for _, model := range models {
		total += model.SuccessRate
	}
	return total / float64(len(models))
}

func (h *DashboardHandler) calculateOverallAverageScore(models []monitoring.ModelStats) float64 {
	if len(models) == 0 {
		return 0.0
	}

	total := 0.0
	for _, model := range models {
		total += model.AvgScore
	}
	return total / float64(len(models))
}
