"""
Statistical Metrics Framework for LLM Evaluation System
Provides advanced statistical validation and analysis for evaluation metrics
"""

try:
    import numpy as np
    import scipy.stats as stats
    HAS_SCIPY = True
except ImportError:
    import math
    HAS_SCIPY = False
    # Create mock numpy and scipy for basic functionality
    class MockStats:
        @staticmethod
        def norm():
            class MockNorm:
                @staticmethod
                def ppf(p):
                    # Simplified normal distribution inverse CDF
                    if p == 0.975:
                        return 1.96
                    elif p == 0.95:
                        return 1.645
                    else:
                        return 1.96  # Default fallback
            return MockNorm()
        
        @staticmethod
        def t():
            class MockT:
                @staticmethod
                def ppf(p, df):
                    # Simplified t-distribution inverse CDF
                    if df > 30:
                        return MockStats.norm().ppf(p)
                    else:
                        return 2.0  # Conservative estimate
            return MockT()
        
        @staticmethod
        def ttest_ind(a, b, equal_var=False):
            # Simplified two-sample t-test
            mean_a = sum(a) / len(a) if a else 0
            mean_b = sum(b) / len(b) if b else 0
            return mean_a - mean_b, 0.5  # Return simple difference and neutral p-value
        
        @staticmethod
        def ttest_1samp(a, popmean):
            # Simplified one-sample t-test
            if not a:
                return 0.0, 1.0
            mean_a = sum(a) / len(a)
            return mean_a - popmean, 0.5
        
        @staticmethod
        def skew(a):
            if not a:
                return 0.0
            mean_a = sum(a) / len(a)
            return 0.0  # Simplified
        
        @staticmethod
        def kurtosis(a):
            return 0.0  # Simplified
        
        @staticmethod
        def shapiro(a):
            return 1.0, 0.5  # Simplified
        
        @staticmethod
        def zscore(a):
            if not a:
                return []
            mean_a = sum(a) / len(a)
            std_a = (sum((x - mean_a)**2 for x in a) / len(a))**0.5
            if std_a == 0:
                return [0.0] * len(a)
            return [(x - mean_a) / std_a for x in a]
    
    stats = MockStats()
    
    class MockNumpy:
        @staticmethod
        def array(a):
            return a
        
        @staticmethod
        def mean(a):
            return sum(a) / len(a) if a else 0
        
        @staticmethod
        def std(a, ddof=0):
            if not a or len(a) <= ddof:
                return 0.0
            mean_a = sum(a) / len(a)
            variance = sum((x - mean_a)**2 for x in a) / (len(a) - ddof)
            return variance**0.5
        
        @staticmethod
        def var(a, ddof=0):
            if not a or len(a) <= ddof:
                return 0.0
            mean_a = sum(a) / len(a)
            return sum((x - mean_a)**2 for x in a) / (len(a) - ddof)
        
        @staticmethod
        def median(a):
            if not a:
                return 0
            sorted_a = sorted(a)
            n = len(sorted_a)
            if n % 2 == 0:
                return (sorted_a[n//2 - 1] + sorted_a[n//2]) / 2
            else:
                return sorted_a[n//2]
        
        @staticmethod
        def min(a):
            return min(a) if a else 0
        
        @staticmethod
        def max(a):
            return max(a) if a else 0
        
        @staticmethod
        def percentile(a, p):
            if not a:
                return 0
            sorted_a = sorted(a)
            k = (len(sorted_a) - 1) * p / 100
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_a[int(k)]
            d0 = sorted_a[int(f)] * (c - k)
            d1 = sorted_a[int(c)] * (k - f)
            return d0 + d1
        
        @staticmethod
        def sqrt(x):
            return math.sqrt(x)
        
        random = type('MockRandom', (), {
            'choice': lambda a, size=None, replace=True: [a[0]] * (size or 1) if a else []
        })()
    
    np = MockNumpy()

from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from .base_metric import BaseMetric, MetricResult, MetricConfig


@dataclass 
class StatisticalResult:
    """Result of statistical analysis"""
    mean: float
    std_dev: float
    confidence_interval: Tuple[float, float]
    confidence_level: float
    sample_size: int
    p_value: Optional[float] = None
    test_statistic: Optional[float] = None
    effect_size: Optional[float] = None
    is_significant: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StatisticalConfig:
    """Configuration for statistical analysis"""
    confidence_level: float = 0.95
    min_sample_size: int = 30
    multiple_runs_count: int = 5
    significance_threshold: float = 0.05
    bootstrap_samples: int = 1000
    enable_effect_size: bool = True
    enable_power_analysis: bool = True
    
    def __post_init__(self):
        if not 0 < self.confidence_level < 1:
            raise ValueError("confidence_level must be between 0 and 1")
        if self.min_sample_size < 1:
            raise ValueError("min_sample_size must be positive")


class StatisticalAnalyzer:
    """Provides statistical analysis capabilities for evaluation metrics"""
    
    def __init__(self, config: Optional[StatisticalConfig] = None):
        self.config = config or StatisticalConfig()
    
    def calculate_confidence_interval(self, data: List[float], 
                                    confidence_level: Optional[float] = None) -> Tuple[float, float]:
        """Calculate confidence interval for a sample"""
        if not data:
            return (0.0, 0.0)
        
        conf_level = confidence_level or self.config.confidence_level
        data_array = np.array(data)
        
        if len(data) < 2:
            return (data_array.mean(), data_array.mean())
        
        # Use t-distribution for small samples, normal for large samples
        if len(data) < 30:
            # t-distribution
            t_critical = stats.t.ppf((1 + conf_level) / 2, df=len(data) - 1)
            margin_error = t_critical * (data_array.std(ddof=1) / np.sqrt(len(data)))
        else:
            # Normal distribution
            z_critical = stats.norm.ppf((1 + conf_level) / 2)
            margin_error = z_critical * (data_array.std(ddof=1) / np.sqrt(len(data)))
        
        mean = data_array.mean()
        return (mean - margin_error, mean + margin_error)
    
    def bootstrap_confidence_interval(self, data: List[float], 
                                    statistic_func: callable = np.mean,
                                    confidence_level: Optional[float] = None) -> Tuple[float, float]:
        """Calculate bootstrap confidence interval"""
        if not data:
            return (0.0, 0.0)
        
        conf_level = confidence_level or self.config.confidence_level
        data_array = np.array(data)
        
        # Bootstrap resampling
        bootstrap_stats = []
        for _ in range(self.config.bootstrap_samples):
            sample = np.random.choice(data_array, size=len(data_array), replace=True)
            bootstrap_stats.append(statistic_func(sample))
        
        # Calculate percentiles
        alpha = 1 - conf_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower_bound = np.percentile(bootstrap_stats, lower_percentile)
        upper_bound = np.percentile(bootstrap_stats, upper_percentile)
        
        return (float(lower_bound), float(upper_bound))
    
    def perform_t_test(self, sample1: List[float], sample2: List[float]) -> Dict[str, Any]:
        """Perform two-sample t-test"""
        if len(sample1) < 2 or len(sample2) < 2:
            return {
                'p_value': 1.0,
                'test_statistic': 0.0,
                'is_significant': False,
                'effect_size': 0.0,
                'degrees_of_freedom': 0
            }
        
        # Perform Welch's t-test (assumes unequal variances)
        statistic, p_value = stats.ttest_ind(sample1, sample2, equal_var=False)
        
        # Calculate Cohen's d (effect size)
        pooled_std = np.sqrt((np.var(sample1, ddof=1) + np.var(sample2, ddof=1)) / 2)
        cohens_d = (np.mean(sample1) - np.mean(sample2)) / pooled_std if pooled_std > 0 else 0.0
        
        # Degrees of freedom for Welch's t-test
        n1, n2 = len(sample1), len(sample2)
        s1, s2 = np.var(sample1, ddof=1), np.var(sample2, ddof=1)
        df = (s1/n1 + s2/n2)**2 / ((s1/n1)**2/(n1-1) + (s2/n2)**2/(n2-1))
        
        return {
            'p_value': float(p_value),
            'test_statistic': float(statistic),
            'is_significant': p_value < self.config.significance_threshold,
            'effect_size': float(cohens_d),
            'degrees_of_freedom': int(df)
        }
    
    def perform_one_sample_t_test(self, sample: List[float], 
                                 population_mean: float) -> Dict[str, Any]:
        """Perform one-sample t-test"""
        if len(sample) < 2:
            return {
                'p_value': 1.0,
                'test_statistic': 0.0,
                'is_significant': False,
                'effect_size': 0.0
            }
        
        statistic, p_value = stats.ttest_1samp(sample, population_mean)
        
        # Calculate Cohen's d
        cohens_d = (np.mean(sample) - population_mean) / np.std(sample, ddof=1)
        
        return {
            'p_value': float(p_value),
            'test_statistic': float(statistic),
            'is_significant': p_value < self.config.significance_threshold,
            'effect_size': float(cohens_d)
        }
    
    def calculate_power_analysis(self, effect_size: float, sample_size: int, 
                               alpha: Optional[float] = None) -> float:
        """Calculate statistical power for given effect size and sample size"""
        alpha = alpha or self.config.significance_threshold
        
        # For two-sample t-test
        try:
            from scipy.stats import ttest_power
            power = ttest_power(effect_size, sample_size, alpha)
            return float(power)
        except ImportError:
            # Fallback calculation
            z_alpha = stats.norm.ppf(1 - alpha / 2)
            z_beta = stats.norm.cdf(effect_size * np.sqrt(sample_size / 2) - z_alpha)
            return float(z_beta)
    
    def analyze_distribution(self, data: List[float]) -> Dict[str, Any]:
        """Analyze the distribution of data"""
        if not data:
            return {'error': 'No data provided'}
        
        data_array = np.array(data)
        
        # Basic statistics
        stats_dict = {
            'mean': float(data_array.mean()),
            'median': float(np.median(data_array)),
            'std_dev': float(data_array.std(ddof=1)),
            'variance': float(data_array.var(ddof=1)),
            'min': float(data_array.min()),
            'max': float(data_array.max()),
            'range': float(data_array.max() - data_array.min()),
            'skewness': float(stats.skew(data_array)),
            'kurtosis': float(stats.kurtosis(data_array)),
            'sample_size': len(data)
        }
        
        # Percentiles
        percentiles = [25, 50, 75, 90, 95, 99]
        stats_dict['percentiles'] = {
            f'p{p}': float(np.percentile(data_array, p)) for p in percentiles
        }
        
        # Normality test
        if len(data) >= 8:  # Minimum sample size for Shapiro-Wilk
            shapiro_stat, shapiro_p = stats.shapiro(data_array)
            stats_dict['normality_test'] = {
                'statistic': float(shapiro_stat),
                'p_value': float(shapiro_p),
                'is_normal': shapiro_p > 0.05
            }
        
        return stats_dict
    
    def detect_outliers(self, data: List[float], method: str = 'iqr') -> Dict[str, Any]:
        """Detect outliers in data using various methods"""
        if not data:
            return {'outliers': [], 'outlier_indices': []}
        
        data_array = np.array(data)
        outlier_indices = []
        
        if method == 'iqr':
            # Interquartile range method
            q1 = np.percentile(data_array, 25)
            q3 = np.percentile(data_array, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outlier_indices = np.where((data_array < lower_bound) | (data_array > upper_bound))[0]
        
        elif method == 'zscore':
            # Z-score method
            z_scores = np.abs(stats.zscore(data_array))
            outlier_indices = np.where(z_scores > 3)[0]
        
        elif method == 'modified_zscore':
            # Modified Z-score method
            median = np.median(data_array)
            mad = np.median(np.abs(data_array - median))
            modified_z_scores = 0.6745 * (data_array - median) / mad
            outlier_indices = np.where(np.abs(modified_z_scores) > 3.5)[0]
        
        outliers = data_array[outlier_indices].tolist()
        
        return {
            'outliers': outliers,
            'outlier_indices': outlier_indices.tolist(),
            'outlier_count': len(outliers),
            'outlier_percentage': (len(outliers) / len(data)) * 100,
            'method': method
        }
    
    def create_statistical_result(self, data: List[float], 
                                reference_data: Optional[List[float]] = None,
                                reference_mean: Optional[float] = None) -> StatisticalResult:
        """Create comprehensive statistical result"""
        if not data:
            return StatisticalResult(
                mean=0.0,
                std_dev=0.0,
                confidence_interval=(0.0, 0.0),
                confidence_level=self.config.confidence_level,
                sample_size=0
            )
        
        data_array = np.array(data)
        mean = float(data_array.mean())
        std_dev = float(data_array.std(ddof=1)) if len(data) > 1 else 0.0
        
        # Calculate confidence interval
        ci = self.calculate_confidence_interval(data)
        
        # Statistical testing
        p_value = None
        test_statistic = None
        effect_size = None
        is_significant = False
        
        if reference_data is not None:
            # Two-sample test
            test_results = self.perform_t_test(data, reference_data)
            p_value = test_results['p_value']
            test_statistic = test_results['test_statistic']
            effect_size = test_results['effect_size']
            is_significant = test_results['is_significant']
        elif reference_mean is not None:
            # One-sample test
            test_results = self.perform_one_sample_t_test(data, reference_mean)
            p_value = test_results['p_value']
            test_statistic = test_results['test_statistic']
            effect_size = test_results['effect_size']
            is_significant = test_results['is_significant']
        
        # Additional analysis
        distribution_analysis = self.analyze_distribution(data)
        outlier_analysis = self.detect_outliers(data)
        
        metadata = {
            'distribution_analysis': distribution_analysis,
            'outlier_analysis': outlier_analysis,
            'statistical_config': {
                'confidence_level': self.config.confidence_level,
                'significance_threshold': self.config.significance_threshold,
                'bootstrap_samples': self.config.bootstrap_samples
            }
        }
        
        return StatisticalResult(
            mean=mean,
            std_dev=std_dev,
            confidence_interval=ci,
            confidence_level=self.config.confidence_level,
            sample_size=len(data),
            p_value=p_value,
            test_statistic=test_statistic,
            effect_size=effect_size,
            is_significant=is_significant,
            metadata=metadata
        )


class StatisticalMetric(BaseMetric):
    """Base metric class with statistical validation capabilities"""
    
    def __init__(self, config: Optional[MetricConfig] = None, 
                 statistical_config: Optional[StatisticalConfig] = None):
        super().__init__(config)
        self.statistical_config = statistical_config or StatisticalConfig()
        self.analyzer = StatisticalAnalyzer(self.statistical_config)
        self._evaluation_history: List[float] = []
    
    def add_evaluation_result(self, score: float):
        """Add evaluation result to history for statistical analysis"""
        self._evaluation_history.append(score)
    
    def get_evaluation_history(self) -> List[float]:
        """Get evaluation history"""
        return self._evaluation_history.copy()
    
    def clear_evaluation_history(self):
        """Clear evaluation history"""
        self._evaluation_history.clear()
    
    def get_statistical_analysis(self) -> Optional[StatisticalResult]:
        """Get statistical analysis of evaluation history"""
        if not self._evaluation_history:
            return None
        
        return self.analyzer.create_statistical_result(self._evaluation_history)
    
    def create_statistical_result(self, score: float, details: Dict[str, Any], 
                                error_message: Optional[str] = None) -> MetricResult:
        """Create MetricResult with statistical validation"""
        # Add score to history
        self.add_evaluation_result(score)
        
        # Create base result
        result = self.create_result(score, details, error_message)
        
        # Add statistical analysis if we have enough data
        if len(self._evaluation_history) >= self.statistical_config.min_sample_size:
            stat_analysis = self.get_statistical_analysis()
            if stat_analysis:
                result.metadata['statistical_analysis'] = {
                    'mean': stat_analysis.mean,
                    'std_dev': stat_analysis.std_dev,
                    'confidence_interval': stat_analysis.confidence_interval,
                    'confidence_level': stat_analysis.confidence_level,
                    'sample_size': stat_analysis.sample_size,
                    'is_statistically_stable': stat_analysis.std_dev < 0.1  # Configurable threshold
                }
        
        return result
    
    async def evaluate_multiple_runs(self, query: str, response: str, 
                                   ground_truth: Optional[str] = None) -> MetricResult:
        """Evaluate multiple times for statistical validation"""
        scores = []
        all_details = []
        
        # Run multiple evaluations
        for i in range(self.statistical_config.multiple_runs_count):
            try:
                result = await self.evaluate(query, response, ground_truth)
                scores.append(result.score)
                all_details.append(result.details)
            except Exception as e:
                # Handle evaluation errors
                scores.append(0.0)
                all_details.append({'error': str(e), 'run': i})
        
        # Statistical analysis
        stat_result = self.analyzer.create_statistical_result(scores)
        
        # Create comprehensive result
        mean_score = stat_result.mean
        details = {
            'multiple_runs': {
                'scores': scores,
                'mean': mean_score,
                'std_dev': stat_result.std_dev,
                'confidence_interval': stat_result.confidence_interval,
                'confidence_level': stat_result.confidence_level,
                'run_count': len(scores),
                'all_run_details': all_details
            },
            'statistical_analysis': stat_result.metadata
        }
        
        return self.create_result(mean_score, details)
    
    def compare_with_baseline(self, baseline_scores: List[float]) -> Dict[str, Any]:
        """Compare current metric performance with baseline"""
        if not self._evaluation_history or not baseline_scores:
            return {'error': 'Insufficient data for comparison'}
        
        # Perform statistical comparison
        comparison_result = self.analyzer.perform_t_test(
            self._evaluation_history, baseline_scores
        )
        
        # Calculate improvement metrics
        current_mean = np.mean(self._evaluation_history)
        baseline_mean = np.mean(baseline_scores)
        improvement = ((current_mean - baseline_mean) / baseline_mean) * 100
        
        return {
            'current_performance': {
                'mean': current_mean,
                'std_dev': np.std(self._evaluation_history, ddof=1),
                'sample_size': len(self._evaluation_history)
            },
            'baseline_performance': {
                'mean': baseline_mean,
                'std_dev': np.std(baseline_scores, ddof=1),
                'sample_size': len(baseline_scores)
            },
            'comparison': {
                'improvement_percentage': improvement,
                'is_significant': comparison_result['is_significant'],
                'p_value': comparison_result['p_value'],
                'effect_size': comparison_result['effect_size'],
                'confidence_level': self.statistical_config.confidence_level
            }
        }
    
    def is_statistically_reliable(self) -> bool:
        """Check if the metric has sufficient statistical reliability"""
        if len(self._evaluation_history) < self.statistical_config.min_sample_size:
            return False
        
        stat_analysis = self.get_statistical_analysis()
        if not stat_analysis:
            return False
        
        # Check coefficient of variation (CV)
        cv = stat_analysis.std_dev / stat_analysis.mean if stat_analysis.mean != 0 else float('inf')
        
        # Consider reliable if CV < 0.2 (configurable threshold)
        return cv < 0.2
    
    def get_requirements(self) -> List[str]:
        """Get requirements for statistical metrics"""
        base_requirements = super().get_requirements() if hasattr(super(), 'get_requirements') else []
        statistical_requirements = [
            'numpy>=1.20.0',
            'scipy>=1.7.0'
        ]
        return base_requirements + statistical_requirements