"""
Evaluation execution time performance tests.
"""

import asyncio
import json
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.performance.utils import benchmark_function, Timer, BenchmarkSuite as TimingBenchmarkSuite
from src.features.llm_evaluation.main_evaluator import LLMEvaluator
from src.features.coding_evaluation.evaluator import CodingEvaluator
from src.features.unified_evaluation.service import UnifiedEvaluationService


class ExecutionPerformanceTester:
    """Test execution performance of evaluation components."""
    
    def __init__(self):
        self.timing_suite = TimingBenchmarkSuite()
        self.baseline_data = self._load_baseline_data()
    
    def _load_baseline_data(self) -> Dict[str, Any]:
        """Load baseline performance expectations."""
        baseline_file = Path(__file__).parent / 'fixtures' / 'performance_baselines.json'
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    async def run_benchmarks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run execution performance benchmarks."""
        results = {
            'metadata': {
                'test_type': 'execution_performance',
                'config': config
            },
            'benchmark_results': {},
            'baseline_comparisons': {},
            'summary': {}
        }
        
        # Test categories to run
        test_categories = config.get('test_categories', ['simple', 'medium', 'complex'])
        warmup_runs = config.get('warmup_runs', 2)
        measurement_runs = config.get('measurement_runs', 5)
        
        for category in test_categories:
            print(f"  Testing {category} evaluations...")
            
            # Test different evaluation components
            category_results = {}
            
            # Test LLM Evaluation Framework
            llm_result = await self._benchmark_llm_evaluation(
                category, warmup_runs, measurement_runs
            )
            category_results['llm_evaluation'] = llm_result
            
            # Test Coding Evaluation
            coding_result = await self._benchmark_coding_evaluation(
                category, warmup_runs, measurement_runs
            )
            category_results['coding_evaluation'] = coding_result
            
            # Test Unified Evaluation Service
            unified_result = await self._benchmark_unified_evaluation(
                category, warmup_runs, measurement_runs
            )
            category_results['unified_evaluation'] = unified_result
            
            results['benchmark_results'][category] = category_results
            
            # Compare against baselines
            baseline_comparison = self._compare_against_baseline(category, category_results)
            results['baseline_comparisons'][category] = baseline_comparison
        
        # Generate summary
        results['summary'] = self._generate_execution_summary(results)
        
        return results
    
    async def _benchmark_llm_evaluation(self, category: str, warmup: int, runs: int) -> Dict[str, Any]:
        """Benchmark LLM evaluation framework."""
        def run_llm_evaluation():
            try:
                # Create a mock evaluation for timing
                evaluator = LLMEvaluator()
                
                if category == 'simple':
                    # Simple test - just initialization and basic operation
                    result = evaluator.get_available_models()
                elif category == 'medium':
                    # Medium test - more complex operation
                    test_config = {
                        'models': ['mock_model'],
                        'test_framework': 'mock'
                    }
                    # Mock a medium complexity operation
                    result = len(str(test_config)) * 100
                else:  # complex
                    # Complex test - full evaluation cycle simulation
                    # Simulate more intensive operation
                    result = sum(range(1000))
                
                return result
            except Exception as e:
                return f"Error: {e}"
        
        return benchmark_function(
            run_llm_evaluation,
            runs=runs,
            warmup=warmup
        )
    
    async def _benchmark_coding_evaluation(self, category: str, warmup: int, runs: int) -> Dict[str, Any]:
        """Benchmark coding evaluation system."""
        def run_coding_evaluation():
            try:
                evaluator = CodingEvaluator()
                
                if category == 'simple':
                    # Simple coding problem
                    problem = {
                        'code': 'def hello(): return "Hello, World!"',
                        'language': 'python',
                        'test_cases': [{'input': '', 'expected': 'Hello, World!'}]
                    }
                elif category == 'medium':
                    # Medium complexity coding problem
                    problem = {
                        'code': 'def factorial(n): return 1 if n <= 1 else n * factorial(n-1)',
                        'language': 'python',
                        'test_cases': [
                            {'input': '5', 'expected': '120'},
                            {'input': '0', 'expected': '1'}
                        ]
                    }
                else:  # complex
                    # Complex coding problem
                    problem = {
                        'code': '''
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
                        return quick_sort(left) + middle + quick_sort(right)
                        ''',
                        'language': 'python',
                        'test_cases': [
                            {'input': '[3,1,4,1,5,9,2,6]', 'expected': '[1,1,2,3,4,5,6,9]'}
                        ]
                    }
                
                # Simulate evaluation process
                result = evaluator.validate_problem_format(problem)
                return result
            except Exception as e:
                return f"Error: {e}"
        
        return benchmark_function(
            run_coding_evaluation,
            runs=runs,
            warmup=warmup
        )
    
    async def _benchmark_unified_evaluation(self, category: str, warmup: int, runs: int) -> Dict[str, Any]:
        """Benchmark unified evaluation service."""
        def run_unified_evaluation():
            try:
                service = UnifiedEvaluationService()
                
                if category == 'simple':
                    # Simple unified evaluation
                    request = {
                        'evaluation_type': 'coding',
                        'problem_id': 'simple_test',
                        'model': 'mock_model'
                    }
                elif category == 'medium':
                    # Medium complexity unified evaluation
                    request = {
                        'evaluation_type': 'intelligence',
                        'test_suite': 'logic_tests',
                        'model': 'mock_model',
                        'parameters': {'difficulty': 'medium'}
                    }
                else:  # complex
                    # Complex unified evaluation
                    request = {
                        'evaluation_type': 'comprehensive',
                        'test_suites': ['coding', 'intelligence', 'tool_calls'],
                        'model': 'mock_model',
                        'parameters': {'batch_size': 10}
                    }
                
                # Simulate service processing
                result = service.validate_request(request)
                return result
            except Exception as e:
                return f"Error: {e}"
        
        return benchmark_function(
            run_unified_evaluation,
            runs=runs,
            warmup=warmup
        )
    
    def _compare_against_baseline(self, category: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare results against baseline expectations."""
        baseline_key = f"{category}_evaluation"
        baseline = self.baseline_data.get('timing_baselines', {}).get(baseline_key, {})
        
        if not baseline:
            return {'error': 'No baseline data available'}
        
        comparisons = {}
        target_time_ms = baseline.get('target_execution_time_ms', 1000)
        max_time_ms = baseline.get('max_execution_time_ms', 5000)
        
        for component, result in results.items():
            if 'timing_stats' in result:
                mean_time_ms = result['timing_stats']['mean'] * 1000  # Convert to ms
                
                comparisons[component] = {
                    'mean_time_ms': mean_time_ms,
                    'target_time_ms': target_time_ms,
                    'max_time_ms': max_time_ms,
                    'meets_target': mean_time_ms <= target_time_ms,
                    'within_max': mean_time_ms <= max_time_ms,
                    'performance_ratio': mean_time_ms / target_time_ms if target_time_ms > 0 else float('inf')
                }
        
        return comparisons
    
    def _generate_execution_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution performance summary."""
        all_times = []
        passed_targets = 0
        total_tests = 0
        
        for category, category_results in results['benchmark_results'].items():
            for component, result in category_results.items():
                if 'timing_stats' in result:
                    mean_time = result['timing_stats']['mean']
                    all_times.append(mean_time)
                    total_tests += 1
        
        # Count baseline comparisons that passed
        for category, comparisons in results['baseline_comparisons'].items():
            for component, comparison in comparisons.items():
                if isinstance(comparison, dict) and comparison.get('meets_target'):
                    passed_targets += 1
        
        summary = {
            'total_tests': total_tests,
            'average_execution_time_s': sum(all_times) / len(all_times) if all_times else 0,
            'fastest_test_s': min(all_times) if all_times else 0,
            'slowest_test_s': max(all_times) if all_times else 0,
            'baseline_targets_met': passed_targets,
            'baseline_success_rate': passed_targets / total_tests if total_tests > 0 else 0
        }
        
        return summary


async def main():
    """Run execution performance tests standalone."""
    tester = ExecutionPerformanceTester()
    
    config = {
        'test_categories': ['simple', 'medium', 'complex'],
        'warmup_runs': 2,
        'measurement_runs': 5
    }
    
    print("Running execution performance benchmarks...")
    results = await tester.run_benchmarks(config)
    
    print("\nExecution Performance Results:")
    print(json.dumps(results['summary'], indent=2))
    
    return results


if __name__ == "__main__":
    asyncio.run(main())