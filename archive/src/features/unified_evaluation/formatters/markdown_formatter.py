"""
Markdown formatter for evaluation results

This module provides Markdown formatting for evaluation results.
"""

from typing import Dict, Any

from .base_formatter import BaseFormatter
from ..models import EvaluationResult, ModelResult


class MarkdownFormatter(BaseFormatter):
    """
    Markdown formatter for evaluation results
    
    This formatter outputs evaluation results in Markdown format,
    suitable for documentation and reports.
    """
    
    def format_result(self, result: EvaluationResult) -> str:
        """
        Format evaluation result as Markdown
        
        Args:
            result: Evaluation result to format
            
        Returns:
            Markdown string representation of the result
        """
        md_lines = []
        
        # Title
        md_lines.append(f"# {result.evaluation_type.value.title()} Evaluation Results")
        md_lines.append("")
        
        # Summary
        md_lines.append("## Summary")
        md_lines.append("")
        md_lines.append(f"- **Evaluation Type**: {result.evaluation_type.value}")
        md_lines.append(f"- **Models Evaluated**: {len(result.model_results)}")
        md_lines.append(f"- **Duration**: {self._format_duration(result.duration)}")
        md_lines.append(f"- **Started**: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"- **Completed**: {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")
        
        # Overall metrics
        avg_metrics = result.get_average_metrics()
        md_lines.append("## Overall Metrics")
        md_lines.append("")
        md_lines.append(f"- **Average Success Rate**: {self._format_percentage(avg_metrics.success_rate or 0)}")
        md_lines.append(f"- **Average Accuracy**: {self._format_percentage(avg_metrics.accuracy or 0)}")
        md_lines.append(f"- **Total Tests**: {avg_metrics.total_tests}")
        md_lines.append(f"- **Passed Tests**: {avg_metrics.passed_tests}")
        md_lines.append(f"- **Failed Tests**: {avg_metrics.failed_tests}")
        md_lines.append(f"- **Error Tests**: {avg_metrics.error_tests}")
        md_lines.append("")
        
        # Best model
        best_model = result.get_best_model()
        if best_model:
            md_lines.append("## Best Performing Model")
            md_lines.append("")
            md_lines.append(f"**{best_model.model_name}** ({best_model.provider})")
            md_lines.append(f"- Success Rate: {self._format_percentage(best_model.metrics.success_rate or 0)}")
            md_lines.append(f"- Accuracy: {self._format_percentage(best_model.metrics.accuracy or 0)}")
            md_lines.append(f"- Average Time: {best_model.metrics.average_time:.2f}s" if best_model.metrics.average_time is not None else "- Average Time: N/A")
            md_lines.append("")
        
        # Model results
        md_lines.append("## Model Results")
        md_lines.append("")
        
        for model_result in result.model_results:
            md_lines.extend(self._format_model_result_md(model_result))
        
        # Detailed summary
        if result.summary:
            md_lines.append("## Detailed Summary")
            md_lines.append("")
            for key, value in result.summary.items():
                if isinstance(value, dict):
                    md_lines.append(f"### {key.replace('_', ' ').title()}")
                    md_lines.append("")
                    for sub_key, sub_value in value.items():
                        md_lines.append(f"- **{sub_key.replace('_', ' ').title()}**: {sub_value}")
                else:
                    md_lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    def format_summary(self, result: EvaluationResult) -> str:
        """
        Format evaluation summary as Markdown
        
        Args:
            result: Evaluation result to summarize
            
        Returns:
            Markdown summary string
        """
        md_lines = []
        
        md_lines.append(f"# {result.evaluation_type.value.title()} Evaluation Summary")
        md_lines.append("")
        
        # Key metrics
        avg_metrics = result.get_average_metrics()
        md_lines.append("## Key Metrics")
        md_lines.append("")
        md_lines.append(f"- **Models Evaluated**: {len(result.model_results)}")
        md_lines.append(f"- **Overall Success Rate**: {self._format_percentage(avg_metrics.success_rate or 0)}")
        md_lines.append(f"- **Total Duration**: {self._format_duration(result.duration)}")
        md_lines.append("")
        
        # Best model
        best_model = result.get_best_model()
        if best_model:
            md_lines.append("## Best Model")
            md_lines.append("")
            md_lines.append(f"**{best_model.model_name}** with {self._format_percentage(best_model.metrics.success_rate or 0)} success rate")
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    def _format_model_result_md(self, model_result: ModelResult) -> list:
        """Format individual model result as Markdown"""
        md_lines = []
        
        md_lines.append(f"### {model_result.model_name}")
        md_lines.append("")
        md_lines.append(f"**Provider**: {model_result.provider}")
        md_lines.append(f"**Model ID**: {model_result.model_id}")
        md_lines.append("")
        
        # Metrics
        md_lines.append("**Metrics**:")
        md_lines.append(f"- Success Rate: {self._format_percentage(model_result.metrics.success_rate or 0)}")
        md_lines.append(f"- Accuracy: {self._format_percentage(model_result.metrics.accuracy or 0)}")
        md_lines.append(f"- Average Time: {model_result.metrics.average_time:.2f}s" if model_result.metrics.average_time is not None else "- Average Time: N/A")
        md_lines.append(f"- Total Tests: {model_result.metrics.total_tests}")
        md_lines.append(f"- Passed: {model_result.metrics.passed_tests}")
        md_lines.append(f"- Failed: {model_result.metrics.failed_tests}")
        md_lines.append(f"- Errors: {model_result.metrics.error_tests}")
        md_lines.append("")
        
        # Errors
        if model_result.errors:
            md_lines.append("**Errors**:")
            for error in model_result.errors:
                md_lines.append(f"- {error}")
            md_lines.append("")
        
        # Duration
        if model_result.duration:
            md_lines.append(f"**Duration**: {self._format_duration(model_result.duration)}")
            md_lines.append("")
        
        return md_lines
    
    def format_model_result(self, model_result: Any) -> str:
        """
        Format individual model result as Markdown
        
        Args:
            model_result: Model result to format
            
        Returns:
            Markdown model result string
        """
        if hasattr(model_result, 'model_name'):
            return "\n".join(self._format_model_result_md(model_result))
        else:
            return f"```\n{str(model_result)}\n```"
    
    def format_metrics(self, metrics: Any) -> str:
        """
        Format metrics as Markdown
        
        Args:
            metrics: Metrics to format
            
        Returns:
            Markdown metrics string
        """
        if hasattr(metrics, 'to_dict'):
            md_lines = []
            md_lines.append("## Metrics")
            md_lines.append("")
            for key, value in metrics.to_dict().items():
                if isinstance(value, float):
                    if 'rate' in key or 'accuracy' in key:
                        value_str = self._format_percentage(value)
                    else:
                        value_str = f"{value:.2f}"
                else:
                    value_str = str(value)
                md_lines.append(f"- **{key.replace('_', ' ').title()}**: {value_str}")
            md_lines.append("")
            return "\n".join(md_lines)
        else:
            return f"```\n{str(metrics)}\n```"