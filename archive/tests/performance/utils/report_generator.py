"""
Performance report generation utilities.
"""

import json
import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Optional visualization dependencies
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    plt = None
    sns = None
    pd = None


class PerformanceReporter:
    """Generate comprehensive performance reports."""
    
    def __init__(self):
        self.report_data = {
            'metadata': {
                'generated_at': datetime.datetime.now().isoformat(),
                'test_environment': self._get_test_environment()
            },
            'timing_results': {},
            'memory_results': {},
            'comparisons': {},
            'summary': {}
        }
    
    def _get_test_environment(self) -> Dict[str, Any]:
        """Get test environment information."""
        import platform
        import sys
        
        return {
            'platform': platform.platform(),
            'python_version': sys.version,
            'architecture': platform.architecture(),
            'processor': platform.processor()
        }
    
    def add_timing_results(self, name: str, results: Dict[str, Any]) -> None:
        """Add timing benchmark results."""
        self.report_data['timing_results'][name] = results
    
    def add_memory_results(self, name: str, results: Dict[str, Any]) -> None:
        """Add memory benchmark results."""
        self.report_data['memory_results'][name] = results
    
    def add_comparison(self, name: str, comparison: Dict[str, Any]) -> None:
        """Add performance comparison results."""
        self.report_data['comparisons'][name] = comparison
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate overall performance summary."""
        timing_count = len(self.report_data['timing_results'])
        memory_count = len(self.report_data['memory_results'])
        comparison_count = len(self.report_data['comparisons'])
        
        # Analyze timing results
        timing_summary = {}
        if self.report_data['timing_results']:
            all_mean_times = []
            for result in self.report_data['timing_results'].values():
                if 'timing_stats' in result and 'mean' in result['timing_stats']:
                    all_mean_times.append(result['timing_stats']['mean'])
            
            if all_mean_times:
                timing_summary = {
                    'total_tests': len(all_mean_times),
                    'average_execution_time': sum(all_mean_times) / len(all_mean_times),
                    'fastest_test_time': min(all_mean_times),
                    'slowest_test_time': max(all_mean_times)
                }
        
        # Analyze memory results
        memory_summary = {}
        memory_leaks = 0
        if self.report_data['memory_results']:
            all_peak_memories = []
            for result in self.report_data['memory_results'].values():
                if 'leak_analysis' in result and result['leak_analysis'].get('leak_detected'):
                    memory_leaks += 1
                
                if 'memory_statistics' in result:
                    peak = result['memory_statistics'].get('max_peak_memory_mb', 0)
                    if peak > 0:
                        all_peak_memories.append(peak)
            
            if all_peak_memories:
                memory_summary = {
                    'total_tests': len(all_peak_memories),
                    'memory_leaks_detected': memory_leaks,
                    'average_peak_memory_mb': sum(all_peak_memories) / len(all_peak_memories),
                    'max_peak_memory_mb': max(all_peak_memories),
                    'min_peak_memory_mb': min(all_peak_memories)
                }
        
        # Analyze comparisons
        comparison_summary = {}
        improvements = 0
        regressions = 0
        if self.report_data['comparisons']:
            for comparison in self.report_data['comparisons'].values():
                changes = comparison.get('changes', {})
                for metric_changes in changes.values():
                    if isinstance(metric_changes, dict) and 'improvement' in metric_changes:
                        if metric_changes['improvement']:
                            improvements += 1
                        else:
                            regressions += 1
            
            comparison_summary = {
                'total_comparisons': comparison_count,
                'improvements': improvements,
                'regressions': regressions
            }
        
        summary = {
            'test_counts': {
                'timing_tests': timing_count,
                'memory_tests': memory_count,
                'comparisons': comparison_count
            },
            'timing_summary': timing_summary,
            'memory_summary': memory_summary,
            'comparison_summary': comparison_summary
        }
        
        self.report_data['summary'] = summary
        return summary
    
    def save_json_report(self, filepath: str) -> None:
        """Save performance report as JSON."""
        self.generate_summary()
        
        with open(filepath, 'w') as f:
            json.dump(self.report_data, f, indent=2)
    
    def generate_markdown_report(self, filepath: str) -> None:
        """Generate markdown performance report."""
        self.generate_summary()
        
        report_lines = [
            "# Performance Benchmark Report",
            "",
            f"**Generated:** {self.report_data['metadata']['generated_at']}",
            f"**Platform:** {self.report_data['metadata']['test_environment']['platform']}",
            f"**Python:** {self.report_data['metadata']['test_environment']['python_version']}",
            "",
            "## Executive Summary",
            ""
        ]
        
        summary = self.report_data['summary']
        
        # Test counts
        counts = summary.get('test_counts', {})
        report_lines.extend([
            f"- **Timing Tests:** {counts.get('timing_tests', 0)}",
            f"- **Memory Tests:** {counts.get('memory_tests', 0)}",
            f"- **Performance Comparisons:** {counts.get('comparisons', 0)}",
            ""
        ])
        
        # Timing summary
        timing = summary.get('timing_summary', {})
        if timing:
            report_lines.extend([
                "### Timing Performance",
                "",
                f"- **Average Execution Time:** {timing.get('average_execution_time', 0):.4f}s",
                f"- **Fastest Test:** {timing.get('fastest_test_time', 0):.4f}s",
                f"- **Slowest Test:** {timing.get('slowest_test_time', 0):.4f}s",
                ""
            ])
        
        # Memory summary
        memory = summary.get('memory_summary', {})
        if memory:
            report_lines.extend([
                "### Memory Performance",
                "",
                f"- **Memory Leaks Detected:** {memory.get('memory_leaks_detected', 0)}",
                f"- **Average Peak Memory:** {memory.get('average_peak_memory_mb', 0):.2f} MB",
                f"- **Maximum Peak Memory:** {memory.get('max_peak_memory_mb', 0):.2f} MB",
                ""
            ])
        
        # Comparison summary
        comparison = summary.get('comparison_summary', {})
        if comparison:
            report_lines.extend([
                "### Performance Comparisons",
                "",
                f"- **Performance Improvements:** {comparison.get('improvements', 0)}",
                f"- **Performance Regressions:** {comparison.get('regressions', 0)}",
                ""
            ])
        
        # Detailed results
        if self.report_data['timing_results']:
            report_lines.extend([
                "## Detailed Timing Results",
                "",
                "| Test Name | Mean Time (s) | Runs | Min (s) | Max (s) |",
                "|-----------|---------------|------|---------|---------|"
            ])
            
            for name, result in self.report_data['timing_results'].items():
                stats = result.get('timing_stats', {})
                mean = stats.get('mean', 0)
                runs = result.get('runs', 0)
                min_time = stats.get('min', 0)
                max_time = stats.get('max', 0)
                
                report_lines.append(f"| {name} | {mean:.4f} | {runs} | {min_time:.4f} | {max_time:.4f} |")
            
            report_lines.append("")
        
        if self.report_data['memory_results']:
            report_lines.extend([
                "## Detailed Memory Results",
                "",
                "| Test Name | Peak Memory (MB) | Memory Leak | Delta (MB) |",
                "|-----------|------------------|-------------|------------|"
            ])
            
            for name, result in self.report_data['memory_results'].items():
                leak_detected = "Yes" if result.get('leak_analysis', {}).get('leak_detected') else "No"
                
                peak_memory = 0
                memory_delta = 0
                
                if 'memory_statistics' in result:
                    peak_memory = result['memory_statistics'].get('max_peak_memory_mb', 0)
                    memory_delta = result['memory_statistics'].get('average_memory_delta_mb', 0)
                elif 'memory_stats' in result:
                    peak_memory = result['memory_stats'].get('peak_traced_mb', 0)
                    memory_delta = result['memory_stats'].get('memory_delta_mb', 0)
                
                report_lines.append(f"| {name} | {peak_memory:.2f} | {leak_detected} | {memory_delta:.2f} |")
            
            report_lines.append("")
        
        # Write report
        with open(filepath, 'w') as f:
            f.write('\n'.join(report_lines))


def generate_comparison_report(baseline_results: Dict[str, Any], current_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate detailed comparison report between two result sets.
    
    Args:
        baseline_results: Baseline performance results
        current_results: Current performance results
    
    Returns:
        Comprehensive comparison analysis
    """
    comparison = {
        'metadata': {
            'generated_at': datetime.datetime.now().isoformat(),
            'baseline_tests': len(baseline_results),
            'current_tests': len(current_results)
        },
        'timing_comparisons': {},
        'memory_comparisons': {},
        'summary': {
            'improvements': 0,
            'regressions': 0,
            'unchanged': 0
        }
    }
    
    # Compare timing results
    for test_name in baseline_results.keys():
        if test_name in current_results:
            baseline = baseline_results[test_name]
            current = current_results[test_name]
            
            # Compare timing if both have timing stats
            if ('timing_stats' in baseline and 'timing_stats' in current):
                baseline_mean = baseline['timing_stats'].get('mean', 0)
                current_mean = current['timing_stats'].get('mean', 0)
                
                if baseline_mean > 0:
                    change_pct = ((current_mean - baseline_mean) / baseline_mean) * 100
                    
                    timing_comparison = {
                        'baseline_mean': baseline_mean,
                        'current_mean': current_mean,
                        'absolute_change': current_mean - baseline_mean,
                        'percentage_change': change_pct,
                        'improvement': change_pct < -1.0,  # > 1% improvement
                        'regression': change_pct > 1.0     # > 1% regression
                    }
                    
                    comparison['timing_comparisons'][test_name] = timing_comparison
                    
                    if timing_comparison['improvement']:
                        comparison['summary']['improvements'] += 1
                    elif timing_comparison['regression']:
                        comparison['summary']['regressions'] += 1
                    else:
                        comparison['summary']['unchanged'] += 1
            
            # Compare memory if both have memory stats
            if ('memory_statistics' in baseline and 'memory_statistics' in current):
                baseline_memory = baseline['memory_statistics'].get('max_peak_memory_mb', 0)
                current_memory = current['memory_statistics'].get('max_peak_memory_mb', 0)
                
                if baseline_memory > 0:
                    memory_change_pct = ((current_memory - baseline_memory) / baseline_memory) * 100
                    
                    memory_comparison = {
                        'baseline_peak_mb': baseline_memory,
                        'current_peak_mb': current_memory,
                        'absolute_change_mb': current_memory - baseline_memory,
                        'percentage_change': memory_change_pct,
                        'improvement': memory_change_pct < -5.0,  # > 5% memory reduction
                        'regression': memory_change_pct > 5.0     # > 5% memory increase
                    }
                    
                    comparison['memory_comparisons'][test_name] = memory_comparison
    
    return comparison


