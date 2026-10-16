"""
Main benchmark suite orchestrator for LLM evaluation performance testing.
"""

import json
import asyncio
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse

# Add both src and current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, os.path.join(repo_root, 'src'))
sys.path.insert(0, repo_root)

from tests.performance.utils import (
    Timer, benchmark_function, MemoryProfiler, track_memory_usage,
    PerformanceReporter, create_benchmark_problems
)
from tests.performance.test_execution_performance import ExecutionPerformanceTester
from tests.performance.test_memory_usage import MemoryUsageTester
from tests.performance.test_api_efficiency import APIEfficiencyTester
from tests.performance.test_concurrent_performance import ConcurrentPerformanceTester
from tests.performance.compare_systems import SystemComparator


class BenchmarkSuite:
    """Main benchmark suite for comprehensive performance testing."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.reporter = PerformanceReporter()
        self.results = {}
        
        # Initialize test components
        self.execution_tester = ExecutionPerformanceTester()
        self.memory_tester = MemoryUsageTester()
        self.api_tester = APIEfficiencyTester()
        self.concurrent_tester = ConcurrentPerformanceTester()
        self.comparator = SystemComparator()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load benchmark configuration."""
        default_config = {
            'execution_tests': {
                'enabled': True,
                'test_categories': ['simple', 'medium', 'complex'],
                'warmup_runs': 2,
                'measurement_runs': 5
            },
            'memory_tests': {
                'enabled': True,
                'leak_detection': True,
                'threshold_mb': 10.0,
                'test_runs': 3
            },
            'api_tests': {
                'enabled': True,
                'providers': ['openrouter', 'ollama'],
                'request_count': 10,
                'timeout_seconds': 30
            },
            'concurrent_tests': {
                'enabled': True,
                'scenarios': ['light_load', 'moderate_load'],
                'max_workers': 5
            },
            'comparison_tests': {
                'enabled': True,
                'baseline_path': 'data/performance/baseline_measurements/'
            },
            'output': {
                'results_dir': 'data/performance/benchmark_results/',
                'reports_dir': 'data/performance/comparison_reports/',
                'generate_charts': True,
                'formats': ['json', 'markdown']
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        
        return default_config
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("🚀 Starting comprehensive benchmark suite...")
        
        # Ensure output directories exist
        self._ensure_output_dirs()
        
        # Run execution performance tests
        if self.config['execution_tests']['enabled']:
            print("\n⏱️  Running execution performance tests...")
            execution_results = await self.execution_tester.run_benchmarks(
                self.config['execution_tests']
            )
            self.results['execution_performance'] = execution_results
            self.reporter.add_timing_results('execution_tests', execution_results)
        
        # Run memory usage tests
        if self.config['memory_tests']['enabled']:
            print("\n🧠 Running memory usage tests...")
            memory_results = await self.memory_tester.run_benchmarks(
                self.config['memory_tests']
            )
            self.results['memory_usage'] = memory_results
            self.reporter.add_memory_results('memory_tests', memory_results)
        
        # Run API efficiency tests
        if self.config['api_tests']['enabled']:
            print("\n🌐 Running API efficiency tests...")
            api_results = await self.api_tester.run_benchmarks(
                self.config['api_tests']
            )
            self.results['api_efficiency'] = api_results
            self.reporter.add_timing_results('api_tests', api_results)
        
        # Run concurrent performance tests
        if self.config['concurrent_tests']['enabled']:
            print("\n⚡ Running concurrent performance tests...")
            concurrent_results = await self.concurrent_tester.run_benchmarks(
                self.config['concurrent_tests']
            )
            self.results['concurrent_performance'] = concurrent_results
            self.reporter.add_timing_results('concurrent_tests', concurrent_results)
        
        # Run system comparison tests
        if self.config['comparison_tests']['enabled']:
            print("\n📊 Running system comparison tests...")
            comparison_results = await self.comparator.run_comparisons(
                self.config['comparison_tests'], self.results
            )
            self.results['system_comparisons'] = comparison_results
            self.reporter.add_comparison('system_comparison', comparison_results)
        
        # Generate reports
        await self._generate_reports()
        
        print("\n✅ Benchmark suite completed successfully!")
        return self.results
    
    async def run_quick_benchmark(self) -> Dict[str, Any]:
        """Run a quick benchmark subset for rapid validation."""
        print("🏃 Running quick benchmark suite...")
        
        # Quick execution test
        quick_config = {
            'test_categories': ['simple'],
            'warmup_runs': 1,
            'measurement_runs': 3
        }
        
        execution_results = await self.execution_tester.run_benchmarks(quick_config)
        
        # Quick memory test
        memory_config = {
            'leak_detection': True,
            'threshold_mb': 10.0,
            'test_runs': 2
        }
        
        memory_results = await self.memory_tester.run_benchmarks(memory_config)
        
        results = {
            'execution_performance': execution_results,
            'memory_usage': memory_results,
            'benchmark_type': 'quick'
        }
        
        print("✅ Quick benchmark completed!")
        return results
    
    async def run_category_benchmark(self, category: str) -> Dict[str, Any]:
        """Run benchmarks for a specific category."""
        print(f"🎯 Running {category} benchmarks...")
        
        if category == 'execution':
            results = await self.execution_tester.run_benchmarks(
                self.config['execution_tests']
            )
        elif category == 'memory':
            results = await self.memory_tester.run_benchmarks(
                self.config['memory_tests']
            )
        elif category == 'api':
            results = await self.api_tester.run_benchmarks(
                self.config['api_tests']
            )
        elif category == 'concurrent':
            results = await self.concurrent_tester.run_benchmarks(
                self.config['concurrent_tests']
            )
        else:
            raise ValueError(f"Unknown benchmark category: {category}")
        
        print(f"✅ {category} benchmarks completed!")
        return {category: results}
    
    def _ensure_output_dirs(self):
        """Ensure output directories exist."""
        Path(self.config['output']['results_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.config['output']['reports_dir']).mkdir(parents=True, exist_ok=True)
    
    async def _generate_reports(self):
        """Generate benchmark reports."""
        print("\n📄 Generating performance reports...")
        
        timestamp = Path().cwd().name
        results_dir = Path(self.config['output']['results_dir'])
        reports_dir = Path(self.config['output']['reports_dir'])
        
        # Save raw results
        results_file = results_dir / f'benchmark_results_{timestamp}.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate formatted reports
        if 'json' in self.config['output']['formats']:
            json_report = reports_dir / f'performance_report_{timestamp}.json'
            self.reporter.save_json_report(str(json_report))
        
        if 'markdown' in self.config['output']['formats']:
            md_report = reports_dir / f'performance_report_{timestamp}.md'
            self.reporter.generate_markdown_report(str(md_report))
        
        # Generate charts if enabled
        if self.config['output']['generate_charts']:
            try:
                from tests.performance.utils.report_generator import create_performance_visualization
                charts_dir = reports_dir / 'charts'
                create_performance_visualization(self.reporter.report_data, str(charts_dir))
                print(f"📈 Performance charts saved to {charts_dir}")
            except ImportError:
                print("⚠️  Charts not generated (matplotlib/seaborn not available)")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark results summary."""
        if not self.results:
            return {'error': 'No benchmark results available'}
        
        summary = {
            'total_tests': len(self.results),
            'categories': list(self.results.keys()),
            'performance_summary': self.reporter.generate_summary()
        }
        
        return summary


async def main():
    """Main entry point for benchmark suite."""
    parser = argparse.ArgumentParser(description='LLM Evaluation Performance Benchmark Suite')
    parser.add_argument('--config', type=str, help='Path to benchmark configuration file')
    parser.add_argument('--mode', choices=['full', 'quick', 'category'], default='full',
                        help='Benchmark mode to run')
    parser.add_argument('--category', type=str, choices=['execution', 'memory', 'api', 'concurrent'],
                        help='Specific category to benchmark (when mode=category)')
    parser.add_argument('--output-dir', type=str, help='Override output directory')
    
    args = parser.parse_args()
    
    # Initialize benchmark suite
    suite = BenchmarkSuite(args.config)
    
    # Override output directory if specified
    if args.output_dir:
        suite.config['output']['results_dir'] = f"{args.output_dir}/benchmark_results/"
        suite.config['output']['reports_dir'] = f"{args.output_dir}/comparison_reports/"
    
    try:
        # Run benchmarks based on mode
        if args.mode == 'full':
            results = await suite.run_all_benchmarks()
        elif args.mode == 'quick':
            results = await suite.run_quick_benchmark()
        elif args.mode == 'category':
            if not args.category:
                print("Error: --category required when mode=category")
                return 1
            results = await suite.run_category_benchmark(args.category)
        
        # Print summary
        summary = suite.get_summary()
        print("\n📊 Benchmark Summary:")
        print(json.dumps(summary, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))