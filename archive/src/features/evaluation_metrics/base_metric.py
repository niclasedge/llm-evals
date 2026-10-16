"""
Base Metric Class for LLM Evaluation System
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import asyncio


class MetricType(Enum):
    """Types of evaluation metrics"""
    RELEVANCE = "relevance"
    ACCURACY = "accuracy"
    COHERENCE = "coherence"
    SIMILARITY = "similarity"
    BIAS = "bias"
    TOXICITY = "toxicity"
    CUSTOM = "custom"


@dataclass
class MetricResult:
    """Result of a metric evaluation"""
    score: float
    passed: bool
    details: Dict[str, Any]
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    confidence_interval: Optional[tuple] = None
    confidence_level: Optional[float] = None
    statistical_significance: Optional[bool] = None
    sample_size: Optional[int] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_statistically_reliable(self) -> bool:
        """Check if the result is statistically reliable"""
        return (self.confidence_interval is not None and 
                self.sample_size is not None and 
                self.sample_size >= 30)


@dataclass
class MetricConfig:
    """Configuration for a metric"""
    threshold: float = 0.5
    weight: float = 1.0
    enabled: bool = True
    parameters: Dict[str, Any] = None
    # Statistical validation settings
    enable_statistical_validation: bool = True
    confidence_level: float = 0.95
    min_sample_size: int = 30
    multiple_runs_count: int = 5
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        # Validate statistical settings
        if not 0 < self.confidence_level < 1:
            raise ValueError("confidence_level must be between 0 and 1")
        if self.min_sample_size < 1:
            raise ValueError("min_sample_size must be positive")


class BaseMetric(ABC):
    """Abstract base class for all evaluation metrics"""
    
    def __init__(self, config: Optional[MetricConfig] = None):
        self.config = config or MetricConfig()
        self._metric_type = MetricType.CUSTOM
        self._name = self.__class__.__name__
        self._description = "Base metric implementation"
        self._version = "1.0.0"
    
    @property
    def metric_type(self) -> MetricType:
        """Get the metric type"""
        return self._metric_type
    
    @property
    def name(self) -> str:
        """Get the metric name"""
        return self._name
    
    @property
    def description(self) -> str:
        """Get the metric description"""
        return self._description
    
    @property
    def version(self) -> str:
        """Get the metric version"""
        return self._version
    
    @abstractmethod
    async def evaluate(self, query: str, response: str, ground_truth: Optional[str] = None) -> MetricResult:
        """
        Evaluate the response against the metric
        
        Args:
            query: The original query/prompt
            response: The LLM response to evaluate
            ground_truth: Optional ground truth for comparison
            
        Returns:
            MetricResult with score, pass/fail status, and details
        """
        pass
    
    @abstractmethod
    def get_requirements(self) -> List[str]:
        """
        Get list of requirements/dependencies for this metric
        
        Returns:
            List of requirement strings
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if metric is enabled"""
        return self.config.enabled
    
    def get_threshold(self) -> float:
        """Get the threshold for pass/fail determination"""
        return self.config.threshold
    
    def get_weight(self) -> float:
        """Get the weight for this metric in overall scoring"""
        return self.config.weight
    
    def validate_inputs(self, query: str, response: str, ground_truth: Optional[str] = None) -> bool:
        """
        Validate input parameters
        
        Args:
            query: The original query/prompt
            response: The LLM response to evaluate
            ground_truth: Optional ground truth for comparison
            
        Returns:
            True if inputs are valid, False otherwise
        """
        if not isinstance(query, str) or not query.strip():
            return False
        
        if not isinstance(response, str) or not response.strip():
            return False
        
        if ground_truth is not None and not isinstance(ground_truth, str):
            return False
        
        return True
    
    def create_result(self, score: float, details: Dict[str, Any], 
                     error_message: Optional[str] = None) -> MetricResult:
        """
        Create a MetricResult with standard processing
        
        Args:
            score: The metric score (0.0 to 1.0)
            details: Additional details about the evaluation
            error_message: Optional error message
            
        Returns:
            MetricResult instance
        """
        # Clamp score to [0, 1] range
        score = max(0.0, min(1.0, score))
        
        # Determine pass/fail based on threshold
        passed = score >= self.get_threshold()
        
        # Add metadata
        metadata = {
            'metric_name': self.name,
            'metric_type': self.metric_type.value,
            'metric_version': self.version,
            'threshold': self.get_threshold(),
            'weight': self.get_weight()
        }
        
        return MetricResult(
            score=score,
            passed=passed,
            details=details,
            error_message=error_message,
            metadata=metadata
        )
    
    async def batch_evaluate(self, evaluations: List[Dict[str, Any]]) -> List[MetricResult]:
        """
        Evaluate multiple query-response pairs in batch
        
        Args:
            evaluations: List of dicts with 'query', 'response', and optional 'ground_truth'
            
        Returns:
            List of MetricResult instances
        """
        results = []
        
        for eval_data in evaluations:
            try:
                query = eval_data['query']
                response = eval_data['response']
                ground_truth = eval_data.get('ground_truth')
                
                result = await self.evaluate(query, response, ground_truth)
                results.append(result)
                
            except Exception as e:
                error_result = self.create_result(
                    score=0.0,
                    details={'error': str(e)},
                    error_message=f"Evaluation failed: {str(e)}"
                )
                results.append(error_result)
        
        return results
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get the configuration schema for this metric
        
        Returns:
            JSON schema for metric configuration
        """
        return {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5,
                    "description": "Threshold for pass/fail determination"
                },
                "weight": {
                    "type": "number",
                    "minimum": 0.0,
                    "default": 1.0,
                    "description": "Weight for this metric in overall scoring"
                },
                "enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether this metric is enabled"
                },
                "parameters": {
                    "type": "object",
                    "description": "Metric-specific parameters"
                }
            }
        }
    
    def __str__(self) -> str:
        return f"{self.name} (type: {self.metric_type.value}, threshold: {self.get_threshold()})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' enabled={self.is_enabled()}>"