def create_performance_visualization(results: Dict[str, Any], output_dir: str) -> None:
    """
    Create performance visualization charts.
    
    Args:
        results: Performance benchmark results
        output_dir: Directory to save charts
    """
    if not VISUALIZATION_AVAILABLE:
        print("⚠️  Visualization libraries not available, skipping chart generation")
        return
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Timing results chart
    if 'timing_results' in results and results['timing_results']:
        timing_data = []
        for name, result in results['timing_results'].items():
            if 'timing_stats' in result:
                stats = result['timing_stats']
                timing_data.append({
                    'Test': name,
                    'Mean Time (s)': stats.get('mean', 0),
                    'Min Time (s)': stats.get('min', 0),
                    'Max Time (s)': stats.get('max', 0)
                })
        
        if timing_data:
            df = pd.DataFrame(timing_data)
            
            plt.figure(figsize=(12, 6))
            plt.bar(df['Test'], df['Mean Time (s)'])
            plt.title('Execution Time by Test')
            plt.xlabel('Test Name')
            plt.ylabel('Mean Execution Time (seconds)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(output_path / 'timing_results.png')
            plt.close()
    
    # Memory results chart
    if 'memory_results' in results and results['memory_results']:
        memory_data = []
        for name, result in results['memory_results'].items():
            peak_memory = 0
            if 'memory_statistics' in result:
                peak_memory = result['memory_statistics'].get('max_peak_memory_mb', 0)
            elif 'memory_stats' in result:
                peak_memory = result['memory_stats'].get('peak_traced_mb', 0)
            
            if peak_memory > 0:
                memory_data.append({
                    'Test': name,
                    'Peak Memory (MB)': peak_memory
                })
        
        if memory_data:
            df = pd.DataFrame(memory_data)
            
            plt.figure(figsize=(12, 6))
            plt.bar(df['Test'], df['Peak Memory (MB)'])
            plt.title('Peak Memory Usage by Test')
            plt.xlabel('Test Name')
            plt.ylabel('Peak Memory (MB)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(output_path / 'memory_results.png')
            plt.close()