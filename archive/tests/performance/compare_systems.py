"""
System comparison framework for old vs new performance analysis.
"""

import json
import asyncio
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import datetime

# Add src to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.performance.utils import generate_comparison_report


class SystemComparator:
    """Compare performance between old and new system implementations."""
    
    def __init__(self):
        self.baseline_dir = Path('data/performance/baseline_measurements/')
        self.comparison_results = {}
    
    async def run_comparisons(self, config: Dict[str, Any], current_results: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive system comparisons."""
        results = {
            'metadata': {
                'comparison_type': 'old_vs_new_system',
                'timestamp': datetime.datetime.now().isoformat(),
                'config': config
            },
            'baseline_data': {},
            'current_data': current_results,
            'comparisons': {},
            'regression_analysis': {},
            'improvement_analysis': {},
            'summary': {}
        }
        
        # Load baseline data
        baseline_path = config.get('baseline_path', 'data/performance/baseline_measurements/')
        baseline_data = await self._load_baseline_data(baseline_path)
        results['baseline_data'] = baseline_data
        
        if not baseline_data:
            print("  No baseline data found, creating baseline from current results...")
            await self._create_baseline(baseline_path, current_results)
            results['summary'] = {'status': 'baseline_created', 'message': 'Created new baseline for future comparisons'}
            return results
        
        # Perform detailed comparisons
        print("  Comparing execution performance...")
        execution_comparison = self._compare_execution_performance(
            baseline_data.get('execution_performance', {}),
            current_results.get('execution_performance', {})
        )
        results['comparisons']['execution_performance'] = execution_comparison
        
        print("  Comparing memory usage...")
        memory_comparison = self._compare_memory_usage(
            baseline_data.get('memory_usage', {}),
            current_results.get('memory_usage', {})
        )
        results['comparisons']['memory_usage'] = memory_comparison
        
        print("  Comparing API efficiency...")
        api_comparison = self._compare_api_efficiency(
            baseline_data.get('api_efficiency', {}),
            current_results.get('api_efficiency', {})
        )
        results['comparisons']['api_efficiency'] = api_comparison
        
        print("  Comparing concurrent performance...")
        concurrent_comparison = self._compare_concurrent_performance(
            baseline_data.get('concurrent_performance', {}),
            current_results.get('concurrent_performance', {})
        )
        results['comparisons']['concurrent_performance'] = concurrent_comparison
        
        # Analyze regressions and improvements
        results['regression_analysis'] = self._analyze_regressions(results['comparisons'])
        results['improvement_analysis'] = self._analyze_improvements(results['comparisons'])
        
        # Generate summary
        results['summary'] = self._generate_comparison_summary(results)
        
        return results
    
    async def _load_baseline_data(self, baseline_path: str) -> Dict[str, Any]:
        """Load baseline performance data."""
        baseline_dir = Path(baseline_path)
        
        if not baseline_dir.exists():
            return {}
        
        # Look for the most recent baseline file
        baseline_files = list(baseline_dir.glob('baseline_*.json'))
        
        if not baseline_files:
            return {}
        
        # Use the most recent baseline
        latest_baseline = max(baseline_files, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(latest_baseline, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"  Warning: Could not load baseline data: {e}")
            return {}
    
    async def _create_baseline(self, baseline_path: str, current_results: Dict[str, Any]):
        """Create baseline from current results."""
        baseline_dir = Path(baseline_path)
        baseline_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        baseline_file = baseline_dir / f'baseline_{timestamp}.json'
        
        baseline_data = {
            'metadata': {
                'created_at': datetime.datetime.now().isoformat(),
                'version': '1.0',
                'source': 'initial_baseline_creation'
            },
            'execution_performance': current_results.get('execution_performance', {}),
            'memory_usage': current_results.get('memory_usage', {}),
            'api_efficiency': current_results.get('api_efficiency', {}),
            'concurrent_performance': current_results.get('concurrent_performance', {})
        }
        
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        print(f"  Created baseline: {baseline_file}")
    
    def _compare_execution_performance(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare execution performance between systems."""
        comparison = {
            'test_type': 'execution_performance',
            'category_comparisons': {},
            'overall_change': {}
        }
        
        baseline_results = baseline.get('benchmark_results', {})
        current_results = current.get('benchmark_results', {})
        
        # Compare each category
        for category in set(list(baseline_results.keys()) + list(current_results.keys())):
            if category in baseline_results and category in current_results:
                category_comparison = self._compare_category_performance(
                    baseline_results[category],
                    current_results[category]
                )
                comparison['category_comparisons'][category] = category_comparison
        
        # Calculate overall change
        all_changes = []
        for category_comp in comparison['category_comparisons'].values():
            for component_comp in category_comp.get('component_comparisons', {}).values():
                if 'percentage_change' in component_comp:
                    all_changes.append(component_comp['percentage_change'])
        
        if all_changes:
            comparison['overall_change'] = {
                'average_change_pct': sum(all_changes) / len(all_changes),
                'improvements': sum(1 for x in all_changes if x < -1.0),
                'regressions': sum(1 for x in all_changes if x > 1.0),
                'unchanged': sum(1 for x in all_changes if -1.0 <= x <= 1.0)
            }
        
        return comparison
    
    def _compare_category_performance(self, baseline_category: Dict[str, Any], current_category: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance for a specific category."""
        category_comparison = {
            'component_comparisons': {}
        }
        
        # Compare each component in the category
        for component in set(list(baseline_category.keys()) + list(current_category.keys())):
            if component in baseline_category and component in current_category:
                baseline_stats = baseline_category[component].get('timing_stats', {})
                current_stats = current_category[component].get('timing_stats', {})
                
                if baseline_stats and current_stats:
                    component_comparison = self._compare_timing_stats(baseline_stats, current_stats)
                    category_comparison['component_comparisons'][component] = component_comparison
        
        return category_comparison
    
    def _compare_timing_stats(self, baseline_stats: Dict[str, Any], current_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Compare timing statistics between baseline and current."""
        comparison = {}
        
        for metric in ['mean', 'median', 'min', 'max']:
            if metric in baseline_stats and metric in current_stats:
                baseline_val = baseline_stats[metric]
                current_val = current_stats[metric]
                
                if baseline_val > 0:
                    change_pct = ((current_val - baseline_val) / baseline_val) * 100
                    comparison[metric] = {
                        'baseline': baseline_val,
                        'current': current_val,
                        'absolute_change': current_val - baseline_val,
                        'percentage_change': change_pct,
                        'improvement': change_pct < -1.0,  # > 1% improvement
                        'regression': change_pct > 1.0     # > 1% regression
                    }
        
        # Overall assessment for this component
        if 'mean' in comparison:
            comparison['overall_assessment'] = {
                'improved': comparison['mean']['improvement'],
                'regressed': comparison['mean']['regression'],
                'stable': not comparison['mean']['improvement'] and not comparison['mean']['regression']
            }
        
        return comparison
    
    def _compare_memory_usage(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare memory usage between systems."""
        comparison = {
            'test_type': 'memory_usage',
            'component_comparisons': {},
            'leak_analysis': {}
        }
        
        baseline_results = baseline.get('memory_results', {})
        current_results = current.get('memory_results', {})
        
        # Compare memory usage for each component
        for component in set(list(baseline_results.keys()) + list(current_results.keys())):
            if component in baseline_results and component in current_results:
                baseline_memory = baseline_results[component]
                current_memory = current_results[component]
                
                component_comparison = self._compare_memory_stats(baseline_memory, current_memory)
                comparison['component_comparisons'][component] = component_comparison
        
        # Compare leak detection results
        baseline_leaks = baseline.get('leak_detection', {})
        current_leaks = current.get('leak_detection', {})
        
        for component in set(list(baseline_leaks.keys()) + list(current_leaks.keys())):
            if component in baseline_leaks and component in current_leaks:
                baseline_leak = baseline_leaks[component].get('leak_analysis', {}).get('leak_detected', False)
                current_leak = current_leaks[component].get('leak_analysis', {}).get('leak_detected', False)
                
                comparison['leak_analysis'][component] = {
                    'baseline_leak': baseline_leak,
                    'current_leak': current_leak,
                    'leak_status_changed': baseline_leak != current_leak,
                    'leak_introduced': not baseline_leak and current_leak,
                    'leak_fixed': baseline_leak and not current_leak
                }
        
        return comparison
    
    def _compare_memory_stats(self, baseline_memory: Dict[str, Any], current_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Compare memory statistics between baseline and current."""
        comparison = {}
        
        # Compare peak memory usage
        baseline_peak = baseline_memory.get('peak_traced_mb', 0)
        current_peak = current_memory.get('peak_traced_mb', 0)
        
        if baseline_peak > 0:
            peak_change_pct = ((current_peak - baseline_peak) / baseline_peak) * 100
            comparison['peak_memory'] = {
                'baseline_mb': baseline_peak,
                'current_mb': current_peak,
                'absolute_change_mb': current_peak - baseline_peak,
                'percentage_change': peak_change_pct,
                'improvement': peak_change_pct < -5.0,  # > 5% memory reduction
                'regression': peak_change_pct > 5.0     # > 5% memory increase
            }
        
        # Compare memory delta
        baseline_delta = baseline_memory.get('memory_delta_mb', 0)
        current_delta = current_memory.get('memory_delta_mb', 0)
        
        comparison['memory_delta'] = {
            'baseline_delta_mb': baseline_delta,
            'current_delta_mb': current_delta,
            'delta_change_mb': current_delta - baseline_delta
        }
        
        return comparison
    
    def _compare_api_efficiency(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare API efficiency between systems."""
        comparison = {
            'test_type': 'api_efficiency',
            'provider_comparisons': {}
        }
        
        baseline_providers = baseline.get('provider_results', {})
        current_providers = current.get('provider_results', {})
        
        for provider in set(list(baseline_providers.keys()) + list(current_providers.keys())):
            if provider in baseline_providers and provider in current_providers:
                baseline_provider = baseline_providers[provider]
                current_provider = current_providers[provider]
                
                if 'error' not in baseline_provider and 'error' not in current_provider:
                    provider_comparison = self._compare_provider_performance(baseline_provider, current_provider)
                    comparison['provider_comparisons'][provider] = provider_comparison
        
        return comparison
    
    def _compare_provider_performance(self, baseline_provider: Dict[str, Any], current_provider: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance for a specific API provider."""
        comparison = {}
        
        # Compare single request performance
        baseline_single = baseline_provider.get('single_requests', {}).get('timing_stats', {})
        current_single = current_provider.get('single_requests', {}).get('timing_stats', {})
        
        if baseline_single and current_single:
            comparison['single_requests'] = self._compare_timing_stats(baseline_single, current_single)
        
        # Compare batch request performance
        baseline_batch = baseline_provider.get('batch_requests', {}).get('timing_stats', {})
        current_batch = current_provider.get('batch_requests', {}).get('timing_stats', {})
        
        if baseline_batch and current_batch:
            comparison['batch_requests'] = self._compare_timing_stats(baseline_batch, current_batch)
        
        return comparison
    
    def _compare_concurrent_performance(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare concurrent performance between systems."""
        comparison = {
            'test_type': 'concurrent_performance',
            'scenario_comparisons': {}
        }
        
        baseline_scenarios = baseline.get('load_test_results', {})
        current_scenarios = current.get('load_test_results', {})
        
        for scenario in set(list(baseline_scenarios.keys()) + list(current_scenarios.keys())):
            if scenario in baseline_scenarios and scenario in current_scenarios:
                baseline_scenario = baseline_scenarios[scenario]
                current_scenario = current_scenarios[scenario]
                
                scenario_comparison = self._compare_scenario_performance(baseline_scenario, current_scenario)
                comparison['scenario_comparisons'][scenario] = scenario_comparison
        
        return comparison
    
    def _compare_scenario_performance(self, baseline_scenario: Dict[str, Any], current_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance for a specific load test scenario."""
        comparison = {}
        
        # Compare throughput
        baseline_rps = baseline_scenario.get('requests_per_second', 0)
        current_rps = current_scenario.get('requests_per_second', 0)
        
        if baseline_rps > 0:
            rps_change_pct = ((current_rps - baseline_rps) / baseline_rps) * 100
            comparison['throughput'] = {
                'baseline_rps': baseline_rps,
                'current_rps': current_rps,
                'absolute_change': current_rps - baseline_rps,
                'percentage_change': rps_change_pct,
                'improvement': rps_change_pct > 5.0,   # > 5% throughput increase
                'regression': rps_change_pct < -5.0    # > 5% throughput decrease
            }
        
        # Compare success rate
        baseline_success = baseline_scenario.get('success_rate', 0)
        current_success = current_scenario.get('success_rate', 0)
        
        comparison['success_rate'] = {
            'baseline_rate': baseline_success,
            'current_rate': current_success,
            'absolute_change': current_success - baseline_success,
            'improvement': current_success > baseline_success,
            'regression': current_success < baseline_success
        }
        
        # Compare response time
        baseline_response = baseline_scenario.get('response_time_stats', {}).get('average', 0)
        current_response = current_scenario.get('response_time_stats', {}).get('average', 0)
        
        if baseline_response > 0:
            response_change_pct = ((current_response - baseline_response) / baseline_response) * 100
            comparison['response_time'] = {
                'baseline_avg_s': baseline_response,
                'current_avg_s': current_response,
                'absolute_change_s': current_response - baseline_response,
                'percentage_change': response_change_pct,
                'improvement': response_change_pct < -5.0,  # > 5% response time reduction
                'regression': response_change_pct > 5.0     # > 5% response time increase
            }
        
        return comparison
    
    def _analyze_regressions(self, comparisons: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance regressions across all comparisons."""
        regressions = {
            'total_regressions': 0,
            'critical_regressions': [],
            'moderate_regressions': [],
            'by_category': {}
        }
        
        for category, comparison in comparisons.items():
            category_regressions = []
            
            if category == 'execution_performance':
                for cat_name, cat_comp in comparison.get('category_comparisons', {}).items():
                    for comp_name, comp_comp in cat_comp.get('component_comparisons', {}).items():
                        if 'mean' in comp_comp and comp_comp['mean'].get('regression'):
                            change_pct = comp_comp['mean']['percentage_change']
                            regression = {
                                'type': 'execution_time',
                                'component': f"{cat_name}.{comp_name}",
                                'change_pct': change_pct,
                                'severity': 'critical' if change_pct > 20 else 'moderate'
                            }
                            category_regressions.append(regression)
            
            elif category == 'memory_usage':
                for comp_name, comp_comp in comparison.get('component_comparisons', {}).items():
                    if 'peak_memory' in comp_comp and comp_comp['peak_memory'].get('regression'):
                        change_pct = comp_comp['peak_memory']['percentage_change']
                        regression = {
                            'type': 'memory_usage',
                            'component': comp_name,
                            'change_pct': change_pct,
                            'severity': 'critical' if change_pct > 25 else 'moderate'
                        }
                        category_regressions.append(regression)
            
            # Add similar logic for other categories...
            
            regressions['by_category'][category] = category_regressions
            regressions['total_regressions'] += len(category_regressions)
            
            # Categorize by severity
            for regression in category_regressions:
                if regression['severity'] == 'critical':
                    regressions['critical_regressions'].append(regression)
                else:
                    regressions['moderate_regressions'].append(regression)
        
        return regressions
    
    def _analyze_improvements(self, comparisons: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance improvements across all comparisons."""
        improvements = {
            'total_improvements': 0,
            'significant_improvements': [],
            'minor_improvements': [],
            'by_category': {}
        }
        
        for category, comparison in comparisons.items():
            category_improvements = []
            
            if category == 'execution_performance':
                for cat_name, cat_comp in comparison.get('category_comparisons', {}).items():
                    for comp_name, comp_comp in cat_comp.get('component_comparisons', {}).items():
                        if 'mean' in comp_comp and comp_comp['mean'].get('improvement'):
                            change_pct = abs(comp_comp['mean']['percentage_change'])
                            improvement = {
                                'type': 'execution_time',
                                'component': f"{cat_name}.{comp_name}",
                                'improvement_pct': change_pct,
                                'significance': 'significant' if change_pct > 10 else 'minor'
                            }
                            category_improvements.append(improvement)
            
            # Add similar logic for other categories...
            
            improvements['by_category'][category] = category_improvements
            improvements['total_improvements'] += len(category_improvements)
            
            # Categorize by significance
            for improvement in category_improvements:
                if improvement['significance'] == 'significant':
                    improvements['significant_improvements'].append(improvement)
                else:
                    improvements['minor_improvements'].append(improvement)
        
        return improvements
    
    def _generate_comparison_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall comparison summary."""
        regression_analysis = results.get('regression_analysis', {})
        improvement_analysis = results.get('improvement_analysis', {})
        
        total_regressions = regression_analysis.get('total_regressions', 0)
        total_improvements = improvement_analysis.get('total_improvements', 0)
        critical_regressions = len(regression_analysis.get('critical_regressions', []))
        significant_improvements = len(improvement_analysis.get('significant_improvements', []))
        
        # Calculate overall assessment
        if critical_regressions > 0:
            overall_assessment = 'regression_detected'
        elif total_regressions > total_improvements:
            overall_assessment = 'mixed_with_concerns'
        elif significant_improvements > 0:
            overall_assessment = 'improved'
        elif total_improvements > 0:
            overall_assessment = 'stable_with_improvements'
        else:
            overall_assessment = 'stable'
        
        summary = {
            'overall_assessment': overall_assessment,
            'total_comparisons': sum(len(comp.get('category_comparisons', comp.get('component_comparisons', comp.get('scenario_comparisons', comp.get('provider_comparisons', {}))))) 
                                   for comp in results.get('comparisons', {}).values()),
            'performance_changes': {
                'improvements': total_improvements,
                'regressions': total_regressions,
                'critical_regressions': critical_regressions,
                'significant_improvements': significant_improvements
            },
            'recommendations': self._generate_recommendations(regression_analysis, improvement_analysis),
            'action_required': critical_regressions > 0 or total_regressions > total_improvements * 2
        }
        
        return summary
    
    def _generate_recommendations(self, regression_analysis: Dict[str, Any], improvement_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comparison results."""
        recommendations = []
        
        critical_regressions = regression_analysis.get('critical_regressions', [])
        moderate_regressions = regression_analysis.get('moderate_regressions', [])
        
        if critical_regressions:
            recommendations.append("URGENT: Address critical performance regressions before deployment")
            for regression in critical_regressions[:3]:  # Show top 3
                recommendations.append(f"- Fix {regression['type']} regression in {regression['component']} ({regression['change_pct']:.1f}% slower)")
        
        if moderate_regressions:
            recommendations.append("Consider investigating moderate performance regressions")
        
        significant_improvements = improvement_analysis.get('significant_improvements', [])
        if significant_improvements:
            recommendations.append("Document and maintain performance improvements achieved")
        
        if not critical_regressions and not moderate_regressions:
            recommendations.append("Performance changes are within acceptable ranges")
        
        return recommendations


async def main():
    """Run system comparison standalone."""
    comparator = SystemComparator()
    
    # Mock current results for testing
    current_results = {
        'execution_performance': {
            'benchmark_results': {
                'simple': {
                    'llm_evaluation': {'timing_stats': {'mean': 0.1, 'median': 0.09, 'min': 0.08, 'max': 0.12}}
                }
            }
        }
    }
    
    config = {
        'baseline_path': 'data/performance/baseline_measurements/'
    }
    
    print("Running system comparison...")
    results = await comparator.run_comparisons(config, current_results)
    
    print("\nSystem Comparison Results:")
    print(json.dumps(results['summary'], indent=2))
    
    return results


if __name__ == "__main__":
    asyncio.run(main())