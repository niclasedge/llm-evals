# Benchmarks Module
from .dataset_manager import DatasetManager

# Import other modules conditionally to avoid circular imports
try:
    from .benchmark_runner import BenchmarkRunner
    BENCHMARK_RUNNER_AVAILABLE = True
except ImportError:
    BENCHMARK_RUNNER_AVAILABLE = False

__all__ = [
    'DatasetManager'
]

if BENCHMARK_RUNNER_AVAILABLE:
    __all__.append('BenchmarkRunner')