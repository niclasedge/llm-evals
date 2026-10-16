"""
Memory usage and leak detection performance tests.
"""

import asyncio
import json
import gc
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.performance.utils import check_memory_leaks, MemoryProfiler, MemoryBenchmarkSuite
from src.features.llm_evaluation.main_evaluator import LLMEvaluator
from src.features.coding_evaluation.evaluator import CodingEvaluator
from src.features.unified_evaluation.service import UnifiedEvaluationService


class MemoryUsageTester:
    """Test memory usage and detect leaks in evaluation components."""
    
    def __init__(self):
        self.memory_suite = MemoryBenchmarkSuite()
        self.baseline_data = self._load_baseline_data()
    
    def _load_baseline_data(self) -> Dict[str, Any]:
        """Load baseline memory expectations."""
        baseline_file = Path(__file__).parent / 'fixtures' / 'performance_baselines.json'
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    async def run_benchmarks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run memory usage benchmarks."""
        results = {
            'metadata': {
                'test_type': 'memory_usage',
                'config': config
            },
            'memory_results': {},
            'leak_detection': {},
            'baseline_comparisons': {},
            'summary': {}
        }
        
        leak_detection = config.get('leak_detection', True)
        threshold_mb = config.get('threshold_mb', 10.0)
        test_runs = config.get('test_runs', 3)
        
        # Test different evaluation components
        components = [
            ('llm_evaluation', self._test_llm_evaluation_memory),
            ('coding_evaluation', self._test_coding_evaluation_memory),
            ('unified_evaluation', self._test_unified_evaluation_memory)
        ]
        
        for component_name, test_func in components:
            print(f"  Testing {component_name} memory usage...")
            
            # Memory profiling
            memory_result = await self._profile_component_memory(test_func)
            results['memory_results'][component_name] = memory_result
            
            # Leak detection
            if leak_detection:
                leak_result = await self._detect_memory_leaks(
                    test_func, runs=test_runs, threshold_mb=threshold_mb
                )
                results['leak_detection'][component_name] = leak_result
            
            # Baseline comparison
            baseline_comparison = self._compare_memory_baseline(component_name, memory_result)
            results['baseline_comparisons'][component_name] = baseline_comparison
        
        # Generate summary
        results['summary'] = self._generate_memory_summary(results)
        
        return results
    
    async def _profile_component_memory(self, test_func) -> Dict[str, Any]:
        """Profile memory usage of a component."""
        profiler = MemoryProfiler()
        
        # Run with memory profiling
        profiler.start_profiling()
        
        try:
            await test_func()
        except Exception as e:
            print(f"Warning: Test function failed during memory profiling: {e}")
        
        memory_stats = profiler.stop_profiling()
        
        # Add process memory info
        process_info = profiler.get_process_memory_info()
        memory_stats.update(process_info)
        
        return memory_stats
    
    async def _detect_memory_leaks(self, test_func, runs: int, threshold_mb: float) -> Dict[str, Any]:
        """Detect memory leaks by running function multiple times."""
        def sync_test_func():
            try:
                # Run test function synchronously for leak detection
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(test_func())
                loop.close()
            except Exception as e:
                print(f"Warning: Test function failed during leak detection: {e}")
        
        leak_results = check_memory_leaks(
            sync_test_func,
            runs=runs,
            threshold_mb=threshold_mb
        )
        
        return leak_results
    
    async def _test_llm_evaluation_memory(self):
        """Test LLM evaluation memory usage."""
        try:
            evaluator = LLMEvaluator()
            
            # Simulate evaluation operations that might use memory
            models = evaluator.get_available_models()
            
            # Create some test data
            test_data = {
                'prompts': ['Test prompt ' + str(i) for i in range(100)],
                'responses': ['Test response ' + str(i) for i in range(100)]
            }
            
            # Simulate processing
            processed = []
            for prompt in test_data['prompts'][:10]:  # Limit to avoid excessive memory
                processed.append(prompt.upper())
            
            # Force garbage collection
            del test_data
            del processed
            gc.collect()
            
        except Exception as e:
            print(f"LLM evaluation memory test error: {e}")
    
    async def _test_coding_evaluation_memory(self):
        """Test coding evaluation memory usage."""
        try:
            evaluator = CodingEvaluator()
            
            # Create test problems that might use memory
            problems = []
            for i in range(50):
                problem = {
                    'id': f'test_{i}',
                    'code': f'def test_function_{i}(): return {i} * 2',
                    'language': 'python',
                    'test_cases': [
                        {'input': str(i), 'expected': str(i * 2)}
                    ]
                }
                problems.append(problem)
            
            # Simulate evaluation of problems
            for problem in problems[:5]:  # Limit to avoid excessive processing
                result = evaluator.validate_problem_format(problem)
            
            # Clean up
            del problems
            gc.collect()
            
        except Exception as e:
            print(f"Coding evaluation memory test error: {e}")
    
    async def _test_unified_evaluation_memory(self):
        """Test unified evaluation memory usage."""
        try:
            service = UnifiedEvaluationService()
            
            # Create multiple evaluation requests
            requests = []
            for i in range(20):
                request = {
                    'evaluation_type': 'coding',
                    'problem_id': f'memory_test_{i}',
                    'model': 'mock_model',
                    'data': {'test_data': list(range(100))}  # Some test data
                }
                requests.append(request)
            
            # Process requests
            for request in requests[:3]:  # Limit processing
                result = service.validate_request(request)
            
            # Clean up
            del requests
            gc.collect()
            
        except Exception as e:
            print(f"Unified evaluation memory test error: {e}")
    
    def _compare_memory_baseline(self, component: str, memory_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare memory usage against baseline."""
        # Map component names to baseline categories
        component_mapping = {
            'llm_evaluation': 'medium_evaluation',
            'coding_evaluation': 'simple_evaluation', 
            'unified_evaluation': 'complex_evaluation'
        }
        
        baseline_key = component_mapping.get(component, 'medium_evaluation')
        baseline = self.baseline_data.get('memory_baselines', {}).get(baseline_key, {})
        
        if not baseline:
            return {'error': 'No baseline data available'}
        
        peak_memory_mb = memory_result.get('peak_traced_mb', 0)
        memory_delta_mb = memory_result.get('memory_delta_mb', 0)
        
        target_peak_mb = baseline.get('target_peak_memory_mb', 50)
        max_peak_mb = baseline.get('max_peak_memory_mb', 100)
        leak_threshold_mb = baseline.get('memory_leak_threshold_mb', 10)
        
        comparison = {
            'peak_memory_mb': peak_memory_mb,
            'memory_delta_mb': memory_delta_mb,
            'target_peak_mb': target_peak_mb,
            'max_peak_mb': max_peak_mb,
            'leak_threshold_mb': leak_threshold_mb,
            'meets_target': peak_memory_mb <= target_peak_mb,
            'within_max': peak_memory_mb <= max_peak_mb,
            'no_significant_leak': abs(memory_delta_mb) <= leak_threshold_mb,
            'memory_efficiency_ratio': peak_memory_mb / target_peak_mb if target_peak_mb > 0 else float('inf')
        }
        
        return comparison
    
    def _generate_memory_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate memory usage summary."""
        total_components = len(results['memory_results'])
        leaks_detected = 0
        baseline_targets_met = 0
        
        # Analyze memory results
        all_peak_memories = []
        all_memory_deltas = []
        
        for component, memory_result in results['memory_results'].items():
            peak_mb = memory_result.get('peak_traced_mb', 0)
            delta_mb = memory_result.get('memory_delta_mb', 0)
            
            if peak_mb > 0:
                all_peak_memories.append(peak_mb)
            if delta_mb != 0:
                all_memory_deltas.append(abs(delta_mb))
        
        # Count leaks detected
        for component, leak_result in results.get('leak_detection', {}).items():
            if leak_result.get('leak_analysis', {}).get('leak_detected'):
                leaks_detected += 1
        
        # Count baseline targets met
        for component, comparison in results.get('baseline_comparisons', {}).items():
            if isinstance(comparison, dict) and comparison.get('meets_target'):
                baseline_targets_met += 1
        
        summary = {
            'total_components_tested': total_components,
            'memory_leaks_detected': leaks_detected,
            'baseline_targets_met': baseline_targets_met,
            'baseline_success_rate': baseline_targets_met / total_components if total_components > 0 else 0,
            'average_peak_memory_mb': sum(all_peak_memories) / len(all_peak_memories) if all_peak_memories else 0,
            'max_peak_memory_mb': max(all_peak_memories) if all_peak_memories else 0,
            'average_memory_delta_mb': sum(all_memory_deltas) / len(all_memory_deltas) if all_memory_deltas else 0,
            'memory_efficiency': 'good' if leaks_detected == 0 else 'needs_attention'
        }
        
        return summary


async def main():
    """Run memory usage tests standalone."""
    tester = MemoryUsageTester()
    
    config = {
        'leak_detection': True,
        'threshold_mb': 10.0,
        'test_runs': 3
    }
    
    print("Running memory usage benchmarks...")
    results = await tester.run_benchmarks(config)
    
    print("\nMemory Usage Results:")
    print(json.dumps(results['summary'], indent=2))
    
    if results['summary']['memory_leaks_detected'] > 0:
        print("\n⚠️  Memory leaks detected! Check detailed results for more information.")
    else:
        print("\n✅ No memory leaks detected.")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())