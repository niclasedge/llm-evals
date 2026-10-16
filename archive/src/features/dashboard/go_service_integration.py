"""
Integration module for Go service monitoring and analytics dashboard.
Provides interface between Python dashboard and Go service metrics.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp
from dataclasses import dataclass
from pathlib import Path

from ...core.config_manager import get_config

logger = logging.getLogger(__name__)

@dataclass
class GoServiceMetrics:
    """Data class for Go service metrics"""
    timestamp: datetime
    total_requests: int
    success_rate: float
    average_response_time: float
    throughput_rps: float
    error_rate: float
    active_connections: int
    models_tested: int


@dataclass
class ModelPerformanceMetrics:
    """Data class for model performance metrics"""
    model_name: str
    model_provider: str
    total_evaluations: int
    success_rate: float
    avg_score: float
    avg_response_time: float
    error_count: int
    last_evaluation: datetime


class GoServiceClient:
    """Client for interacting with Go service monitoring endpoints"""
    
    def __init__(self, go_service_url: str = None):
        self.go_service_url = go_service_url or self._get_default_go_service_url()
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        
    def _get_default_go_service_url(self) -> str:
        """Get default Go service URL from configuration"""
        config = get_config()
        return config.get('go_service', {}).get('url', 'http://localhost:8080')
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Go service health"""
        try:
            async with self.session.get(f"{self.go_service_url}/health") as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Go service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary from Go service"""
        try:
            async with self.session.get(f"{self.go_service_url}/api/metrics/summary") as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    async def get_performance_metrics(self, timeframe: str = "24h") -> Dict[str, Any]:
        """Get performance metrics for specified timeframe"""
        try:
            params = {"timeframe": timeframe}
            async with self.session.get(f"{self.go_service_url}/api/metrics/performance", params=params) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    async def get_system_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system analytics"""
        try:
            async with self.session.get(f"{self.go_service_url}/api/analytics/performance") as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get system analytics: {e}")
            return {}
    
    async def get_model_comparison(self, models: List[str] = None) -> Dict[str, Any]:
        """Get comparative performance data for models"""
        try:
            params = {}
            if models:
                params["models"] = ",".join(models)
            async with self.session.get(f"{self.go_service_url}/api/analytics/models/comparison", params=params) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get model comparison: {e}")
            return {}
    
    async def get_model_performance(self, model_name: str, model_provider: str, timeframe: str = "24h") -> Dict[str, Any]:
        """Get performance metrics for specific model"""
        try:
            params = {
                "model_name": model_name,
                "model_provider": model_provider,
                "timeframe": timeframe
            }
            async with self.session.get(f"{self.go_service_url}/api/metrics/models", params=params) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get model performance: {e}")
            return {}
    
    async def get_dashboard_data(self, timeframe: str = "24h") -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            params = {"timeframe": timeframe}
            async with self.session.get(f"{self.go_service_url}/dashboard/api/data", params=params) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {}
    
    async def trigger_load_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a load test with given configuration"""
        try:
            async with self.session.post(f"{self.go_service_url}/api/loadtest", json=config) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to trigger load test: {e}")
            return {"error": str(e)}
    
    async def get_load_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get results of a load test"""
        try:
            async with self.session.get(f"{self.go_service_url}/api/loadtest/{test_id}") as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get load test results: {e}")
            return {"error": str(e)}