class AsyncMetricMixin:
    """Mixin for metrics that need async capabilities"""
    
    async def async_operation(self, operation_name: str, *args, **kwargs):
        """Generic async operation wrapper"""
        try:
            return await self._perform_async_operation(operation_name, *args, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Async operation {operation_name} failed: {str(e)}")
    
    async def _perform_async_operation(self, operation_name: str, *args, **kwargs):
        """Override this method in subclasses for specific async operations"""
        raise NotImplementedError("Subclasses must implement _perform_async_operation")


class CacheableMetricMixin:
    """Mixin for metrics that can cache results"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}
        self._cache_enabled = True
    
    def _get_cache_key(self, query: str, response: str, ground_truth: Optional[str] = None) -> str:
        """Generate cache key for evaluation"""
        import hashlib
        content = f"{query}|{response}|{ground_truth or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[MetricResult]:
        """Get cached result if available"""
        if not self._cache_enabled:
            return None
        return self._cache.get(cache_key)
    
    def _cache_result(self, cache_key: str, result: MetricResult):
        """Cache evaluation result"""
        if self._cache_enabled:
            self._cache[cache_key] = result
    
    def clear_cache(self):
        """Clear the metric cache"""
        self._cache.clear()
    
    def disable_cache(self):
        """Disable caching"""
        self._cache_enabled = False
    
    def enable_cache(self):
        """Enable caching"""
        self._cache_enabled = True


class CompositeMetric(BaseMetric):
    """Base class for metrics that combine multiple sub-metrics"""
    
    def __init__(self, sub_metrics: List[BaseMetric], config: Optional[MetricConfig] = None):
        super().__init__(config)
        self.sub_metrics = sub_metrics
        self._name = "CompositeMetric"
        self._description = "Composite metric combining multiple sub-metrics"
    
    async def evaluate(self, query: str, response: str, ground_truth: Optional[str] = None) -> MetricResult:
        """Evaluate using all sub-metrics and combine results"""
        if not self.validate_inputs(query, response, ground_truth):
            return self.create_result(
                score=0.0,
                details={'error': 'Invalid inputs'},
                error_message="Invalid input parameters"
            )
        
        sub_results = []
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for metric in self.sub_metrics:
            if not metric.is_enabled():
                continue
                
            try:
                result = await metric.evaluate(query, response, ground_truth)
                sub_results.append({
                    'metric': metric.name,
                    'score': result.score,
                    'passed': result.passed,
                    'weight': metric.get_weight(),
                    'details': result.details
                })
                
                total_weighted_score += result.score * metric.get_weight()
                total_weight += metric.get_weight()
                
            except Exception as e:
                sub_results.append({
                    'metric': metric.name,
                    'score': 0.0,
                    'passed': False,
                    'weight': metric.get_weight(),
                    'error': str(e)
                })
        
        # Calculate composite score
        composite_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        details = {
            'composite_score': composite_score,
            'sub_metrics': sub_results,
            'total_weight': total_weight,
            'metrics_count': len(self.sub_metrics)
        }
        
        return self.create_result(composite_score, details)
    
    def get_requirements(self) -> List[str]:
        """Get requirements from all sub-metrics"""
        requirements = []
        for metric in self.sub_metrics:
            requirements.extend(metric.get_requirements())
        return list(set(requirements))  # Remove duplicates