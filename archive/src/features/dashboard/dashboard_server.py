"""
Dashboard Server for LLM Evaluation System
Web-based interface for viewing evaluation results and metrics
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None

from ...core.database import DatabaseManager, EvaluationResult, EvaluationSummary
from ...core.config_manager import get_config
from .visualization import VisualizationManager
from .report_generator import ReportGenerator
from .go_service_integration import GoServiceIntegration, check_go_service_availability


class DashboardServer:
    """Web dashboard server for LLM evaluation results"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for dashboard. Install with: pip install fastapi uvicorn jinja2")
        
        self.app = FastAPI(title="LLM Evaluation Dashboard", version="1.0.0")
        self.db_manager = db_manager
        self.visualization_manager = VisualizationManager()
        self.report_generator = ReportGenerator()
        self.active_connections: List[WebSocket] = []
        
        # Go service integration
        self.go_service_integration = GoServiceIntegration()
        
        # Setup templates and static files
        self._setup_templates_and_static()
        
        # Setup routes
        self._setup_routes()
        
        # Configuration
        self.config = get_config()
    
    def _setup_templates_and_static(self):
        """Setup templates and static file directories"""
        # Create directories if they don't exist
        dashboard_dir = Path(__file__).parent
        templates_dir = dashboard_dir / "templates"
        static_dir = dashboard_dir / "static"
        
        templates_dir.mkdir(exist_ok=True)
        static_dir.mkdir(exist_ok=True)
        
        # Create basic templates if they don't exist
        self._create_default_templates(templates_dir)
        self._create_default_static_files(static_dir)
        
        # Setup FastAPI templates and static files
        self.templates = Jinja2Templates(directory=str(templates_dir))
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    def _create_default_templates(self, templates_dir: Path):
        """Create default HTML templates"""
        # Main dashboard template
        dashboard_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Evaluation Dashboard</title>
    <link href="/static/style.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="/static/dashboard.js"></script>
</head>
<body>
    <nav class="navbar">
        <div class="nav-container">
            <h1>LLM Evaluation Dashboard</h1>
            <div class="nav-links">
                <a href="/" class="nav-link">Dashboard</a>
                <a href="/evaluations" class="nav-link">Evaluations</a>
                <a href="/metrics" class="nav-link">Metrics</a>
                <a href="/reports" class="nav-link">Reports</a>
            </div>
        </div>
    </nav>
    
    <main class="main-content">
        <div class="container">
            <div class="dashboard-header">
                <h2>Evaluation Overview</h2>
                <div class="refresh-controls">
                    <label>
                        <input type="checkbox" id="auto-refresh" checked>
                        Auto-refresh (30s)
                    </label>
                    <button onclick="refreshDashboard()" class="btn btn-primary">Refresh</button>
                </div>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Total Evaluations</h3>
                    <div class="metric-value" id="total-evaluations">-</div>
                </div>
                <div class="metric-card">
                    <h3>Success Rate</h3>
                    <div class="metric-value" id="success-rate">-</div>
                </div>
                <div class="metric-card">
                    <h3>Average Score</h3>
                    <div class="metric-value" id="average-score">-</div>
                </div>
                <div class="metric-card">
                    <h3>Models Tested</h3>
                    <div class="metric-value" id="models-tested">-</div>
                </div>
            </div>
            
            <div class="charts-container">
                <div class="chart-section">
                    <h3>Score Distribution</h3>
                    <canvas id="score-chart"></canvas>
                </div>
                <div class="chart-section">
                    <h3>Results Over Time</h3>
                    <canvas id="timeline-chart"></canvas>
                </div>
            </div>
            
            <div class="recent-evaluations">
                <h3>Recent Evaluations</h3>
                <div class="table-container">
                    <table id="evaluations-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Model</th>
                                <th>Test Type</th>
                                <th>Score</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="evaluations-tbody">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>
    
    <script>
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeDashboard();
        });
    </script>