class GoServiceIntegration:
    """Integration layer for Go service monitoring in Python dashboard"""
    
    def __init__(self, go_service_url: str = None):
        self.go_service_url = go_service_url
        self.client = GoServiceClient(go_service_url)
        self.cache = {}
        self.cache_timeout = 30  # seconds
    
    async def is_available(self) -> bool:
        """Check if Go service is available"""
        try:
            async with self.client as client:
                health = await client.health_check()
                return health.get("status") == "healthy"
        except Exception:
            return False
    
    async def get_consolidated_metrics(self, timeframe: str = "24h") -> Dict[str, Any]:
        """Get consolidated metrics from Go service"""
        cache_key = f"consolidated_metrics_{timeframe}"
        
        # Check cache
        if self._is_cached(cache_key):
            return self.cache[cache_key]["data"]
        
        try:
            async with self.client as client:
                # Get multiple data sources concurrently
                tasks = [
                    client.get_metrics_summary(),
                    client.get_performance_metrics(timeframe),
                    client.get_system_analytics(),
                    client.get_dashboard_data(timeframe)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                metrics_summary = results[0] if not isinstance(results[0], Exception) else {}
                performance_metrics = results[1] if not isinstance(results[1], Exception) else {}
                system_analytics = results[2] if not isinstance(results[2], Exception) else {}
                dashboard_data = results[3] if not isinstance(results[3], Exception) else {}
                
                # Consolidate data
                consolidated = {
                    "timestamp": datetime.now().isoformat(),
                    "timeframe": timeframe,
                    "go_service_available": True,
                    "metrics_summary": metrics_summary,
                    "performance_metrics": performance_metrics,
                    "system_analytics": system_analytics,
                    "dashboard_data": dashboard_data,
                    "models": self._extract_model_data(system_analytics),
                    "summary": self._create_summary(metrics_summary, system_analytics)
                }
                
                # Cache the result
                self._cache_data(cache_key, consolidated)
                
                return consolidated
                
        except Exception as e:
            logger.error(f"Failed to get consolidated metrics: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "timeframe": timeframe,
                "go_service_available": False,
                "error": str(e),
                "metrics_summary": {},
                "performance_metrics": {},
                "system_analytics": {},
                "dashboard_data": {},
                "models": [],
                "summary": {}
            }
    
    async def get_model_performance_trends(self, model_name: str, model_provider: str, timeframe: str = "24h") -> List[Dict[str, Any]]:
        """Get performance trends for specific model"""
        cache_key = f"model_trends_{model_name}_{model_provider}_{timeframe}"
        
        if self._is_cached(cache_key):
            return self.cache[cache_key]["data"]
        
        try:
            async with self.client as client:
                data = await client.get_model_performance(model_name, model_provider, timeframe)
                trends = data.get("metrics", [])
                
                self._cache_data(cache_key, trends)
                return trends
                
        except Exception as e:
            logger.error(f"Failed to get model performance trends: {e}")
            return []
    
    async def run_performance_benchmark(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a performance benchmark using Go service"""
        try:
            async with self.client as client:
                # Configure load test
                load_test_config = {
                    "concurrent_users": config.get("concurrent_users", 10),
                    "test_duration": config.get("test_duration", "60s"),
                    "request_rate": config.get("request_rate", 10),
                    "models": config.get("models", ["test-model"]),
                    "test_scenarios": config.get("scenarios", ["basic"]),
                    "target_endpoint": config.get("endpoint", "/api/evaluate")
                }
                
                # Trigger load test
                result = await client.trigger_load_test(load_test_config)
                
                if "error" in result:
                    return {"success": False, "error": result["error"]}
                
                # For now, return immediate results
                # In a real implementation, you might poll for results
                return {
                    "success": True,
                    "test_id": result.get("test_id", "unknown"),
                    "config": load_test_config,
                    "status": "completed",
                    "results": result
                }
                
        except Exception as e:
            logger.error(f"Failed to run performance benchmark: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_model_data(self, system_analytics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract model data from system analytics"""
        model_comparison = system_analytics.get("model_comparison", [])
        
        models = []
        for model_data in model_comparison:
            models.append({
                "name": model_data.get("model_name", "unknown"),
                "provider": model_data.get("model_provider", "unknown"),
                "evaluations": model_data.get("total_evaluations", 0),
                "success_rate": model_data.get("success_rate", 0.0),
                "avg_score": model_data.get("avg_score", 0.0),
                "avg_response_time": model_data.get("avg_response_time", 0.0),
                "error_count": model_data.get("error_count", 0),
                "last_evaluation": model_data.get("last_evaluation", "")
            })
        
        return models
    
    def _create_summary(self, metrics_summary: Dict[str, Any], system_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Create a consolidated summary"""
        system_health = system_analytics.get("system_health", {})
        model_comparison = system_analytics.get("model_comparison", [])
        
        total_evaluations = system_health.get("total_requests", 0)
        models_tested = len(model_comparison)
        
        # Calculate average success rate
        avg_success_rate = 0.0
        if model_comparison:
            total_success = sum(model.get("success_rate", 0) for model in model_comparison)
            avg_success_rate = total_success / len(model_comparison)
        
        # Calculate average score
        avg_score = 0.0
        if model_comparison:
            total_score = sum(model.get("avg_score", 0) for model in model_comparison)
            avg_score = total_score / len(model_comparison)
        
        return {
            "total_evaluations": total_evaluations,
            "models_tested": models_tested,
            "avg_success_rate": avg_success_rate,
            "avg_score": avg_score,
            "system_status": system_health.get("status", "unknown"),
            "uptime": system_health.get("uptime", 0),
            "active_connections": system_health.get("active_connections", 0)
        }
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and not expired"""
        if key not in self.cache:
            return False
        
        cached_time = self.cache[key]["timestamp"]
        return (datetime.now() - cached_time).total_seconds() < self.cache_timeout
    
    def _cache_data(self, key: str, data: Any):
        """Cache data with timestamp"""
        self.cache[key] = {
            "data": data,
            "timestamp": datetime.now()
        }
        
        # Clean old cache entries
        self._clean_cache()
    
    def _clean_cache(self):
        """Remove expired cache entries"""
        current_time = datetime.now()
        expired_keys = [
            key for key, value in self.cache.items()
            if (current_time - value["timestamp"]).total_seconds() > self.cache_timeout
        ]
        
        for key in expired_keys:
            del self.cache[key]


# Utility functions for dashboard integration
async def get_go_service_metrics(timeframe: str = "24h") -> Dict[str, Any]:
    """Convenience function to get Go service metrics"""
    integration = GoServiceIntegration()
    return await integration.get_consolidated_metrics(timeframe)


async def check_go_service_availability() -> bool:
    """Check if Go service is available"""
    integration = GoServiceIntegration()
    return await integration.is_available()


async def run_go_service_benchmark(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run a performance benchmark using Go service"""
    integration = GoServiceIntegration()
    return await integration.run_performance_benchmark(config)


def create_go_service_dashboard_config() -> Dict[str, Any]:
    """Create dashboard configuration for Go service integration"""
    return {
        "go_service_integration": {
            "enabled": True,
            "url": "http://localhost:8080",
            "cache_timeout": 30,
            "endpoints": {
                "health": "/health",
                "metrics": "/api/metrics/summary",
                "performance": "/api/metrics/performance",
                "analytics": "/api/analytics/performance",
                "dashboard": "/dashboard/api/data",
                "load_test": "/api/loadtest"
            }
        },
        "dashboard_sections": {
            "go_service_metrics": {
                "title": "Go Service Performance",
                "priority": 1,
                "components": [
                    "metrics_summary",
                    "performance_charts",
                    "model_comparison",
                    "system_health"
                ]
            },
            "load_testing": {
                "title": "Load Testing",
                "priority": 2,
                "components": [
                    "load_test_config",
                    "benchmark_results",
                    "performance_trends"
                ]
            }
        }
    }


# Export main classes and functions
__all__ = [
    "GoServiceClient",
    "GoServiceIntegration",
    "GoServiceMetrics",
    "ModelPerformanceMetrics",
    "get_go_service_metrics",
    "check_go_service_availability",
    "run_go_service_benchmark",
    "create_go_service_dashboard_config"
]