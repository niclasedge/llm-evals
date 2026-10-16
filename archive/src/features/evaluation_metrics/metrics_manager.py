"""
Metrics Manager for LLM Evaluation System
Manages and orchestrates all evaluation metrics
"""

import asyncio
from typing import Dict, Any, Optional, List, Type
from .base_metric import BaseMetric, MetricResult, MetricConfig, CompositeMetric
from .statistical_metrics import StatisticalMetric, StatisticalAnalyzer, StatisticalConfig
from .relevance_metric import RelevanceMetric
from .accuracy_metric import AccuracyMetric
from .coherence_metric import CoherenceMetric
from .similarity_metric import SimilarityMetric
from .bias_metric import BiasMetric
from .toxicity_metric import ToxicityMetric


class MetricsManager:
    """Manages and orchestrates all evaluation metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, BaseMetric] = {}
        self.metric_configs: Dict[str, MetricConfig] = {}
        self.statistical_analyzer = StatisticalAnalyzer()
        self.evaluation_history: Dict[str, List[float]] = {}
        self._initialize_default_metrics()
    
    def _initialize_default_metrics(self):
        """Initialize default metrics"""
        default_metrics = {
            'relevance': RelevanceMetric,
            'accuracy': AccuracyMetric,
            'coherence': CoherenceMetric,
            'similarity': SimilarityMetric,
            'bias': BiasMetric,
            'toxicity': ToxicityMetric
        }
        
        for name, metric_class in default_metrics.items():
            self.register_metric(name, metric_class)
    
    def register_metric(self, name: str, metric_class: Type[BaseMetric], config: Optional[MetricConfig] = None):
        """Register a new metric"""
        if config is None:
            config = MetricConfig()
        
        self.metric_configs[name] = config
        self.metrics[name] = metric_class(config)
    
    def unregister_metric(self, name: str):
        """Unregister a metric"""
        if name in self.metrics:
            del self.metrics[name]
        if name in self.metric_configs:
            del self.metric_configs[name]
    
    def get_metric(self, name: str) -> Optional[BaseMetric]:
        """Get a metric by name"""
        return self.metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, BaseMetric]:
        """Get all registered metrics"""
        return self.metrics.copy()
    
    def get_enabled_metrics(self) -> Dict[str, BaseMetric]:
        """Get all enabled metrics"""
        return {name: metric for name, metric in self.metrics.items() if metric.is_enabled()}
    
    def configure_metric(self, name: str, config: MetricConfig):
        """Configure a metric"""
        if name in self.metrics:
            self.metric_configs[name] = config
            # Recreate metric with new config
            metric_class = type(self.metrics[name])
            self.metrics[name] = metric_class(config)
    
    def enable_metric(self, name: str):
        """Enable a metric"""
        if name in self.metric_configs:
            self.metric_configs[name].enabled = True
            self.configure_metric(name, self.metric_configs[name])
    
    def disable_metric(self, name: str):
        """Disable a metric"""
        if name in self.metric_configs:
            self.metric_configs[name].enabled = False
            self.configure_metric(name, self.metric_configs[name])
    
    async def evaluate_single(self, metric_name: str, query: str, response: str, 
                             ground_truth: Optional[str] = None) -> Optional[MetricResult]:
        """Evaluate using a single metric"""
        metric = self.get_metric(metric_name)
        if not metric or not metric.is_enabled():
            return None
        
        try:
            return await metric.evaluate(query, response, ground_truth)
        except Exception as e:
            return metric.create_result(
                score=0.0,
                details={'error': str(e)},
                error_message=f"Metric evaluation failed: {str(e)}"
            )
    
    async def evaluate_all(self, query: str, response: str, 
                          ground_truth: Optional[str] = None,
                          metric_names: Optional[List[str]] = None) -> Dict[str, MetricResult]:
        """Evaluate using all enabled metrics or specified metrics"""
        if metric_names is None:
            metrics_to_use = self.get_enabled_metrics()
        else:
            metrics_to_use = {name: self.metrics[name] for name in metric_names 
                            if name in self.metrics and self.metrics[name].is_enabled()}
        
        results = {}
        
        # Run evaluations concurrently
        tasks = []
        for name, metric in metrics_to_use.items():
            tasks.append(self._evaluate_metric_safe(name, metric, query, response, ground_truth))
        
        if tasks:
            evaluation_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (name, _) in enumerate(metrics_to_use.items()):
                result = evaluation_results[i]
                if isinstance(result, Exception):
                    # Handle exception
                    error_result = MetricResult(
                        score=0.0,
                        passed=False,
                        details={'error': str(result)},
                        error_message=f"Metric evaluation failed: {str(result)}"
                    )
                    results[name] = error_result
                else:
                    results[name] = result
        
        return results
    
    async def _evaluate_metric_safe(self, name: str, metric: BaseMetric, query: str, 
                                   response: str, ground_truth: Optional[str] = None) -> MetricResult:
        """Safely evaluate a metric with error handling"""
        try:
            return await metric.evaluate(query, response, ground_truth)
        except Exception as e:
            return metric.create_result(
                score=0.0,
                details={'error': str(e)},
                error_message=f"Metric {name} evaluation failed: {str(e)}"
            )
    
    def calculate_composite_score(self, results: Dict[str, MetricResult], 
                                 weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate composite score from multiple metric results"""
        if not results:
            return 0.0
        
        if weights is None:
            # Use equal weights
            weights = {name: 1.0 / len(results) for name in results.keys()}
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for name, result in results.items():
            if name in weights and not result.error_message:
                weight = weights[name]
                total_weighted_score += result.score * weight
                total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0.0
    
    def create_composite_metric(self, name: str, metric_names: List[str], 
                               config: Optional[MetricConfig] = None) -> CompositeMetric:
        """Create a composite metric from existing metrics"""
        sub_metrics = []
        for metric_name in metric_names:
            if metric_name in self.metrics:
                sub_metrics.append(self.metrics[metric_name])
        
        composite = CompositeMetric(sub_metrics, config)
        composite._name = name
        composite._description = f"Composite metric combining: {', '.join(metric_names)}"
        
        return composite
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            'total_metrics': len(self.metrics),
            'enabled_metrics': len(self.get_enabled_metrics()),
            'disabled_metrics': len(self.metrics) - len(self.get_enabled_metrics()),
            'metrics_details': {}
        }
        
        for name, metric in self.metrics.items():
            summary['metrics_details'][name] = {
                'name': metric.name,
                'type': metric.metric_type.value,
                'description': metric.description,
                'version': metric.version,
                'enabled': metric.is_enabled(),
                'threshold': metric.get_threshold(),
                'weight': metric.get_weight(),
                'requirements': metric.get_requirements()
            }
        
        return summary
    
    def validate_metrics_configuration(self) -> Dict[str, List[str]]:
        """Validate metrics configuration"""
        validation_results = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # Check for enabled metrics
        enabled_metrics = self.get_enabled_metrics()
        if not enabled_metrics:
            validation_results['errors'].append("No metrics are enabled")
        
        # Check metric requirements
        for name, metric in enabled_metrics.items():
            requirements = metric.get_requirements()
            if requirements:
                validation_results['info'].append(f"Metric {name} requires: {', '.join(requirements)}")
        
        # Check for metrics that require ground truth
        ground_truth_metrics = ['similarity']
        enabled_gt_metrics = [name for name in ground_truth_metrics if name in enabled_metrics]
        if enabled_gt_metrics:
            validation_results['warnings'].append(
                f"Metrics {', '.join(enabled_gt_metrics)} require ground truth for evaluation"
            )
        
        # Check threshold values
        for name, metric in enabled_metrics.items():
            threshold = metric.get_threshold()
            if not 0 <= threshold <= 1:
                validation_results['errors'].append(f"Metric {name} has invalid threshold: {threshold}")
        
        return validation_results
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current metrics configuration"""
        config_export = {
            'metrics': {}
        }
        
        for name, config in self.metric_configs.items():
            config_export['metrics'][name] = {
                'threshold': config.threshold,
                'weight': config.weight,
                'enabled': config.enabled,
                'parameters': config.parameters
            }
        
        return config_export
    
    def import_configuration(self, config_data: Dict[str, Any]):
        """Import metrics configuration"""
        if 'metrics' in config_data:
            for name, config_dict in config_data['metrics'].items():
                if name in self.metrics:
                    config = MetricConfig(
                        threshold=config_dict.get('threshold', 0.5),
                        weight=config_dict.get('weight', 1.0),
                        enabled=config_dict.get('enabled', True),
                        parameters=config_dict.get('parameters', {})
                    )
                    self.configure_metric(name, config)
    
    async def benchmark_metrics(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Benchmark all enabled metrics"""
        benchmark_results = {}
        enabled_metrics = self.get_enabled_metrics()
        
        for name, metric in enabled_metrics.items():
            metric_results = []
            
            for test_case in test_data:
                query = test_case['query']
                response = test_case['response']
                ground_truth = test_case.get('ground_truth')
                
                result = await self.evaluate_single(name, query, response, ground_truth)
                if result:
                    metric_results.append({
                        'score': result.score,
                        'passed': result.passed,
                        'error': result.error_message is not None
                    })
            
            if metric_results:
                avg_score = sum(r['score'] for r in metric_results) / len(metric_results)
                pass_rate = sum(1 for r in metric_results if r['passed']) / len(metric_results)
                error_rate = sum(1 for r in metric_results if r['error']) / len(metric_results)
                
                benchmark_results[name] = {
                    'average_score': avg_score,
                    'pass_rate': pass_rate,
                    'error_rate': error_rate,
                    'total_evaluations': len(metric_results)
                }
        
        return benchmark_results
    
    def get_metric_dependencies(self) -> Dict[str, List[str]]:
        """Get dependencies for all metrics"""
        dependencies = {}
        
        for name, metric in self.metrics.items():
            requirements = metric.get_requirements()
            if requirements:
                dependencies[name] = requirements
        
        return dependencies
    
    async def evaluate_with_statistical_validation(self, query: str, response: str,
                                           ground_truth: Optional[str] = None,
                                           metric_names: Optional[List[str]] = None,
                                           num_runs: int = 5) -> Dict[str, Any]:
        """Evaluate with statistical validation across multiple runs"""
        results = {}
        
        if metric_names is None:
            metrics_to_use = self.get_enabled_metrics()
        else:
            metrics_to_use = {name: self.metrics[name] for name in metric_names 
                            if name in self.metrics and self.metrics[name].is_enabled()}
        
        for metric_name, metric in metrics_to_use.items():
            # Run multiple evaluations
            scores = []
            detailed_results = []
            
            for i in range(num_runs):
                try:
                    result = await metric.evaluate(query, response, ground_truth)
                    scores.append(result.score)
                    detailed_results.append(result)
                except Exception as e:
                    scores.append(0.0)
                    detailed_results.append(
                        metric.create_result(0.0, {'error': str(e)}, f"Run {i} failed: {str(e)}")
                    )
            
            # Statistical analysis
            if metric_name not in self.evaluation_history:
                self.evaluation_history[metric_name] = []
            
            self.evaluation_history[metric_name].extend(scores)
            
            stat_result = self.statistical_analyzer.create_statistical_result(scores)
            
            results[metric_name] = {
                'mean_score': stat_result.mean,
                'std_dev': stat_result.std_dev,
                'confidence_interval': stat_result.confidence_interval,
                'confidence_level': stat_result.confidence_level,
                'sample_size': stat_result.sample_size,
                'is_statistically_reliable': len(self.evaluation_history[metric_name]) >= 30,
                'individual_results': detailed_results,
                'statistical_metadata': stat_result.metadata
            }
        
        return results
    
    def get_statistical_summary(self) -> Dict[str, Any]:
        """Get statistical summary of all metrics"""
        summary = {}
        
        for metric_name, history in self.evaluation_history.items():
            if history:
                stat_result = self.statistical_analyzer.create_statistical_result(history)
                summary[metric_name] = {
                    'total_evaluations': len(history),
                    'mean_performance': stat_result.mean,
                    'std_dev': stat_result.std_dev,
                    'confidence_interval': stat_result.confidence_interval,
                    'is_stable': stat_result.std_dev < 0.1,
                    'distribution_analysis': stat_result.metadata.get('distribution_analysis', {})
                }
        
        return summary
    
    def compare_metric_performance(self, metric_name1: str, metric_name2: str) -> Dict[str, Any]:
        """Compare performance between two metrics"""
        if metric_name1 not in self.evaluation_history or metric_name2 not in self.evaluation_history:
            return {'error': 'Insufficient data for comparison'}
        
        history1 = self.evaluation_history[metric_name1]
        history2 = self.evaluation_history[metric_name2]
        
        if not history1 or not history2:
            return {'error': 'Insufficient data for comparison'}
        
        # Perform statistical comparison
        comparison_result = self.statistical_analyzer.perform_t_test(history1, history2)
        
        return {
            'metric1': {
                'name': metric_name1,
                'mean': sum(history1) / len(history1),
                'sample_size': len(history1)
            },
            'metric2': {
                'name': metric_name2,
                'mean': sum(history2) / len(history2),
                'sample_size': len(history2)
            },
            'comparison': comparison_result
        }
    
    def detect_performance_regression(self, metric_name: str, baseline_threshold: float) -> Dict[str, Any]:
        """Detect if metric performance has regressed"""
        if metric_name not in self.evaluation_history:
            return {'error': 'No evaluation history found'}
        
        history = self.evaluation_history[metric_name]
        
        if len(history) < 10:
            return {'warning': 'Insufficient data for regression detection'}
        
        # Compare recent performance with baseline
        recent_scores = history[-10:]  # Last 10 evaluations
        
        # Perform one-sample t-test against baseline
        test_result = self.statistical_analyzer.perform_one_sample_t_test(
            recent_scores, baseline_threshold
        )
        
        recent_mean = sum(recent_scores) / len(recent_scores)
        
        return {
            'metric_name': metric_name,
            'baseline_threshold': baseline_threshold,
            'recent_mean': recent_mean,
            'regression_detected': recent_mean < baseline_threshold and test_result['is_significant'],
            'statistical_test': test_result,
            'recommendation': 'investigate' if recent_mean < baseline_threshold else 'continue'
        }
    
    def clear_evaluation_history(self, metric_name: Optional[str] = None):
        """Clear evaluation history"""
        if metric_name:
            if metric_name in self.evaluation_history:
                self.evaluation_history[metric_name].clear()
        else:
            self.evaluation_history.clear()
    
    def export_statistical_report(self) -> str:
        """Export comprehensive statistical report"""
        import json
        from datetime import datetime
        
        summary = self.get_statistical_summary()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_metrics': len(self.metrics),
            'metrics_with_history': len(self.evaluation_history),
            'statistical_summary': summary,
            'recommendations': []
        }
        
        # Add recommendations
        for metric_name, stats in summary.items():
            if stats['total_evaluations'] < 30:
                report['recommendations'].append(
                    f"Metric {metric_name} needs more evaluations for statistical reliability"
                )
            
            if not stats['is_stable']:
                report['recommendations'].append(
                    f"Metric {metric_name} shows high variability (std_dev: {stats['std_dev']:.3f})"
                )
        
        return json.dumps(report, indent=2)