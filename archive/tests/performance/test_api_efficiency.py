"""
LLM provider API efficiency and performance tests.
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.performance.utils import benchmark_function, Timer
from src.features.llm_evaluation.llm_service import LLMService
from src.core.llm_client import LLMClient


class APIEfficiencyTester:
    """Test API efficiency and performance for LLM providers."""
    
    def __init__(self):
        self.baseline_data = self._load_baseline_data()
    
    def _load_baseline_data(self) -> Dict[str, Any]:
        """Load baseline API performance expectations."""
        baseline_file = Path(__file__).parent / 'fixtures' / 'performance_baselines.json'
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    async def run_benchmarks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run API efficiency benchmarks."""
        results = {
            'metadata': {
                'test_type': 'api_efficiency',
                'config': config
            },
            'provider_results': {},
            'request_patterns': {},
            'baseline_comparisons': {},
            'summary': {}
        }
        
        providers = config.get('providers', ['openrouter', 'ollama'])
        request_count = config.get('request_count', 10)
        timeout_seconds = config.get('timeout_seconds', 30)
        
        for provider in providers:
            if self._is_provider_available(provider):
                print(f"  Testing {provider} API efficiency...")
                
                # Test single requests
                single_request_result = await self._benchmark_single_requests(
                    provider, request_count, timeout_seconds
                )
                
                # Test batch requests
                batch_request_result = await self._benchmark_batch_requests(
                    provider, request_count, timeout_seconds
                )
                
                # Test connection overhead
                connection_result = await self._benchmark_connection_overhead(
                    provider, timeout_seconds
                )
                
                results['provider_results'][provider] = {
                    'single_requests': single_request_result,
                    'batch_requests': batch_request_result,
                    'connection_overhead': connection_result
                }
                
                # Compare against baseline
                baseline_comparison = self._compare_api_baseline(provider, results['provider_results'][provider])
                results['baseline_comparisons'][provider] = baseline_comparison
            else:
                print(f"  Skipping {provider} (not available)")
                results['provider_results'][provider] = {'error': 'Provider not available'}
        
        # Test request patterns
        results['request_patterns'] = await self._test_request_patterns(config)
        
        # Generate summary
        results['summary'] = self._generate_api_summary(results)
        
        return results
    
    def _is_provider_available(self, provider: str) -> bool:
        """Check if provider is available for testing."""
        try:
            if provider == 'openrouter':
                # Check if API key is available
                import os
                return bool(os.getenv('OPENROUTER_API_KEY'))
            elif provider == 'ollama':
                # Check if Ollama service is running
                import requests
                try:
                    response = requests.get('http://localhost:11434/api/tags', timeout=2)
                    return response.status_code == 200
                except:
                    return False
            else:
                return False
        except Exception:
            return False
    
    async def _benchmark_single_requests(self, provider: str, count: int, timeout: int) -> Dict[str, Any]:
        """Benchmark single API requests."""
        def make_single_request():
            try:
                # Simulate API request timing
                start_time = time.perf_counter()
                
                if provider == 'openrouter':
                    # Mock OpenRouter request
                    result = self._mock_openrouter_request()
                elif provider == 'ollama':
                    # Mock Ollama request
                    result = self._mock_ollama_request()
                else:
                    result = {'mock': 'response'}
                
                end_time = time.perf_counter()
                request_time = end_time - start_time
                
                return {
                    'success': True,
                    'response_time': request_time,
                    'response_size': len(str(result))
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'response_time': timeout
                }
        
        # Benchmark multiple single requests
        benchmark_result = benchmark_function(
            make_single_request,
            runs=count,
            warmup=2
        )
        
        # Calculate additional metrics
        successful_requests = 0
        total_response_time = 0
        
        if 'measurements' in benchmark_result:
            # For this mock, all measurements are timing
            successful_requests = count
            total_response_time = sum(benchmark_result['measurements'])
        
        benchmark_result.update({
            'successful_requests': successful_requests,
            'failed_requests': count - successful_requests,
            'success_rate': successful_requests / count if count > 0 else 0,
            'total_response_time': total_response_time,
            'requests_per_second': successful_requests / total_response_time if total_response_time > 0 else 0
        })
        
        return benchmark_result
    
    async def _benchmark_batch_requests(self, provider: str, batch_size: int, timeout: int) -> Dict[str, Any]:
        """Benchmark batch API requests."""
        def make_batch_request():
            try:
                start_time = time.perf_counter()
                
                # Simulate batch processing
                results = []
                for i in range(min(batch_size, 5)):  # Limit batch size for testing
                    if provider == 'openrouter':
                        result = self._mock_openrouter_request()
                    elif provider == 'ollama':
                        result = self._mock_ollama_request()
                    else:
                        result = {'mock': f'response_{i}'}
                    results.append(result)
                
                end_time = time.perf_counter()
                batch_time = end_time - start_time
                
                return {
                    'success': True,
                    'batch_time': batch_time,
                    'batch_size': len(results),
                    'average_per_request': batch_time / len(results) if results else 0
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'batch_time': timeout
                }
        
        return benchmark_function(
            make_batch_request,
            runs=3,
            warmup=1
        )
    
    async def _benchmark_connection_overhead(self, provider: str, timeout: int) -> Dict[str, Any]:
        """Benchmark connection establishment overhead."""
        def test_connection():
            try:
                start_time = time.perf_counter()
                
                # Simulate connection establishment
                if provider == 'openrouter':
                    # Mock connection to OpenRouter
                    connection_time = 0.1  # Mock 100ms connection time
                elif provider == 'ollama':
                    # Mock connection to Ollama
                    connection_time = 0.05  # Mock 50ms connection time
                else:
                    connection_time = 0.2
                
                # Simulate actual connection time
                time.sleep(connection_time)
                
                end_time = time.perf_counter()
                actual_time = end_time - start_time
                
                return {
                    'success': True,
                    'connection_time': actual_time,
                    'overhead_ms': actual_time * 1000
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'connection_time': timeout
                }
        
        return benchmark_function(
            test_connection,
            runs=5,
            warmup=1
        )
    
    def _mock_openrouter_request(self) -> Dict[str, Any]:
        """Mock OpenRouter API request."""
        return {
            'model': 'mock_openrouter_model',
            'response': 'Mock response from OpenRouter',
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 20,
                'total_tokens': 30
            }
        }
    
    def _mock_ollama_request(self) -> Dict[str, Any]:
        """Mock Ollama API request."""
        return {
            'model': 'mock_ollama_model',
            'response': 'Mock response from Ollama',
            'duration': 500000000,  # 500ms in nanoseconds
            'context': [1, 2, 3, 4, 5]
        }
    
    async def _test_request_patterns(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test different request patterns."""
        patterns = {
            'sequential': await self._test_sequential_pattern(),
            'concurrent': await self._test_concurrent_pattern(),
            'burst': await self._test_burst_pattern()
        }
        
        return patterns
    
    async def _test_sequential_pattern(self) -> Dict[str, Any]:
        """Test sequential request pattern."""
        def sequential_requests():
            start_time = time.perf_counter()
            
            # Simulate 3 sequential requests
            for i in range(3):
                time.sleep(0.1)  # Mock 100ms per request
            
            end_time = time.perf_counter()
            return end_time - start_time
        
        result = benchmark_function(sequential_requests, runs=3, warmup=1)
        result['pattern_type'] = 'sequential'
        return result
    
    async def _test_concurrent_pattern(self) -> Dict[str, Any]:
        """Test concurrent request pattern."""
        async def concurrent_requests():
            start_time = time.perf_counter()
            
            # Simulate 3 concurrent requests
            tasks = []
            for i in range(3):
                task = asyncio.create_task(self._mock_async_request())
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            return end_time - start_time
        
        # Run concurrent test
        times = []
        for _ in range(3):
            execution_time = await concurrent_requests()
            times.append(execution_time)
        
        return {
            'pattern_type': 'concurrent',
            'measurements': times,
            'timing_stats': {
                'mean': sum(times) / len(times),
                'min': min(times),
                'max': max(times)
            }
        }
    
    async def _test_burst_pattern(self) -> Dict[str, Any]:
        """Test burst request pattern."""
        def burst_requests():
            start_time = time.perf_counter()
            
            # Simulate burst of requests
            for i in range(5):
                time.sleep(0.02)  # Mock 20ms per request in burst
            
            end_time = time.perf_counter()
            return end_time - start_time
        
        result = benchmark_function(burst_requests, runs=3, warmup=1)
        result['pattern_type'] = 'burst'
        return result
    
    async def _mock_async_request(self):
        """Mock asynchronous API request."""
        await asyncio.sleep(0.1)  # Mock 100ms async request
        return {'mock': 'async_response'}
    
    def _compare_api_baseline(self, provider: str, provider_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare API performance against baseline."""
        baseline = self.baseline_data.get('timing_baselines', {}).get('api_request', {})
        
        if not baseline:
            return {'error': 'No baseline data available'}
        
        target_time_ms = baseline.get('target_execution_time_ms', 800)
        max_time_ms = baseline.get('max_execution_time_ms', 2000)
        
        comparison = {
            'provider': provider,
            'target_time_ms': target_time_ms,
            'max_time_ms': max_time_ms
        }
        
        # Compare single request performance
        single_requests = provider_results.get('single_requests', {})
        if 'timing_stats' in single_requests:
            mean_time_ms = single_requests['timing_stats']['mean'] * 1000
            comparison['single_request'] = {
                'mean_time_ms': mean_time_ms,
                'meets_target': mean_time_ms <= target_time_ms,
                'within_max': mean_time_ms <= max_time_ms,
                'performance_ratio': mean_time_ms / target_time_ms if target_time_ms > 0 else float('inf')
            }
        
        # Compare batch request performance
        batch_requests = provider_results.get('batch_requests', {})
        if 'timing_stats' in batch_requests:
            batch_mean_ms = batch_requests['timing_stats']['mean'] * 1000
            comparison['batch_request'] = {
                'mean_time_ms': batch_mean_ms,
                'meets_target': batch_mean_ms <= target_time_ms * 2,  # Allow 2x for batch
                'within_max': batch_mean_ms <= max_time_ms * 2
            }
        
        return comparison
    
    def _generate_api_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate API efficiency summary."""
        total_providers = len(results['provider_results'])
        successful_providers = 0
        all_response_times = []
        baseline_targets_met = 0
        
        for provider, provider_result in results['provider_results'].items():
            if 'error' not in provider_result:
                successful_providers += 1
                
                # Collect response times
                single_requests = provider_result.get('single_requests', {})
                if 'timing_stats' in single_requests:
                    mean_time = single_requests['timing_stats']['mean']
                    all_response_times.append(mean_time)
        
        # Count baseline targets met
        for provider, comparison in results.get('baseline_comparisons', {}).items():
            if isinstance(comparison, dict):
                single_req = comparison.get('single_request', {})
                if single_req.get('meets_target'):
                    baseline_targets_met += 1
        
        summary = {
            'total_providers_tested': total_providers,
            'successful_providers': successful_providers,
            'provider_success_rate': successful_providers / total_providers if total_providers > 0 else 0,
            'average_response_time_s': sum(all_response_times) / len(all_response_times) if all_response_times else 0,
            'fastest_provider_time_s': min(all_response_times) if all_response_times else 0,
            'slowest_provider_time_s': max(all_response_times) if all_response_times else 0,
            'baseline_targets_met': baseline_targets_met,
            'api_efficiency': 'good' if baseline_targets_met >= successful_providers * 0.8 else 'needs_improvement'
        }
        
        return summary


async def main():
    """Run API efficiency tests standalone."""
    tester = APIEfficiencyTester()
    
    config = {
        'providers': ['openrouter', 'ollama'],
        'request_count': 5,
        'timeout_seconds': 10
    }
    
    print("Running API efficiency benchmarks...")
    results = await tester.run_benchmarks(config)
    
    print("\nAPI Efficiency Results:")
    print(json.dumps(results['summary'], indent=2))
    
    return results


if __name__ == "__main__":
    asyncio.run(main())