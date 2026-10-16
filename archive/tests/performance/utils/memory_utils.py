"""
Memory profiling utilities for performance testing.
"""

import gc
import tracemalloc
import os
from typing import Dict, List, Any, Optional, Callable
from contextlib import contextmanager
import json

# Optional system monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available, using basic memory monitoring")


class MemoryProfiler:
    """Memory profiling and leak detection utility."""
    
    def __init__(self):
        self.measurements: List[Dict[str, Any]] = []
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
        self.baseline_memory: Optional[float] = None
    
    def start_profiling(self) -> None:
        """Start memory profiling."""
        tracemalloc.start()
        self.baseline_memory = self.get_memory_usage()
    
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return memory statistics."""
        if not tracemalloc.is_tracing():
            raise ValueError("Memory profiling not started")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        final_memory = self.get_memory_usage()
        
        stats = {
            'current_traced_mb': current / 1024 / 1024,
            'peak_traced_mb': peak / 1024 / 1024,
            'baseline_memory_mb': self.baseline_memory,
            'final_memory_mb': final_memory,
            'memory_delta_mb': final_memory - (self.baseline_memory or 0),
            'process_memory_info': self.get_process_memory_info()
        }
        
        self.measurements.append(stats)
        return stats
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        if not PSUTIL_AVAILABLE or self.process is None:
            return 0.0  # Return 0 if psutil not available
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_process_memory_info(self) -> Dict[str, float]:
        """Get detailed process memory information."""
        if not PSUTIL_AVAILABLE or self.process is None:
            return {
                'rss_mb': 0.0,
                'vms_mb': 0.0,
                'memory_percent': 0.0,
                'num_threads': 1
            }
        
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'memory_percent': memory_percent,
            'num_threads': self.process.num_threads()
        }
    
    def check_memory_leak(self, threshold_mb: float = 10.0) -> Dict[str, Any]:
        """
        Check for potential memory leaks.
        
        Args:
            threshold_mb: Memory increase threshold in MB to consider a leak
        
        Returns:
            Leak detection results
        """
        if not self.measurements:
            return {'leak_detected': False, 'reason': 'No measurements available'}
        
        latest = self.measurements[-1]
        memory_delta = latest.get('memory_delta_mb', 0)
        
        leak_detected = memory_delta > threshold_mb
        
        return {
            'leak_detected': leak_detected,
            'memory_delta_mb': memory_delta,
            'threshold_mb': threshold_mb,
            'baseline_mb': latest.get('baseline_memory_mb', 0),
            'final_mb': latest.get('final_memory_mb', 0),
            'peak_traced_mb': latest.get('peak_traced_mb', 0)
        }
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistical analysis of memory measurements."""
        if not self.measurements:
            return {}
        
        memory_deltas = [m.get('memory_delta_mb', 0) for m in self.measurements]
        peak_memories = [m.get('peak_traced_mb', 0) for m in self.measurements]
        
        return {
            'total_measurements': len(self.measurements),
            'average_memory_delta_mb': sum(memory_deltas) / len(memory_deltas),
            'max_memory_delta_mb': max(memory_deltas),
            'min_memory_delta_mb': min(memory_deltas),
            'average_peak_memory_mb': sum(peak_memories) / len(peak_memories),
            'max_peak_memory_mb': max(peak_memories),
            'latest_measurement': self.measurements[-1]
        }


@contextmanager
def track_memory_usage():
    """Context manager for tracking memory usage."""
    profiler = MemoryProfiler()
    profiler.start_profiling()
    try:
        yield profiler
    finally:
        stats = profiler.stop_profiling()


def check_memory_leaks(func: Callable, *args, runs: int = 5, threshold_mb: float = 10.0, **kwargs) -> Dict[str, Any]:
    """
    Check function for memory leaks by running it multiple times.
    
    Args:
        func: Function to test
        *args: Function arguments
        runs: Number of test runs
        threshold_mb: Memory increase threshold to consider a leak
        **kwargs: Function keyword arguments
    
    Returns:
        Memory leak analysis results
    """
    profiler = MemoryProfiler()
    
    # Run multiple times to detect accumulating leaks
    for i in range(runs):
        profiler.start_profiling()
        
        # Force garbage collection before each run
        gc.collect()
        
        # Run the function
        func(*args, **kwargs)
        
        # Force garbage collection after each run
        gc.collect()
        
        profiler.stop_profiling()
    
    # Analyze for leaks
    leak_analysis = profiler.check_memory_leak(threshold_mb)
    memory_stats = profiler.get_memory_statistics()
    
    return {
        'function_name': func.__name__,
        'runs': runs,
        'leak_analysis': leak_analysis,
        'memory_statistics': memory_stats,
        'all_measurements': profiler.measurements
    }


def profile_memory_usage(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Profile memory usage of a single function execution.
    
    Args:
        func: Function to profile
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        Memory profiling results
    """
    with track_memory_usage() as profiler:
        result = func(*args, **kwargs)
        
    final_stats = profiler.stop_profiling()
    
    return {
        'function_name': func.__name__,
        'memory_stats': final_stats,
        'function_result': str(type(result))  # Don't store actual result to avoid memory issues
    }


class MemoryBenchmarkSuite:
    """Collection of memory benchmark results."""
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def add_result(self, name: str, result: Dict[str, Any]) -> None:
        """Add memory benchmark result."""
        self.results[name] = result
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of memory benchmark results."""
        if not self.results:
            return {}
        
        summary = {
            'total_benchmarks': len(self.results),
            'memory_leaks_detected': 0,
            'benchmarks': {}
        }
        
        for name, result in self.results.items():
            leak_detected = False
            peak_memory = 0
            
            if 'leak_analysis' in result:
                leak_detected = result['leak_analysis'].get('leak_detected', False)
                if leak_detected:
                    summary['memory_leaks_detected'] += 1
            
            if 'memory_statistics' in result:
                peak_memory = result['memory_statistics'].get('max_peak_memory_mb', 0)
            elif 'memory_stats' in result:
                peak_memory = result['memory_stats'].get('peak_traced_mb', 0)
            
            summary['benchmarks'][name] = {
                'leak_detected': leak_detected,
                'peak_memory_mb': peak_memory
            }
        
        return summary
    
    def save_results(self, filepath: str) -> None:
        """Save memory benchmark results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def load_results(self, filepath: str) -> None:
        """Load memory benchmark results from JSON file."""
        with open(filepath, 'r') as f:
            self.results = json.load(f)