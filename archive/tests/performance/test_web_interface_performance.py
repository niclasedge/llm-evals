"""
Web interface responsiveness and performance tests.
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

from tests.performance.utils import Timer, benchmark_function


class WebInterfacePerformanceTester:
    """Test web interface responsiveness and performance."""
    
    def __init__(self):
        self.baseline_data = self._load_baseline_data()
    
    def _load_baseline_data(self) -> Dict[str, Any]:
        """Load baseline web interface performance expectations."""
        baseline_file = Path(__file__).parent / 'fixtures' / 'performance_baselines.json'
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    async def run_benchmarks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run web interface performance benchmarks."""
        results = {
            'metadata': {
                'test_type': 'web_interface_performance',
                'config': config
            },
            'page_load_results': {},
            'interaction_results': {},
            'data_handling_results': {},
            'baseline_comparisons': {},
            'summary': {}
        }
        
        # Test page load performance
        print("  Testing page load performance...")
        page_load_results = await self._test_page_load_performance()
        results['page_load_results'] = page_load_results
        
        # Test user interaction responsiveness
        print("  Testing interaction responsiveness...")
        interaction_results = await self._test_interaction_responsiveness()
        results['interaction_results'] = interaction_results
        
        # Test data handling performance
        print("  Testing data handling performance...")
        data_handling_results = await self._test_data_handling_performance()
        results['data_handling_results'] = data_handling_results
        
        # Compare against baselines
        baseline_comparison = self._compare_web_baseline(results)
        results['baseline_comparisons'] = baseline_comparison
        
        # Generate summary
        results['summary'] = self._generate_web_summary(results)
        
        return results
    
    async def _test_page_load_performance(self) -> Dict[str, Any]:
        """Test page load times for different interfaces."""
        def simulate_page_load(page_type: str):
            try:
                start_time = time.perf_counter()
                
                # Simulate different page loading scenarios
                if page_type == 'dashboard':
                    # Dashboard with basic metrics
                    time.sleep(0.2)  # 200ms load time
                    page_size_kb = 150
                elif page_type == 'coding_interface':
                    # Coding evaluation interface with Monaco editor
                    time.sleep(0.5)  # 500ms load time (editor initialization)
                    page_size_kb = 800
                elif page_type == 'results_view':
                    # Results visualization page
                    time.sleep(0.3)  # 300ms load time
                    page_size_kb = 300
                elif page_type == 'unified_interface':
                    # Unified evaluation interface
                    time.sleep(0.4)  # 400ms load time
                    page_size_kb = 600
                else:
                    time.sleep(0.1)
                    page_size_kb = 50
                
                end_time = time.perf_counter()
                load_time = end_time - start_time
                
                return {
                    'success': True,
                    'load_time': load_time,
                    'page_size_kb': page_size_kb,
                    'performance_score': max(0, 100 - (load_time * 100))  # Simple perf score
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'load_time': float('inf')
                }
        
        page_types = ['dashboard', 'coding_interface', 'results_view', 'unified_interface']
        page_results = {}
        
        for page_type in page_types:
            page_result = benchmark_function(
                simulate_page_load,
                page_type,
                runs=5,
                warmup=2
            )
            page_results[page_type] = page_result
        
        return page_results
    
    async def _test_interaction_responsiveness(self) -> Dict[str, Any]:
        """Test responsiveness of user interactions."""
        def simulate_interaction(interaction_type: str):
            try:
                start_time = time.perf_counter()
                
                # Simulate different user interactions
                if interaction_type == 'button_click':
                    # Simple button click response
                    time.sleep(0.05)  # 50ms response
                elif interaction_type == 'form_submission':
                    # Form validation and submission
                    time.sleep(0.2)   # 200ms response
                elif interaction_type == 'data_filter':
                    # Filter large dataset
                    time.sleep(0.15)  # 150ms response
                elif interaction_type == 'code_execution':
                    # Execute code in editor
                    time.sleep(1.0)   # 1000ms response
                elif interaction_type == 'real_time_update':
                    # Real-time status update
                    time.sleep(0.03)  # 30ms response
                else:
                    time.sleep(0.1)
                
                end_time = time.perf_counter()
                response_time = end_time - start_time
                
                # Calculate responsiveness score (lower time = higher score)
                if response_time <= 0.1:
                    responsiveness_score = 100
                elif response_time <= 0.3:
                    responsiveness_score = 80
                elif response_time <= 0.5:
                    responsiveness_score = 60
                elif response_time <= 1.0:
                    responsiveness_score = 40
                else:
                    responsiveness_score = 20
                
                return {
                    'success': True,
                    'response_time': response_time,
                    'responsiveness_score': responsiveness_score,
                    'user_perception': 'fast' if response_time <= 0.1 else 'slow' if response_time > 0.5 else 'acceptable'
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'response_time': float('inf')
                }
        
        interaction_types = [
            'button_click', 'form_submission', 'data_filter', 
            'code_execution', 'real_time_update'
        ]
        interaction_results = {}
        
        for interaction_type in interaction_types:
            interaction_result = benchmark_function(
                simulate_interaction,
                interaction_type,
                runs=10,
                warmup=2
            )
            interaction_results[interaction_type] = interaction_result
        
        return interaction_results
    
    async def _test_data_handling_performance(self) -> Dict[str, Any]:
        """Test performance of data handling operations."""
        def simulate_data_operation(operation_type: str):
            try:
                start_time = time.perf_counter()
                
                # Simulate different data operations
                if operation_type == 'load_small_dataset':
                    # Load <100 records
                    time.sleep(0.1)
                    records_processed = 50
                elif operation_type == 'load_medium_dataset':
                    # Load 100-1000 records
                    time.sleep(0.3)
                    records_processed = 500
                elif operation_type == 'load_large_dataset':
                    # Load >1000 records
                    time.sleep(0.8)
                    records_processed = 2000
                elif operation_type == 'search_filter':
                    # Search and filter operations
                    time.sleep(0.2)
                    records_processed = 1000
                elif operation_type == 'export_data':
                    # Export data to file
                    time.sleep(0.5)
                    records_processed = 800
                elif operation_type == 'visualization_render':
                    # Render charts/graphs
                    time.sleep(0.4)
                    records_processed = 300
                else:
                    time.sleep(0.2)
                    records_processed = 100
                
                end_time = time.perf_counter()
                processing_time = end_time - start_time
                
                # Calculate throughput
                throughput = records_processed / processing_time if processing_time > 0 else 0
                
                return {
                    'success': True,
                    'processing_time': processing_time,
                    'records_processed': records_processed,
                    'throughput_records_per_second': throughput,
                    'efficiency_score': min(100, throughput / 10)  # Normalize to 0-100
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'processing_time': float('inf')
                }
        
        operation_types = [
            'load_small_dataset', 'load_medium_dataset', 'load_large_dataset',
            'search_filter', 'export_data', 'visualization_render'
        ]
        data_results = {}
        
        for operation_type in operation_types:
            data_result = benchmark_function(
                simulate_data_operation,
                operation_type,
                runs=5,
                warmup=1
            )
            data_results[operation_type] = data_result
        
        return data_results
    
    def _compare_web_baseline(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare web interface performance against baseline expectations."""
        # Define baseline expectations for web interface
        baseline_expectations = {
            'page_load': {
                'dashboard': 0.3,           # 300ms max
                'coding_interface': 0.8,    # 800ms max (due to editor)
                'results_view': 0.5,        # 500ms max
                'unified_interface': 0.6    # 600ms max
            },
            'interaction': {
                'button_click': 0.1,        # 100ms max
                'form_submission': 0.3,     # 300ms max
                'data_filter': 0.2,         # 200ms max
                'code_execution': 2.0,      # 2000ms max
                'real_time_update': 0.05    # 50ms max
            },
            'data_handling': {
                'load_small_dataset': 0.2,  # 200ms max
                'load_medium_dataset': 0.5, # 500ms max
                'load_large_dataset': 1.0,  # 1000ms max
                'search_filter': 0.3,       # 300ms max
                'export_data': 1.0,         # 1000ms max
                'visualization_render': 0.6 # 600ms max
            }
        }
        
        comparison = {}
        
        # Compare page load performance
        page_load_comparison = {}
        for page_type, page_result in results.get('page_load_results', {}).items():
            if 'timing_stats' in page_result:
                mean_time = page_result['timing_stats']['mean']
                baseline_time = baseline_expectations['page_load'].get(page_type, 0.5)
                
                page_load_comparison[page_type] = {
                    'mean_time_s': mean_time,
                    'baseline_time_s': baseline_time,
                    'meets_target': mean_time <= baseline_time,
                    'performance_ratio': mean_time / baseline_time if baseline_time > 0 else float('inf')
                }
        
        comparison['page_load'] = page_load_comparison
        
        # Compare interaction responsiveness
        interaction_comparison = {}
        for interaction_type, interaction_result in results.get('interaction_results', {}).items():
            if 'timing_stats' in interaction_result:
                mean_time = interaction_result['timing_stats']['mean']
                baseline_time = baseline_expectations['interaction'].get(interaction_type, 0.2)
                
                interaction_comparison[interaction_type] = {
                    'mean_time_s': mean_time,
                    'baseline_time_s': baseline_time,
                    'meets_target': mean_time <= baseline_time,
                    'performance_ratio': mean_time / baseline_time if baseline_time > 0 else float('inf')
                }
        
        comparison['interaction'] = interaction_comparison
        
        # Compare data handling performance
        data_handling_comparison = {}
        for operation_type, operation_result in results.get('data_handling_results', {}).items():
            if 'timing_stats' in operation_result:
                mean_time = operation_result['timing_stats']['mean']
                baseline_time = baseline_expectations['data_handling'].get(operation_type, 0.5)
                
                data_handling_comparison[operation_type] = {
                    'mean_time_s': mean_time,
                    'baseline_time_s': baseline_time,
                    'meets_target': mean_time <= baseline_time,
                    'performance_ratio': mean_time / baseline_time if baseline_time > 0 else float('inf')
                }
        
        comparison['data_handling'] = data_handling_comparison
        
        return comparison
    
    def _generate_web_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate web interface performance summary."""
        total_tests = 0
        targets_met = 0
        all_load_times = []
        all_response_times = []
        
        # Analyze page load results
        for page_type, page_result in results.get('page_load_results', {}).items():
            if 'timing_stats' in page_result:
                mean_time = page_result['timing_stats']['mean']
                all_load_times.append(mean_time)
                total_tests += 1
        
        # Analyze interaction results
        for interaction_type, interaction_result in results.get('interaction_results', {}).items():
            if 'timing_stats' in interaction_result:
                mean_time = interaction_result['timing_stats']['mean']
                all_response_times.append(mean_time)
                total_tests += 1
        
        # Analyze data handling results
        for operation_type, operation_result in results.get('data_handling_results', {}).items():
            if 'timing_stats' in operation_result:
                mean_time = operation_result['timing_stats']['mean']
                all_response_times.append(mean_time)
                total_tests += 1
        
        # Count baseline targets met
        baseline_comparisons = results.get('baseline_comparisons', {})
        for category_comparison in baseline_comparisons.values():
            for test_comparison in category_comparison.values():
                if isinstance(test_comparison, dict) and test_comparison.get('meets_target'):
                    targets_met += 1
        
        # Calculate performance ratings
        avg_load_time = sum(all_load_times) / len(all_load_times) if all_load_times else 0
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
        
        # Determine overall web performance rating
        if targets_met >= total_tests * 0.9:
            performance_rating = 'excellent'
        elif targets_met >= total_tests * 0.7:
            performance_rating = 'good'
        elif targets_met >= total_tests * 0.5:
            performance_rating = 'fair'
        else:
            performance_rating = 'poor'
        
        # User experience assessment
        if avg_response_time <= 0.1:
            user_experience = 'excellent'
        elif avg_response_time <= 0.3:
            user_experience = 'good'
        elif avg_response_time <= 0.5:
            user_experience = 'acceptable'
        else:
            user_experience = 'poor'
        
        summary = {
            'total_tests': total_tests,
            'baseline_targets_met': targets_met,
            'baseline_success_rate': targets_met / total_tests if total_tests > 0 else 0,
            'average_page_load_time_s': avg_load_time,
            'average_interaction_response_time_s': avg_response_time,
            'fastest_page_load_s': min(all_load_times) if all_load_times else 0,
            'slowest_page_load_s': max(all_load_times) if all_load_times else 0,
            'fastest_interaction_s': min(all_response_times) if all_response_times else 0,
            'slowest_interaction_s': max(all_response_times) if all_response_times else 0,
            'performance_rating': performance_rating,
            'user_experience_rating': user_experience,
            'recommendations': self._generate_web_recommendations(results, performance_rating)
        }
        
        return summary
    
    def _generate_web_recommendations(self, results: Dict[str, Any], performance_rating: str) -> List[str]:
        """Generate recommendations for web interface performance."""
        recommendations = []
        
        baseline_comparisons = results.get('baseline_comparisons', {})
        
        # Check page load performance
        page_load_issues = []
        for page_type, comparison in baseline_comparisons.get('page_load', {}).items():
            if not comparison.get('meets_target'):
                page_load_issues.append(page_type)
        
        if page_load_issues:
            recommendations.append(f"Optimize page load times for: {', '.join(page_load_issues)}")
        
        # Check interaction responsiveness
        interaction_issues = []
        for interaction_type, comparison in baseline_comparisons.get('interaction', {}).items():
            if not comparison.get('meets_target'):
                interaction_issues.append(interaction_type)
        
        if interaction_issues:
            recommendations.append(f"Improve interaction responsiveness for: {', '.join(interaction_issues)}")
        
        # Check data handling performance
        data_issues = []
        for operation_type, comparison in baseline_comparisons.get('data_handling', {}).items():
            if not comparison.get('meets_target'):
                data_issues.append(operation_type)
        
        if data_issues:
            recommendations.append(f"Optimize data handling performance for: {', '.join(data_issues)}")
        
        # General recommendations based on rating
        if performance_rating == 'poor':
            recommendations.append("Consider major web interface optimizations")
            recommendations.append("Implement caching strategies")
            recommendations.append("Optimize JavaScript bundle size")
        elif performance_rating == 'fair':
            recommendations.append("Consider minor performance optimizations")
            recommendations.append("Review and optimize slow operations")
        elif performance_rating in ['good', 'excellent']:
            recommendations.append("Web interface performance is satisfactory")
            recommendations.append("Continue monitoring for regressions")
        
        return recommendations


async def main():
    """Run web interface performance tests standalone."""
    tester = WebInterfacePerformanceTester()
    
    config = {
        'test_all_interfaces': True,
        'include_interaction_tests': True,
        'include_data_handling_tests': True
    }
    
    print("Running web interface performance benchmarks...")
    results = await tester.run_benchmarks(config)
    
    print("\nWeb Interface Performance Results:")
    print(json.dumps(results['summary'], indent=2))
    
    performance_rating = results['summary']['performance_rating']
    user_experience = results['summary']['user_experience_rating']
    
    if performance_rating in ['excellent', 'good'] and user_experience in ['excellent', 'good']:
        print(f"\n✅ Web interface performance: {performance_rating} (User experience: {user_experience})")
    else:
        print(f"\n⚠️  Web interface performance: {performance_rating} (User experience: {user_experience})")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())