</body>
</html>
        """
        
        with open(templates_dir / "dashboard.html", "w") as f:
            f.write(dashboard_template)
        
        # Evaluation details template
        evaluation_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Details - LLM Dashboard</title>
    <link href="/static/style.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar">
        <div class="nav-container">
            <h1>LLM Evaluation Dashboard</h1>
            <div class="nav-links">
                <a href="/" class="nav-link">Dashboard</a>
                <a href="/evaluations" class="nav-link active">Evaluations</a>
                <a href="/metrics" class="nav-link">Metrics</a>
                <a href="/reports" class="nav-link">Reports</a>
            </div>
        </div>
    </nav>
    
    <main class="main-content">
        <div class="container">
            <div class="evaluation-details">
                <h2>Evaluation #{{ evaluation.id }}</h2>
                
                <div class="evaluation-info">
                    <div class="info-grid">
                        <div class="info-item">
                            <label>Model:</label>
                            <span>{{ evaluation.model_provider }}/{{ evaluation.model_name }}</span>
                        </div>
                        <div class="info-item">
                            <label>Test Type:</label>
                            <span>{{ evaluation.test_type }}</span>
                        </div>
                        <div class="info-item">
                            <label>Score:</label>
                            <span class="score-badge score-{{ 'pass' if evaluation.passed else 'fail' }}">
                                {{ "%.2f"|format(evaluation.score) }}
                            </span>
                        </div>
                        <div class="info-item">
                            <label>Status:</label>
                            <span class="status-badge status-{{ 'pass' if evaluation.passed else 'fail' }}">
                                {{ 'PASSED' if evaluation.passed else 'FAILED' }}
                            </span>
                        </div>
                        <div class="info-item">
                            <label>Execution Time:</label>
                            <span>{{ "%.2f"|format(evaluation.execution_time) }}s</span>
                        </div>
                        <div class="info-item">
                            <label>Timestamp:</label>
                            <span>{{ evaluation.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</span>
                        </div>
                    </div>
                </div>
                
                <div class="evaluation-content">
                    <div class="content-section">
                        <h3>Query</h3>
                        <div class="content-box">{{ evaluation.query }}</div>
                    </div>
                    
                    <div class="content-section">
                        <h3>Response</h3>
                        <div class="content-box">{{ evaluation.response }}</div>
                    </div>
                    
                    {% if evaluation.expected_response %}
                    <div class="content-section">
                        <h3>Expected Response</h3>
                        <div class="content-box">{{ evaluation.expected_response }}</div>
                    </div>
                    {% endif %}
                    
                    {% if evaluation.metrics %}
                    <div class="content-section">
                        <h3>Metrics</h3>
                        <div class="metrics-details">
                            {% for metric, value in evaluation.metrics.items() %}
                            <div class="metric-item">
                                <span class="metric-name">{{ metric }}:</span>
                                <span class="metric-value">{{ "%.3f"|format(value) if value is number else value }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                    
                    {% if evaluation.error_message %}
                    <div class="content-section error-section">
                        <h3>Error</h3>
                        <div class="error-box">{{ evaluation.error_message }}</div>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </main>
</body>
</html>
        """
        
        with open(templates_dir / "evaluation_detail.html", "w") as f:
            f.write(evaluation_template)
    
    def _create_default_static_files(self, static_dir: Path):
        """Create default static files"""
        # CSS file
        css_content = """
/* Dashboard CSS */
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

.navbar {
    background-color: #2c3e50;
    color: white;
    padding: 1rem 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.nav-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.nav-links {
    display: flex;
    gap: 2rem;
}

.nav-link {
    color: white;
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.nav-link:hover, .nav-link.active {
    background-color: #34495e;
}

.main-content {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 2rem;
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
}

.refresh-controls {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.btn {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background-color 0.2s;
}

.btn-primary {
    background-color: #3498db;
    color: white;
}

.btn-primary:hover {
    background-color: #2980b9;
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
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
}

.metric-card h3 {
    color: #666;
    font-size: 0.9rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
}

.metric-value {
    font-size: 2rem;
    font-weight: bold;
    color: #2c3e50;
}

.charts-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
    margin-bottom: 2rem;
}

.chart-section {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.chart-section h3 {
    margin-bottom: 1rem;
    color: #2c3e50;
}

.recent-evaluations {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.table-container {
    overflow-x: auto;
    margin-top: 1rem;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #eee;
}

th {
    background-color: #f8f9fa;
    font-weight: 600;
    color: #2c3e50;
}

.score-badge, .status-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
}

.score-pass, .status-pass {
    background-color: #d4edda;
    color: #155724;
}

.score-fail, .status-fail {
    background-color: #f8d7da;
    color: #721c24;
}

.evaluation-details {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.info-item {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid #eee;
}

.info-item label {
    font-weight: 600;
    color: #666;
}

.content-section {
    margin-bottom: 2rem;
}

.content-section h3 {
    margin-bottom: 1rem;
    color: #2c3e50;
}

.content-box {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    border-left: 4px solid #3498db;
    white-space: pre-wrap;
}

.error-box {
    background-color: #f8d7da;
    border-left-color: #dc3545;
    color: #721c24;
}

.metrics-details {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
}

.metric-item {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.metric-name {
    font-weight: 600;
    color: #666;
}

@media (max-width: 768px) {
    .nav-container {
        flex-direction: column;
        gap: 1rem;
    }
    
    .nav-links {
        flex-wrap: wrap;
        justify-content: center;
    }
    
    .dashboard-header {
        flex-direction: column;
        gap: 1rem;
        align-items: flex-start;
    }
    
    .metrics-grid {
        grid-template-columns: 1fr;
    }
    
    .charts-container {
        grid-template-columns: 1fr;
    }
}
        """
        
        with open(static_dir / "style.css", "w") as f:
            f.write(css_content)
        
        # JavaScript file
        js_content = """
// Dashboard JavaScript
let autoRefreshInterval;
let scoreChart, timelineChart;

function initializeDashboard() {
    setupAutoRefresh();
    loadDashboardData();
    initializeCharts();
    connectWebSocket();
}

function setupAutoRefresh() {
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', function() {
            if (this.checked) {
                autoRefreshInterval = setInterval(loadDashboardData, 30000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        });
        
        // Start auto-refresh by default
        if (autoRefreshCheckbox.checked) {
            autoRefreshInterval = setInterval(loadDashboardData, 30000);
        }
    }
}

async function loadDashboardData() {
    try {
        const response = await fetch('/api/dashboard/summary');
        const data = await response.json();
        
        updateMetrics(data);
        updateEvaluationsTable(data.recent_evaluations || []);
        updateCharts(data);
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateMetrics(data) {
    const elements = {
        'total-evaluations': data.total_evaluations || 0,
        'success-rate': data.success_rate ? (data.success_rate * 100).toFixed(1) + '%' : '0%',
        'average-score': data.average_score ? data.average_score.toFixed(2) : '0.00',
        'models-tested': data.models_tested ? data.models_tested.length : 0
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
}

function updateEvaluationsTable(evaluations) {
    const tbody = document.getElementById('evaluations-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    evaluations.forEach(evaluation => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(evaluation.timestamp).toLocaleString()}</td>
            <td>${evaluation.model_provider}/${evaluation.model_name}</td>
            <td>${evaluation.test_type}</td>
            <td><span class="score-badge score-${evaluation.passed ? 'pass' : 'fail'}">${evaluation.score.toFixed(2)}</span></td>
            <td><span class="status-badge status-${evaluation.passed ? 'pass' : 'fail'}">${evaluation.passed ? 'PASSED' : 'FAILED'}</span></td>
            <td><a href="/evaluations/${evaluation.id}" class="btn btn-primary">View</a></td>
        `;
        tbody.appendChild(row);
    });
}

function initializeCharts() {
    const scoreCtx = document.getElementById('score-chart');
    const timelineCtx = document.getElementById('timeline-chart');
    
    if (scoreCtx) {
        scoreChart = new Chart(scoreCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Score Distribution',
                    data: [],
                    backgroundColor: '#3498db',
                    borderColor: '#2980b9',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1
                    }
                }
            }
        });
    }
    
    if (timelineCtx) {
        timelineChart = new Chart(timelineCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Average Score',
                    data: [],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1
                    }
                }
            }
        });
    }
}

function updateCharts(data) {
    // Update score distribution chart
    if (scoreChart && data.score_distribution) {
        scoreChart.data.labels = Object.keys(data.score_distribution);
        scoreChart.data.datasets[0].data = Object.values(data.score_distribution);
        scoreChart.update();
    }
    
    // Update timeline chart
    if (timelineChart && data.timeline_data) {
        timelineChart.data.labels = data.timeline_data.map(d => new Date(d.date).toLocaleDateString());
        timelineChart.data.datasets[0].data = data.timeline_data.map(d => d.average_score);
        timelineChart.update();
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'evaluation_update') {
            loadDashboardData();
        }
    };
    
    ws.onclose = function() {
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
    };
}

function refreshDashboard() {
    loadDashboardData();
}

// Utility functions
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

function formatScore(score) {
    return score.toFixed(2);
}
        """
        
        with open(static_dir / "dashboard.js", "w") as f:
            f.write(js_content)
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            return self.templates.TemplateResponse("dashboard.html", {"request": request})
        
        @self.app.get("/api/dashboard/summary")
        async def get_dashboard_summary():
            if not self.db_manager:
                return {"error": "Database not available"}
            
            try:
                summary = await self.db_manager.get_summary()
                recent_evaluations = await self.db_manager.get_recent_results(limit=10)
                
                # Convert to dict format for JSON response
                summary_dict = {
                    "total_evaluations": summary.total_evaluations,
                    "passed_evaluations": summary.passed_evaluations,
                    "failed_evaluations": summary.failed_evaluations,
                    "error_evaluations": summary.error_evaluations,
                    "average_score": summary.average_score,
                    "average_execution_time": summary.average_execution_time,
                    "success_rate": summary.success_rate,
                    "models_tested": summary.models_tested,
                    "test_types": summary.test_types,
                    "recent_evaluations": [
                        {
                            "id": result.id,
                            "timestamp": result.timestamp.isoformat(),
                            "model_provider": result.model_provider,
                            "model_name": result.model_name,
                            "test_type": result.test_type,
                            "score": result.score,
                            "passed": result.passed,
                            "execution_time": result.execution_time
                        }
                        for result in recent_evaluations
                    ]
                }
                
                return summary_dict
                
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.get("/evaluations/{evaluation_id}", response_class=HTMLResponse)
        async def evaluation_detail(request: Request, evaluation_id: int):
            if not self.db_manager:
                raise HTTPException(status_code=500, detail="Database not available")
            
            evaluation = await self.db_manager.get_result(evaluation_id)
            if not evaluation:
                raise HTTPException(status_code=404, detail="Evaluation not found")
            
            return self.templates.TemplateResponse(
                "evaluation_detail.html", 
                {"request": request, "evaluation": evaluation}
            )
        
        @self.app.get("/api/evaluations")
        async def get_evaluations(
            limit: int = 50,
            offset: int = 0,
            model_provider: Optional[str] = None,
            model_name: Optional[str] = None,
            test_type: Optional[str] = None
        ):
            if not self.db_manager:
                return {"error": "Database not available"}
            
            try:
                results = await self.db_manager.get_results(
                    model_provider=model_provider,
                    model_name=model_name,
                    test_type=test_type,
                    limit=limit,
                    offset=offset
                )
                
                return {
                    "evaluations": [
                        {
                            "id": result.id,
                            "timestamp": result.timestamp.isoformat(),
                            "model_provider": result.model_provider,
                            "model_name": result.model_name,
                            "test_name": result.test_name,
                            "test_type": result.test_type,
                            "query": result.query,
                            "response": result.response,
                            "score": result.score,
                            "passed": result.passed,
                            "execution_time": result.execution_time,
                            "metrics": result.metrics,
                            "error_message": result.error_message
                        }
                        for result in results
                    ]
                }
                
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.get("/api/metrics/summary")
        async def get_metrics_summary():
            # This would integrate with the metrics manager
            return {
                "available_metrics": [
                    "relevance", "accuracy", "coherence", 
                    "similarity", "bias", "toxicity"
                ],
                "enabled_metrics": [
                    "relevance", "accuracy", "coherence"
                ]
            }
        
        @self.app.get("/api/go-service/health")
        async def get_go_service_health():
            """Get Go service health status"""
            is_available = await check_go_service_availability()
            return {"available": is_available, "timestamp": datetime.now().isoformat()}
        
        @self.app.get("/api/go-service/metrics")
        async def get_go_service_metrics(request: Request):
            """Get Go service metrics"""
            timeframe = request.query_params.get("timeframe", "24h")
            metrics = await self.go_service_integration.get_consolidated_metrics(timeframe)
            return metrics
        
        @self.app.get("/api/go-service/models/{model_name}/{model_provider}")
        async def get_model_performance(model_name: str, model_provider: str, request: Request):
            """Get performance metrics for specific model"""
            timeframe = request.query_params.get("timeframe", "24h")
            trends = await self.go_service_integration.get_model_performance_trends(
                model_name, model_provider, timeframe
            )
            return {"model_name": model_name, "model_provider": model_provider, "trends": trends}
        
        @self.app.post("/api/go-service/benchmark")
        async def run_benchmark(config: Dict[str, Any]):
            """Run performance benchmark using Go service"""
            result = await self.go_service_integration.run_performance_benchmark(config)
            return result
        
        @self.app.get("/api/dashboard/enhanced")
        async def get_enhanced_dashboard(request: Request):
            """Get enhanced dashboard data including Go service metrics"""
            timeframe = request.query_params.get("timeframe", "24h")
            
            # Get traditional Python dashboard data
            if self.db_manager:
                summary = await self.db_manager.get_summary()
                recent_evaluations = await self.db_manager.get_recent_results(limit=10)
                
                python_data = {
                    "total_evaluations": summary.total_evaluations,
                    "passed_evaluations": summary.passed_evaluations,
                    "failed_evaluations": summary.failed_evaluations,
                    "error_evaluations": summary.error_evaluations,
                    "average_score": summary.average_score,
                    "average_execution_time": summary.average_execution_time,
                    "success_rate": summary.success_rate,
                    "models_tested": summary.models_tested,
                    "test_types": summary.test_types,
                    "recent_evaluations": [
                        {
                            "id": result.id,
                            "timestamp": result.timestamp.isoformat(),
                            "model_provider": result.model_provider,
                            "model_name": result.model_name,
                            "test_type": result.test_type,
                            "score": result.score,
                            "passed": result.passed,
                            "execution_time": result.execution_time
                        }
                        for result in recent_evaluations
                    ]
                }
            else:
                python_data = {"error": "Database not available"}
            
            # Get Go service data
            go_service_data = await self.go_service_integration.get_consolidated_metrics(timeframe)
            
            # Combine data
            enhanced_data = {
                "timestamp": datetime.now().isoformat(),
                "timeframe": timeframe,
                "python_dashboard": python_data,
                "go_service": go_service_data,
                "integrated_summary": self._create_integrated_summary(python_data, go_service_data)
            }
            
            return enhanced_data

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
    
    async def broadcast_update(self, message: Dict[str, Any]):
        """Broadcast update to all connected WebSocket clients"""
        if self.active_connections:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected:
                self.active_connections.remove(connection)
    
    def _create_integrated_summary(self, python_data: Dict[str, Any], go_service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create integrated summary from Python and Go service data"""
        integrated = {
            "timestamp": datetime.now().isoformat(),
            "sources": {
                "python_dashboard": python_data.get("error") is None,
                "go_service": go_service_data.get("go_service_available", False)
            }
        }
        
        # Combine metrics if both sources are available
        if integrated["sources"]["python_dashboard"] and integrated["sources"]["go_service"]:
            python_summary = python_data
            go_summary = go_service_data.get("summary", {})
            
            integrated.update({
                "total_evaluations": python_summary.get("total_evaluations", 0) + go_summary.get("total_evaluations", 0),
                "success_rate": (python_summary.get("success_rate", 0) + go_summary.get("avg_success_rate", 0)) / 2,
                "average_score": (python_summary.get("average_score", 0) + go_summary.get("avg_score", 0)) / 2,
                "models_tested": max(python_summary.get("models_tested", 0), go_summary.get("models_tested", 0)),
                "system_status": go_summary.get("system_status", "unknown"),
                "active_connections": go_summary.get("active_connections", 0),
                "data_sources": ["python", "go_service"]
            })
        elif integrated["sources"]["python_dashboard"]:
            integrated.update({
                "total_evaluations": python_data.get("total_evaluations", 0),
                "success_rate": python_data.get("success_rate", 0),
                "average_score": python_data.get("average_score", 0),
                "models_tested": python_data.get("models_tested", 0),
                "system_status": "python_only",
                "active_connections": 0,
                "data_sources": ["python"]
            })
        elif integrated["sources"]["go_service"]:
            go_summary = go_service_data.get("summary", {})
            integrated.update({
                "total_evaluations": go_summary.get("total_evaluations", 0),
                "success_rate": go_summary.get("avg_success_rate", 0),
                "average_score": go_summary.get("avg_score", 0),
                "models_tested": go_summary.get("models_tested", 0),
                "system_status": go_summary.get("system_status", "unknown"),
                "active_connections": go_summary.get("active_connections", 0),
                "data_sources": ["go_service"]
            })
        else:
            integrated.update({
                "total_evaluations": 0,
                "success_rate": 0,
                "average_score": 0,
                "models_tested": 0,
                "system_status": "unavailable",
                "active_connections": 0,
                "data_sources": [],
                "error": "No data sources available"
            })
        
        return integrated
    
    async def start_server(self, host: str = "localhost", port: int = 8080):
        """Start the dashboard server"""
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run(self, host: str = "localhost", port: int = 8080, reload: bool = False):
        """Run the dashboard server (blocking)"""
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            reload=reload
        )