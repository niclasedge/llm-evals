"""
Concurrent evaluation performance and load testing.
"""

import asyncio
import json
import time
import threading
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.performance.utils import Timer


class ConcurrentPerformanceTester:
    """Test concurrent evaluation performance and system behavior under load."""
    
    def __init__(self):
        self.baseline_data = self._load_baseline_data()
        self.load_scenarios = self._load_load_scenarios()
    
    def _load_baseline_data(self) -> Dict[str, Any]:
        """Load baseline concurrent performance expectations."""
        baseline_file = Path(__file__).parent / 'fixtures' / 'performance_baselines.json'
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    def _load_load_scenarios(self) -> Dict[str, Any]:
        """Load load testing scenarios."""
        scenarios_file = Path(__file__).parent / 'fixtures' / 'load_test_scenarios.json'
        
        if scenarios_file.exists():
            with open(scenarios_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    async def run_benchmarks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run concurrent performance benchmarks."""
        results = {
            'metadata': {
                'test_type': 'concurrent_performance',
                'config': config
            },
            'load_test_results': {},
            'concurrency_analysis': {},
            'baseline_comparisons': {},
            'summary': {}
        }
        
        scenarios = config.get('scenarios', ['light_load', 'moderate_load'])
        max_workers = config.get('max_workers', 5)
        
        for scenario_name in scenarios:
            scenario = self._get_scenario_config(scenario_name)
            if scenario:
                print(f"  Running {scenario_name} scenario...")
                
                # Run load test
                load_result = await self._run_load_test(scenario, max_workers)
                results['load_test_results'][scenario_name] = load_result
                
                # Analyze concurrency behavior
                concurrency_analysis = self._analyze_concurrency(load_result)
                results['concurrency_analysis'][scenario_name] = concurrency_analysis
                
                # Compare against baseline
                baseline_comparison = self._compare_concurrent_baseline(scenario_name, load_result)
                results['baseline_comparisons'][scenario_name] = baseline_comparison
            else:
                print(f"  Skipping {scenario_name} (scenario not found)")
        
        # Generate summary
        results['summary'] = self._generate_concurrent_summary(results)
        
        return results
    
    def _get_scenario_config(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a load test scenario."""
        scenarios = self.load_scenarios.get('scenarios', [])
        for scenario in scenarios:
            if scenario.get('name') == scenario_name:
                return scenario
        return None
    
    async def _run_load_test(self, scenario: Dict[str, Any], max_workers: int) -> Dict[str, Any]:
        """Run load test for a specific scenario."""
        concurrent_users = min(scenario.get('concurrent_users', 2), max_workers)
        duration_minutes = scenario.get('duration_minutes', 1)
        ramp_up_time_seconds = scenario.get('ramp_up_time_seconds', 10)
        
        print(f"    Running {concurrent_users} concurrent users for {duration_minutes} minutes...")
        
        # Track performance metrics
        start_time = time.perf_counter()
        completed_requests = 0
        failed_requests = 0
        response_times = []
        
        # Run concurrent workers
        async def worker(worker_id: int, duration: float):
            worker_start = time.perf_counter()
            worker_requests = 0
            worker_failures = 0
            worker_times = []
            
            while time.perf_counter() - worker_start < duration:
                try:
                    request_start = time.perf_counter()
                    
                    # Simulate evaluation work
                    await self._simulate_evaluation_work(scenario)
                    
                    request_end = time.perf_counter()
                    request_time = request_end - request_start
                    
                    worker_requests += 1
                    worker_times.append(request_time)
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    worker_failures += 1
                    print(f"    Worker {worker_id} error: {e}")
            
            return {
                'worker_id': worker_id,
                'requests': worker_requests,
                'failures': worker_failures,
                'response_times': worker_times
            }
        
        # Start workers with ramp-up
        workers = []
        ramp_up_delay = ramp_up_time_seconds / concurrent_users if concurrent_users > 0 else 0
        
        for i in range(concurrent_users):
            # Stagger worker starts
            if i > 0:
                await asyncio.sleep(ramp_up_delay)
            
            worker_task = asyncio.create_task(
                worker(i, duration_minutes * 60)
            )
            workers.append(worker_task)
        
        # Wait for all workers to complete
        worker_results = await asyncio.gather(*workers, return_exceptions=True)
        
        # Aggregate results
        for result in worker_results:
            if isinstance(result, dict):
                completed_requests += result['requests']
                failed_requests += result['failures']
                response_times.extend(result['response_times'])
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        # Calculate performance metrics
        total_requests = completed_requests + failed_requests
        success_rate = completed_requests / total_requests if total_requests > 0 else 0
        requests_per_second = completed_requests / total_duration if total_duration > 0 else 0
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        return {
            'scenario': scenario['name'],
            'concurrent_users': concurrent_users,
            'duration_seconds': total_duration,
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'failed_requests': failed_requests,
            'success_rate': success_rate,
            'requests_per_second': requests_per_second,
            'response_time_stats': {
                'average': avg_response_time,
                'min': min_response_time,
                'max': max_response_time,
                'samples': len(response_times)
            },
            'worker_results': [r for r in worker_results if isinstance(r, dict)]
        }
    
    async def _simulate_evaluation_work(self, scenario: Dict[str, Any]):
        """Simulate evaluation work based on scenario."""
        test_categories = scenario.get('test_categories', ['simple'])
        
        # Simulate different workloads
        if 'simple' in test_categories:
            # Light CPU work
            await asyncio.sleep(0.05)  # 50ms
            result = sum(range(100))
        
        if 'medium' in test_categories:
            # Medium CPU work
            await asyncio.sleep(0.1)   # 100ms
            result = sum(range(1000))
        
        if 'complex' in test_categories:
            # Heavy CPU work
            await asyncio.sleep(0.2)   # 200ms
            result = sum(range(5000))
        
        return result
    
    def _analyze_concurrency(self, load_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze concurrency behavior from load test results."""
        concurrent_users = load_result.get('concurrent_users', 0)
        requests_per_second = load_result.get('requests_per_second', 0)
        success_rate = load_result.get('success_rate', 0)
        avg_response_time = load_result.get('response_time_stats', {}).get('average', 0)
        
        # Calculate concurrency metrics
        theoretical_max_rps = concurrent_users * (1 / avg_response_time) if avg_response_time > 0 else 0
        concurrency_efficiency = requests_per_second / theoretical_max_rps if theoretical_max_rps > 0 else 0
        
        # Analyze scalability
        scalability_score = min(success_rate, concurrency_efficiency)
        
        # Categorize performance
        if scalability_score > 0.8:
            performance_category = 'excellent'
        elif scalability_score > 0.6:
            performance_category = 'good'
        elif scalability_score > 0.4:
            performance_category = 'fair'
        else:
            performance_category = 'poor'
        
        return {
            'concurrent_users': concurrent_users,
            'requests_per_second': requests_per_second,
            'theoretical_max_rps': theoretical_max_rps,
            'concurrency_efficiency': concurrency_efficiency,
            'scalability_score': scalability_score,
            'performance_category': performance_category,
            'bottleneck_indicators': {
                'low_success_rate': success_rate < 0.9,
                'high_response_time': avg_response_time > 1.0,
                'low_throughput': requests_per_second < concurrent_users * 0.5
            }
        }
    
    def _compare_concurrent_baseline(self, scenario_name: str, load_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare concurrent performance against baseline."""
        baseline_key = scenario_name.replace('_', '_')
        baseline = self.baseline_data.get('concurrent_baselines', {}).get(baseline_key, {})
        
        if not baseline:
            return {'error': 'No baseline data available'}
        
        max_response_time_ms = baseline.get('max_response_time_ms', 2000)
        min_throughput_rps = baseline.get('min_throughput_requests_per_second', 1)
        
        actual_response_time_ms = load_result.get('response_time_stats', {}).get('average', 0) * 1000
        actual_throughput_rps = load_result.get('requests_per_second', 0)
        
        comparison = {
            'scenario': scenario_name,
            'baseline_max_response_ms': max_response_time_ms,
            'actual_response_ms': actual_response_time_ms,
            'baseline_min_throughput_rps': min_throughput_rps,
            'actual_throughput_rps': actual_throughput_rps,
            'meets_response_target': actual_response_time_ms <= max_response_time_ms,
            'meets_throughput_target': actual_throughput_rps >= min_throughput_rps,
            'overall_pass': (actual_response_time_ms <= max_response_time_ms and 
                           actual_throughput_rps >= min_throughput_rps)
        }
        
        return comparison
    
    def _generate_concurrent_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate concurrent performance summary."""
        total_scenarios = len(results['load_test_results'])
        successful_scenarios = 0
        baseline_targets_met = 0
        
        all_throughputs = []
        all_response_times = []
        performance_categories = []
        
        # Analyze load test results
        for scenario_name, load_result in results['load_test_results'].items():
            success_rate = load_result.get('success_rate', 0)
            if success_rate > 0.8:  # Consider successful if > 80% success rate
                successful_scenarios += 1
            
            throughput = load_result.get('requests_per_second', 0)
            avg_response = load_result.get('response_time_stats', {}).get('average', 0)
            
            if throughput > 0:
                all_throughputs.append(throughput)
            if avg_response > 0:
                all_response_times.append(avg_response)
        
        # Count baseline targets met
        for scenario_name, comparison in results.get('baseline_comparisons', {}).items():
            if isinstance(comparison, dict) and comparison.get('overall_pass'):
                baseline_targets_met += 1
        
        # Analyze concurrency analysis results
        for scenario_name, analysis in results.get('concurrency_analysis', {}).items():
            performance_category = analysis.get('performance_category', 'unknown')
            performance_categories.append(performance_category)
        
        # Calculate overall performance rating
        excellent_count = performance_categories.count('excellent')
        good_count = performance_categories.count('good')
        
        if excellent_count >= len(performance_categories) * 0.7:
            overall_performance = 'excellent'
        elif (excellent_count + good_count) >= len(performance_categories) * 0.7:
            overall_performance = 'good'
        else:
            overall_performance = 'needs_improvement'
        
        summary = {
            'total_scenarios_tested': total_scenarios,
            'successful_scenarios': successful_scenarios,
            'scenario_success_rate': successful_scenarios / total_scenarios if total_scenarios > 0 else 0,
            'baseline_targets_met': baseline_targets_met,
            'baseline_success_rate': baseline_targets_met / total_scenarios if total_scenarios > 0 else 0,
            'average_throughput_rps': sum(all_throughputs) / len(all_throughputs) if all_throughputs else 0,
            'average_response_time_s': sum(all_response_times) / len(all_response_times) if all_response_times else 0,
            'performance_categories': {
                'excellent': performance_categories.count('excellent'),
                'good': performance_categories.count('good'),
                'fair': performance_categories.count('fair'),
                'poor': performance_categories.count('poor')
            },
            'overall_performance_rating': overall_performance,
            'scalability_assessment': 'good' if baseline_targets_met >= total_scenarios * 0.8 else 'needs_improvement'
        }
        
        return summary


async def main():
    """Run concurrent performance tests standalone."""
    tester = ConcurrentPerformanceTester()
    
    config = {
        'scenarios': ['light_load', 'moderate_load'],
        'max_workers': 3
    }
    
    print("Running concurrent performance benchmarks...")
    results = await tester.run_benchmarks(config)
    
    print("\nConcurrent Performance Results:")
    print(json.dumps(results['summary'], indent=2))
    
    overall_rating = results['summary']['overall_performance_rating']
    if overall_rating in ['excellent', 'good']:
        print(f"\n✅ Concurrent performance: {overall_rating}")
    else:
        print(f"\n⚠️  Concurrent performance: {overall_rating}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())