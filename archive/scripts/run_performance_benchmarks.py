#!/usr/bin/env python3
"""
Script to run performance benchmarks for the LLM evaluation framework.
"""

import sys
import os
import asyncio
import argparse
import json

# Add src and tests to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, 'src'))
sys.path.insert(0, repo_root)

def run_quick_benchmark():
    """Run quick benchmark tests."""
    print("🚀 Running quick performance benchmarks...")
    
    try:
        # Import here to avoid path issues
        from tests.performance.test_execution_performance import ExecutionPerformanceTester
        from tests.performance.test_memory_usage import MemoryUsageTester
        
        async def run_tests():
            results = {}
            
            # Quick execution test
            print("  Testing execution performance...")
            exec_tester = ExecutionPerformanceTester()
            exec_config = {
                'test_categories': ['simple'],
                'warmup_runs': 1,
                'measurement_runs': 3
            }
            exec_results = await exec_tester.run_benchmarks(exec_config)
            results['execution'] = exec_results
            
            # Quick memory test
            print("  Testing memory usage...")
            memory_tester = MemoryUsageTester()
            memory_config = {
                'leak_detection': True,
                'threshold_mb': 10.0,
                'test_runs': 2
            }
            memory_results = await memory_tester.run_benchmarks(memory_config)
            results['memory'] = memory_results
            
            return results
        
        # Run async tests
        results = asyncio.run(run_tests())
        
        print("\n📊 Quick Benchmark Summary:")
        if 'execution' in results:
            exec_summary = results['execution'].get('summary', {})
            print(f"  Execution Tests: {exec_summary.get('total_tests', 0)} tests")
            print(f"  Average Time: {exec_summary.get('average_execution_time_s', 0):.3f}s")
            
        if 'memory' in results:
            memory_summary = results['memory'].get('summary', {})
            print(f"  Memory Tests: {memory_summary.get('total_components_tested', 0)} components")
            print(f"  Memory Leaks: {memory_summary.get('memory_leaks_detected', 0)}")
        
        print("\n✅ Quick benchmarks completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Quick benchmarks failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_basic_performance_test():
    """Run basic performance validation test."""
    print("🧪 Running basic performance validation...")
    
    try:
        # Test timing utilities
        from tests.performance.utils.timing_utils import Timer, benchmark_function
        
        def simple_operation():
            return sum(range(1000))
        
        # Basic timing test
        timer = Timer()
        timer.start()
        result = simple_operation()
        elapsed = timer.stop()
        
        print(f"  Simple operation: {elapsed:.4f}s")
        
        # Benchmark test
        benchmark_result = benchmark_function(simple_operation, runs=3, warmup=1)
        mean_time = benchmark_result['timing_stats']['mean']
        print(f"  Benchmarked operation: {mean_time:.4f}s average")
        
        # Test memory utilities
        from tests.performance.utils.memory_utils import MemoryProfiler
        
        profiler = MemoryProfiler()
        profiler.start_profiling()
        
        # Do some memory work
        data = [i for i in range(10000)]
        del data
        
        memory_stats = profiler.stop_profiling()
        peak_mb = memory_stats.get('peak_traced_mb', 0)
        print(f"  Memory test: {peak_mb:.2f} MB peak usage")
        
        print("\n✅ Basic performance validation passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Basic performance validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run performance benchmarks')
    parser.add_argument('--mode', choices=['basic', 'quick', 'test'], default='basic',
                        help='Benchmark mode to run')
    
    args = parser.parse_args()
    
    if args.mode == 'basic':
        success = run_basic_performance_test()
    elif args.mode == 'quick':
        success = run_quick_benchmark()
    elif args.mode == 'test':
        success = run_basic_performance_test()
    else:
        print(f"Unknown mode: {args.mode}")
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())