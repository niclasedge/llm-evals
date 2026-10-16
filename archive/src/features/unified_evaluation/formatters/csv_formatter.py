"""
CSV formatter for evaluation results

This module provides CSV formatting for evaluation results.
"""

import csv
import io
from typing import Dict, Any, List

from .base_formatter import BaseFormatter
from ..models import EvaluationResult, ModelResult


class CSVFormatter(BaseFormatter):
    """
    CSV formatter for evaluation results
    
    This formatter outputs evaluation results in CSV format,
    suitable for spreadsheet analysis and data processing.
    """
    
    def format_result(self, result: EvaluationResult) -> str:
        """
        Format evaluation result as CSV
        
        Args:
            result: Evaluation result to format
            
        Returns:
            CSV string representation of the result
        """
        output = io.StringIO()
        
        # Write model results
        if result.model_results:
            writer = csv.writer(output)
            
            # Write header
            headers = [
                'Model Name',
                'Provider',
                'Model ID',
                'Success Rate',
                'Accuracy',
                'Average Time',
                'Total Tests',
                'Passed Tests',
                'Failed Tests',
                'Error Tests',
                'Duration',
                'Errors'
            ]
            writer.writerow(headers)
            
            # Write data rows
            for model_result in result.model_results:
                row = [
                    model_result.model_name,
                    model_result.provider,
                    model_result.model_id,
                    f"{(model_result.metrics.success_rate or 0) * 100:.1f}%",
                    f"{(model_result.metrics.accuracy or 0) * 100:.1f}%",
                    f"{model_result.metrics.average_time:.2f}s" if model_result.metrics.average_time is not None else "N/A",
                    model_result.metrics.total_tests,
                    model_result.metrics.passed_tests,
                    model_result.metrics.failed_tests,
                    model_result.metrics.error_tests,
                    f"{model_result.duration:.2f}s" if model_result.duration else "N/A",
                    "; ".join(model_result.errors) if model_result.errors else ""
                ]
                writer.writerow(row)
        
        return output.getvalue()
    
    def format_summary(self, result: EvaluationResult) -> str:
        """
        Format evaluation summary as CSV
        
        Args:
            result: Evaluation result to summarize
            
        Returns:
            CSV summary string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Summary metrics
        avg_metrics = result.get_average_metrics()
        best_model = result.get_best_model()
        
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Evaluation Type', result.evaluation_type.value])
        writer.writerow(['Models Evaluated', len(result.model_results)])
        writer.writerow(['Total Duration', f"{result.duration:.2f}s"])
        writer.writerow(['Average Success Rate', f"{(avg_metrics.success_rate or 0) * 100:.1f}%"])
        writer.writerow(['Average Accuracy', f"{(avg_metrics.accuracy or 0) * 100:.1f}%"])
        writer.writerow(['Total Tests', avg_metrics.total_tests])
        writer.writerow(['Passed Tests', avg_metrics.passed_tests])
        writer.writerow(['Failed Tests', avg_metrics.failed_tests])
        writer.writerow(['Error Tests', avg_metrics.error_tests])
        
        if best_model:
            writer.writerow(['Best Model', best_model.model_name])
            writer.writerow(['Best Model Success Rate', f"{(best_model.metrics.success_rate or 0) * 100:.1f}%"])
        
        return output.getvalue()
    
    def format_model_result(self, model_result: Any) -> str:
        """
        Format individual model result as CSV
        
        Args:
            model_result: Model result to format
            
        Returns:
            CSV model result string
        """
        if hasattr(model_result, 'model_name'):
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header for single model result
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Model Name', model_result.model_name])
            writer.writerow(['Provider', model_result.provider])
            writer.writerow(['Model ID', model_result.model_id])
            writer.writerow(['Success Rate', f"{(model_result.metrics.success_rate or 0) * 100:.1f}%"])
            writer.writerow(['Accuracy', f"{(model_result.metrics.accuracy or 0) * 100:.1f}%"])
            writer.writerow(['Average Time', f"{model_result.metrics.average_time:.2f}s" if model_result.metrics.average_time is not None else "N/A"])
            writer.writerow(['Total Tests', model_result.metrics.total_tests])
            writer.writerow(['Passed Tests', model_result.metrics.passed_tests])
            writer.writerow(['Failed Tests', model_result.metrics.failed_tests])
            writer.writerow(['Error Tests', model_result.metrics.error_tests])
            
            if model_result.duration:
                writer.writerow(['Duration', f"{model_result.duration:.2f}s"])
            
            if model_result.errors:
                writer.writerow(['Errors', "; ".join(model_result.errors)])
            
            return output.getvalue()
        else:
            return str(model_result)
    
    def format_metrics(self, metrics: Any) -> str:
        """
        Format metrics as CSV
        
        Args:
            metrics: Metrics to format
            
        Returns:
            CSV metrics string
        """
        if hasattr(metrics, 'to_dict'):
            output = io.StringIO()
            writer = csv.writer(output)
            
            writer.writerow(['Metric', 'Value'])
            for key, value in metrics.to_dict().items():
                if isinstance(value, float):
                    if 'rate' in key or 'accuracy' in key:
                        value_str = f"{value * 100:.1f}%"
                    else:
                        value_str = f"{value:.2f}"
                else:
                    value_str = str(value)
                writer.writerow([key.replace('_', ' ').title(), value_str])
            
            return output.getvalue()
        else:
            return str(metrics)
    
    def format_detailed_results(self, result: EvaluationResult) -> str:
        """
        Format detailed results with breakdown by evaluation type
        
        Args:
            result: Evaluation result to format
            
        Returns:
            Detailed CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write detailed breakdown if available
        for model_result in result.model_results:
            if hasattr(model_result, 'details') and model_result.details:
                # Write section header
                writer.writerow([])
                writer.writerow([f"Detailed Results for {model_result.model_name}"])
                writer.writerow([])
                
                # Format details based on evaluation type
                self._write_detailed_csv(writer, model_result.details, result.evaluation_type.value)
        
        return output.getvalue()
    
    def _write_detailed_csv(self, writer: csv.writer, details: Dict[str, Any], eval_type: str):
        """Write detailed results to CSV writer"""
        
        if eval_type == 'coding':
            self._write_coding_details(writer, details)
        elif eval_type == 'vision':
            self._write_vision_details(writer, details)
        elif eval_type == 'tools':
            self._write_tools_details(writer, details)
        elif eval_type == 'intelligence':
            self._write_intelligence_details(writer, details)
    
    def _write_coding_details(self, writer: csv.writer, details: Dict[str, Any]):
        """Write coding evaluation details"""
        writer.writerow(['Problem ID', 'Language', 'Difficulty', 'Total Tests', 'Passed Tests', 'Score'])
        
        for problem_id, results in details.get('results_by_problem', {}).items():
            for result in results:
                writer.writerow([
                    result.get('problem_id', ''),
                    result.get('language', ''),
                    result.get('difficulty', ''),
                    result.get('total_tests', 0),
                    result.get('passed_tests', 0),
                    f"{result.get('score', 0) * 100:.1f}%"
                ])
    
    def _write_vision_details(self, writer: csv.writer, details: Dict[str, Any]):
        """Write vision evaluation details"""
        writer.writerow(['Test Case ID', 'Category', 'Score', 'Passed', 'Execution Time'])
        
        for test_case_id, result in details.get('results_by_test_case', {}).items():
            writer.writerow([
                result.get('test_case_id', ''),
                result.get('category', ''),
                f"{result.get('score', 0) * 100:.1f}%",
                'Yes' if result.get('passed', False) else 'No',
                f"{result.get('execution_time', 0):.2f}s"
            ])
    
    def _write_tools_details(self, writer: csv.writer, details: Dict[str, Any]):
        """Write tools evaluation details"""
        writer.writerow(['Scenario ID', 'Category', 'Difficulty', 'Overall Score', 'Tool Call Score', 'Passed'])
        
        for scenario_id, result in details.get('results_by_scenario', {}).items():
            writer.writerow([
                result.get('scenario_id', ''),
                result.get('category', ''),
                result.get('difficulty', ''),
                f"{result.get('overall_score', 0) * 100:.1f}%",
                f"{result.get('tool_call_score', 0) * 100:.1f}%",
                'Yes' if result.get('passed', False) else 'No'
            ])
    
    def _write_intelligence_details(self, writer: csv.writer, details: Dict[str, Any]):
        """Write intelligence evaluation details"""
        writer.writerow(['Test ID', 'Category', 'Difficulty', 'Overall Score', 'Accuracy Score', 'Passed'])
        
        for test_id, result in details.get('results_by_test', {}).items():
            writer.writerow([
                result.get('test_id', ''),
                result.get('category', ''),
                result.get('difficulty', ''),
                f"{result.get('overall_score', 0) * 100:.1f}%",
                f"{result.get('accuracy_score', 0) * 100:.1f}%",
                'Yes' if result.get('passed', False) else 'No'
            ])