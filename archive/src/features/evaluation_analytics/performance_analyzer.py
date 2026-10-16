"""
Performance Analyzer for LLM Evaluation System
Comprehensive analysis of model performance across various dimensions
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    overall_score: float
    category_scores: Dict[str, float]
    difficulty_scores: Dict[str, float]
    trend_analysis: Dict[str, Any]
    comparative_analysis: Dict[str, Any]
    reliability_metrics: Dict[str, float]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EvaluationResult:
    """Single evaluation result for analysis"""
    id: str
    model_name: str
    test_category: str
    difficulty: str
    score: float
    timestamp: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PerformanceAnalyzer:
    """Analyzes model performance across multiple dimensions"""
    
    def __init__(self):
        self.evaluation_results: List[EvaluationResult] = []
        self.analysis_cache: Dict[str, Any] = {}
        self.benchmark_data: Dict[str, float] = {}
    
    def add_evaluation_result(self, result: EvaluationResult):
        """Add a single evaluation result"""
        self.evaluation_results.append(result)
        # Clear cache when new data is added
        self.analysis_cache.clear()
    
    def add_evaluation_results(self, results: List[EvaluationResult]):
        """Add multiple evaluation results"""
        self.evaluation_results.extend(results)
        self.analysis_cache.clear()
    
    def set_benchmark_data(self, benchmarks: Dict[str, float]):
        """Set benchmark scores for comparison"""
        self.benchmark_data = benchmarks
    
    def analyze_overall_performance(self, model_name: Optional[str] = None) -> PerformanceMetrics:
        """Analyze overall performance for a model or all models"""
        cache_key = f"overall_{model_name or 'all'}"
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        # Filter results if model_name specified
        if model_name:
            results = [r for r in self.evaluation_results if r.model_name == model_name]
        else:
            results = self.evaluation_results
        
        if not results:
            return PerformanceMetrics(
                overall_score=0.0,
                category_scores={},
                difficulty_scores={},
                trend_analysis={},
                comparative_analysis={},
                reliability_metrics={}
            )
        
        # Calculate overall score
        overall_score = sum(r.score for r in results) / len(results)
        
        # Calculate category scores
        category_scores = self._calculate_category_scores(results)
        
        # Calculate difficulty scores
        difficulty_scores = self._calculate_difficulty_scores(results)
        
        # Perform trend analysis
        trend_analysis = self._analyze_trends(results)
        
        # Perform comparative analysis
        comparative_analysis = self._perform_comparative_analysis(results, model_name)
        
        # Calculate reliability metrics
        reliability_metrics = self._calculate_reliability_metrics(results)
        
        metrics = PerformanceMetrics(
            overall_score=overall_score,
            category_scores=category_scores,
            difficulty_scores=difficulty_scores,
            trend_analysis=trend_analysis,
            comparative_analysis=comparative_analysis,
            reliability_metrics=reliability_metrics,
            metadata={
                'total_evaluations': len(results),
                'analysis_timestamp': datetime.now().isoformat(),
                'model_name': model_name
            }
        )
        
        self.analysis_cache[cache_key] = metrics
        return metrics
    
    def _calculate_category_scores(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate average scores by category"""
        category_scores = defaultdict(list)
        
        for result in results:
            category_scores[result.test_category].append(result.score)
        
        return {
            category: sum(scores) / len(scores)
            for category, scores in category_scores.items()
        }
    
    def _calculate_difficulty_scores(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate average scores by difficulty level"""
        difficulty_scores = defaultdict(list)
        
        for result in results:
            difficulty_scores[result.difficulty].append(result.score)
        
        return {
            difficulty: sum(scores) / len(scores)
            for difficulty, scores in difficulty_scores.items()
        }
    
    def _analyze_trends(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if len(results) < 2:
            return {'trend': 'insufficient_data'}
        
        # Sort by timestamp
        sorted_results = sorted(results, key=lambda r: r.timestamp)
        
        # Calculate moving averages
        window_size = min(10, len(sorted_results) // 3)
        if window_size < 2:
            window_size = 2
        
        moving_averages = []
        for i in range(window_size, len(sorted_results) + 1):
            window_scores = [r.score for r in sorted_results[i-window_size:i]]
            avg_score = sum(window_scores) / len(window_scores)
            moving_averages.append(avg_score)
        
        # Determine trend direction
        if len(moving_averages) >= 2:
            recent_avg = sum(moving_averages[-3:]) / len(moving_averages[-3:])
            early_avg = sum(moving_averages[:3]) / len(moving_averages[:3])
            
            if recent_avg > early_avg * 1.05:
                trend_direction = 'improving'
            elif recent_avg < early_avg * 0.95:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'
        else:
            trend_direction = 'unknown'
        
        # Calculate volatility
        if len(moving_averages) > 1:
            volatility = self._calculate_volatility(moving_averages)
        else:
            volatility = 0.0
        
        return {
            'trend_direction': trend_direction,
            'volatility': volatility,
            'moving_averages': moving_averages,
            'recent_performance': moving_averages[-1] if moving_averages else 0.0,
            'best_performance': max(moving_averages) if moving_averages else 0.0,
            'worst_performance': min(moving_averages) if moving_averages else 0.0
        }
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation) of values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _perform_comparative_analysis(self, results: List[EvaluationResult], 
                                    model_name: Optional[str]) -> Dict[str, Any]:
        """Perform comparative analysis against benchmarks and other models"""
        comparative_analysis = {}
        
        # Compare against benchmarks
        if self.benchmark_data:
            avg_score = sum(r.score for r in results) / len(results) if results else 0.0
            
            benchmark_comparisons = {}
            for benchmark_name, benchmark_score in self.benchmark_data.items():
                if avg_score > benchmark_score:
                    status = 'above'
                    difference = avg_score - benchmark_score
                elif avg_score < benchmark_score:
                    status = 'below'
                    difference = benchmark_score - avg_score
                else:
                    status = 'equal'
                    difference = 0.0
                
                benchmark_comparisons[benchmark_name] = {
                    'status': status,
                    'difference': difference,
                    'percentage_difference': (difference / benchmark_score) * 100 if benchmark_score > 0 else 0.0
                }
            
            comparative_analysis['benchmark_comparison'] = benchmark_comparisons
        
        # Compare against other models
        if model_name:
            other_models_results = [r for r in self.evaluation_results if r.model_name != model_name]
            if other_models_results:
                other_models_avg = sum(r.score for r in other_models_results) / len(other_models_results)
                current_model_avg = sum(r.score for r in results) / len(results) if results else 0.0
                
                comparative_analysis['other_models_comparison'] = {
                    'current_model_score': current_model_avg,
                    'other_models_average': other_models_avg,
                    'relative_performance': 'better' if current_model_avg > other_models_avg else 'worse' if current_model_avg < other_models_avg else 'equal'
                }
        
        return comparative_analysis
    
    def _calculate_reliability_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate reliability and consistency metrics"""
        if not results:
            return {}
        
        scores = [r.score for r in results]
        
        # Calculate coefficient of variation
        mean_score = sum(scores) / len(scores)
        if mean_score > 0:
            std_dev = (sum((s - mean_score) ** 2 for s in scores) / len(scores)) ** 0.5
            coefficient_of_variation = std_dev / mean_score
        else:
            coefficient_of_variation = 0.0
        
        # Calculate consistency score (inverse of CV)
        consistency_score = max(0.0, 1.0 - coefficient_of_variation)
        
        # Calculate score range
        score_range = max(scores) - min(scores) if scores else 0.0
        
        # Calculate reliability score (based on consistency and sample size)
        sample_size_factor = min(1.0, len(results) / 30.0)  # More reliable with more samples
        reliability_score = consistency_score * sample_size_factor
        
        return {
            'consistency_score': consistency_score,
            'coefficient_of_variation': coefficient_of_variation,
            'score_range': score_range,
            'reliability_score': reliability_score,
            'sample_size': len(results)
        }
    
    def analyze_performance_by_dimension(self, dimension: str, 
                                       model_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze performance broken down by a specific dimension"""
        # Filter results
        if model_name:
            results = [r for r in self.evaluation_results if r.model_name == model_name]
        else:
            results = self.evaluation_results
        
        if not results:
            return {'error': 'No results found'}
        
        # Group by dimension
        dimension_groups = defaultdict(list)
        
        for result in results:
            if dimension == 'category':
                key = result.test_category
            elif dimension == 'difficulty':
                key = result.difficulty
            elif dimension == 'model':
                key = result.model_name
            else:
                # Try to get from metadata
                key = result.metadata.get(dimension, 'unknown')
            
            dimension_groups[key].append(result)
        
        # Analyze each group
        dimension_analysis = {}
        
        for group_name, group_results in dimension_groups.items():
            scores = [r.score for r in group_results]
            
            group_analysis = {
                'count': len(group_results),
                'average_score': sum(scores) / len(scores),
                'min_score': min(scores),
                'max_score': max(scores),
                'score_range': max(scores) - min(scores),
                'std_deviation': (sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores)) ** 0.5
            }
            
            dimension_analysis[group_name] = group_analysis
        
        # Calculate dimension insights
        if len(dimension_analysis) > 1:
            best_group = max(dimension_analysis.items(), key=lambda x: x[1]['average_score'])
            worst_group = min(dimension_analysis.items(), key=lambda x: x[1]['average_score'])
            
            insights = {
                'best_performing_group': {
                    'name': best_group[0],
                    'score': best_group[1]['average_score']
                },
                'worst_performing_group': {
                    'name': worst_group[0],
                    'score': worst_group[1]['average_score']
                },
                'performance_gap': best_group[1]['average_score'] - worst_group[1]['average_score']
            }
        else:
            insights = {}
        
        return {
            'dimension': dimension,
            'groups': dimension_analysis,
            'insights': insights,
            'total_groups': len(dimension_analysis)
        }
    
    def generate_performance_report(self, model_name: Optional[str] = None) -> str:
        """Generate comprehensive performance report"""
        overall_metrics = self.analyze_overall_performance(model_name)
        category_analysis = self.analyze_performance_by_dimension('category', model_name)
        difficulty_analysis = self.analyze_performance_by_dimension('difficulty', model_name)
        
        report = []
        
        # Header
        report.append("=" * 80)
        report.append(f"PERFORMANCE ANALYSIS REPORT")
        if model_name:
            report.append(f"Model: {model_name}")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append()
        
        # Overall Performance
        report.append("OVERALL PERFORMANCE")
        report.append("-" * 40)
        report.append(f"Overall Score: {overall_metrics.overall_score:.3f}")
        report.append(f"Total Evaluations: {overall_metrics.metadata.get('total_evaluations', 0)}")
        report.append(f"Reliability Score: {overall_metrics.reliability_metrics.get('reliability_score', 0):.3f}")
        report.append(f"Consistency Score: {overall_metrics.reliability_metrics.get('consistency_score', 0):.3f}")
        report.append()
        
        # Trend Analysis
        trend = overall_metrics.trend_analysis
        report.append("TREND ANALYSIS")
        report.append("-" * 40)
        report.append(f"Trend Direction: {trend.get('trend_direction', 'unknown')}")
        report.append(f"Volatility: {trend.get('volatility', 0):.3f}")
        report.append(f"Recent Performance: {trend.get('recent_performance', 0):.3f}")
        report.append(f"Best Performance: {trend.get('best_performance', 0):.3f}")
        report.append()
        
        # Category Performance
        report.append("PERFORMANCE BY CATEGORY")
        report.append("-" * 40)
        for category, score in overall_metrics.category_scores.items():
            report.append(f"{category:20}: {score:.3f}")
        report.append()
        
        # Difficulty Performance
        report.append("PERFORMANCE BY DIFFICULTY")
        report.append("-" * 40)
        for difficulty, score in overall_metrics.difficulty_scores.items():
            report.append(f"{difficulty:20}: {score:.3f}")
        report.append()
        
        # Comparative Analysis
        if overall_metrics.comparative_analysis:
            report.append("COMPARATIVE ANALYSIS")
            report.append("-" * 40)
            
            if 'benchmark_comparison' in overall_metrics.comparative_analysis:
                report.append("Benchmark Comparisons:")
                for benchmark, comparison in overall_metrics.comparative_analysis['benchmark_comparison'].items():
                    status = comparison['status']
                    diff = comparison['difference']
                    report.append(f"  {benchmark}: {status} by {diff:.3f}")
                report.append()
            
            if 'other_models_comparison' in overall_metrics.comparative_analysis:
                comp = overall_metrics.comparative_analysis['other_models_comparison']
                report.append(f"Compared to other models: {comp['relative_performance']}")
                report.append()
        
        # Insights and Recommendations
        report.append("INSIGHTS AND RECOMMENDATIONS")
        report.append("-" * 40)
        
        insights = self._generate_insights(overall_metrics, category_analysis, difficulty_analysis)
        for insight in insights:
            report.append(f"• {insight}")
        
        return "\n".join(report)
    
    def _generate_insights(self, overall_metrics: PerformanceMetrics,
                          category_analysis: Dict[str, Any],
                          difficulty_analysis: Dict[str, Any]) -> List[str]:
        """Generate insights and recommendations"""
        insights = []
        
        # Overall performance insights
        if overall_metrics.overall_score > 0.8:
            insights.append("Strong overall performance across evaluations")
        elif overall_metrics.overall_score < 0.5:
            insights.append("Performance below expectations, requires investigation")
        
        # Reliability insights
        reliability = overall_metrics.reliability_metrics.get('reliability_score', 0)
        if reliability > 0.8:
            insights.append("High reliability and consistency in performance")
        elif reliability < 0.5:
            insights.append("Low reliability, results may be inconsistent")
        
        # Trend insights
        trend_direction = overall_metrics.trend_analysis.get('trend_direction')
        if trend_direction == 'improving':
            insights.append("Performance is improving over time")
        elif trend_direction == 'declining':
            insights.append("Performance is declining - requires attention")
        
        # Category insights
        if 'insights' in category_analysis and category_analysis['insights']:
            best_cat = category_analysis['insights'].get('best_performing_group', {})
            worst_cat = category_analysis['insights'].get('worst_performing_group', {})
            
            if best_cat and worst_cat:
                gap = category_analysis['insights'].get('performance_gap', 0)
                if gap > 0.2:
                    insights.append(f"Large performance gap between {best_cat['name']} and {worst_cat['name']} categories")
                    insights.append(f"Focus improvement efforts on {worst_cat['name']} category")
        
        # Difficulty insights
        if 'insights' in difficulty_analysis and difficulty_analysis['insights']:
            best_diff = difficulty_analysis['insights'].get('best_performing_group', {})
            worst_diff = difficulty_analysis['insights'].get('worst_performing_group', {})
            
            if best_diff and worst_diff:
                if best_diff['name'] == 'easy' and worst_diff['name'] in ['hard', 'expert']:
                    insights.append("Performance decreases appropriately with difficulty")
                elif best_diff['name'] in ['hard', 'expert']:
                    insights.append("Surprisingly strong performance on difficult tasks")
        
        # Sample size insights
        total_evals = overall_metrics.metadata.get('total_evaluations', 0)
        if total_evals < 10:
            insights.append("Small sample size - results may not be representative")
        elif total_evals > 100:
            insights.append("Large sample size provides confident results")
        
        return insights
    
    def export_analysis(self, filename: Optional[str] = None) -> str:
        """Export complete analysis to file"""
        analysis_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_results': len(self.evaluation_results),
            'models_analyzed': list(set(r.model_name for r in self.evaluation_results)),
            'overall_analysis': {},
            'model_specific_analysis': {}
        }
        
        # Overall analysis
        overall_metrics = self.analyze_overall_performance()
        analysis_data['overall_analysis'] = asdict(overall_metrics)
        
        # Model-specific analysis
        unique_models = set(r.model_name for r in self.evaluation_results)
        for model_name in unique_models:
            model_metrics = self.analyze_overall_performance(model_name)
            analysis_data['model_specific_analysis'][model_name] = asdict(model_metrics)
        
        # Export to file
        if filename:
            filepath = filename
        else:
            filepath = f"performance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        logger.info(f"Exported analysis to {filepath}")
        return filepath
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for all evaluation data"""
        if not self.evaluation_results:
            return {'error': 'No evaluation results available'}
        
        # Basic statistics
        scores = [r.score for r in self.evaluation_results]
        models = [r.model_name for r in self.evaluation_results]
        categories = [r.test_category for r in self.evaluation_results]
        difficulties = [r.difficulty for r in self.evaluation_results]
        
        return {
            'total_evaluations': len(self.evaluation_results),
            'unique_models': len(set(models)),
            'unique_categories': len(set(categories)),
            'unique_difficulties': len(set(difficulties)),
            'score_statistics': {
                'mean': sum(scores) / len(scores),
                'min': min(scores),
                'max': max(scores),
                'range': max(scores) - min(scores)
            },
            'model_distribution': dict(Counter(models)),
            'category_distribution': dict(Counter(categories)),
            'difficulty_distribution': dict(Counter(difficulties)),
            'date_range': {
                'earliest': min(r.timestamp for r in self.evaluation_results),
                'latest': max(r.timestamp for r in self.evaluation_results)
            }
        }