"""
Timing utilities for performance measurement.
"""

import time
import statistics
from contextlib import contextmanager
from typing import Dict, List, Callable, Any, Optional
import functools
import json


class Timer:
    """High-precision timer for performance measurements."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.measurements: List[float] = []
    
    def start(self) -> None:
        """Start timing."""
        self.start_time = time.perf_counter()
    
    def stop(self) -> float:
        """Stop timing and return elapsed time."""
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        self.end_time = time.perf_counter()
        elapsed = self.end_time - self.start_time
        self.measurements.append(elapsed)
        return elapsed
    
    def elapsed(self) -> float:
        """Get elapsed time without stopping timer."""
        if self.start_time is None:
            raise ValueError("Timer not started")
        return time.perf_counter() - self.start_time
    
    def reset(self) -> None:
        """Reset timer."""
        self.start_time = None
        self.end_time = None
    
    def get_statistics(self) -> Dict[str, float]:
        """Get statistical analysis of measurements."""
        if not self.measurements:
            return {}
        
        return {
            'mean': statistics.mean(self.measurements),
            'median': statistics.median(self.measurements),
            'min': min(self.measurements),
            'max': max(self.measurements),
            'std_dev': statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0.0,
            'count': len(self.measurements)
        }


@contextmanager
def measure_execution_time():
    """Context manager for measuring execution time."""
    timer = Timer()
    timer.start()
    try:
        yield timer
    finally:
        timer.stop()


def benchmark_function(func: Callable, *args, runs: int = 5, warmup: int = 1, **kwargs) -> Dict[str, Any]:
    """
    Benchmark a function with multiple runs and statistical analysis.
    
    Args:
        func: Function to benchmark
        *args: Function arguments
        runs: Number of measurement runs
        warmup: Number of warmup runs (not measured)
        **kwargs: Function keyword arguments
    
    Returns:
        Dictionary with timing statistics and metadata
    """
    timer = Timer()
    
    # Warmup runs
    for _ in range(warmup):
        func(*args, **kwargs)
    
    # Measurement runs
    for _ in range(runs):
        timer.start()
        result = func(*args, **kwargs)
        timer.stop()
    
    stats = timer.get_statistics()
    
    return {
        'function_name': func.__name__,
        'runs': runs,
        'warmup_runs': warmup,
        'timing_stats': stats,
        'measurements': timer.measurements,
        'args_info': {
            'args_count': len(args),
            'kwargs_count': len(kwargs)
        }
    }


class BenchmarkSuite:
    """Collection of benchmark results for analysis."""
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def add_result(self, name: str, result: Dict[str, Any]) -> None:
        """Add benchmark result."""
        self.results[name] = result
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmark results."""
        if not self.results:
            return {}
        
        summary = {
            'total_benchmarks': len(self.results),
            'benchmarks': {}
        }
        
        for name, result in self.results.items():
            if 'timing_stats' in result:
                summary['benchmarks'][name] = {
                    'mean_time': result['timing_stats']['mean'],
                    'runs': result.get('runs', 0)
                }
        
        return summary
    
    def save_results(self, filepath: str) -> None:
        """Save benchmark results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def load_results(self, filepath: str) -> None:
        """Load benchmark results from JSON file."""
        with open(filepath, 'r') as f:
            self.results = json.load(f)


def compare_benchmark_results(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two benchmark results and calculate performance differences.
    
    Args:
        baseline: Baseline benchmark results
        current: Current benchmark results
    
    Returns:
        Comparison analysis with performance changes
    """
    comparison = {
        'baseline': baseline.get('timing_stats', {}),
        'current': current.get('timing_stats', {}),
        'changes': {}
    }
    
    baseline_stats = baseline.get('timing_stats', {})
    current_stats = current.get('timing_stats', {})
    
    if baseline_stats and current_stats:
        # Calculate percentage changes
        for metric in ['mean', 'median', 'min', 'max']:
            if metric in baseline_stats and metric in current_stats:
                baseline_val = baseline_stats[metric]
                current_val = current_stats[metric]
                
                if baseline_val > 0:
                    change_pct = ((current_val - baseline_val) / baseline_val) * 100
                    comparison['changes'][metric] = {
                        'absolute_change': current_val - baseline_val,
                        'percentage_change': change_pct,
                        'improvement': change_pct < 0  # Negative change is improvement for timing
                    }
    
    return comparison