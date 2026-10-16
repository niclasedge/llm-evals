"""
Console formatter for evaluation results

This module provides console formatting for evaluation results.
"""

from typing import Dict, Any
import textwrap

from .base_formatter import BaseFormatter
from ..models import EvaluationResult, ModelResult


class ConsoleFormatter(BaseFormatter):
    """
    Console formatter for evaluation results
    
    This formatter outputs evaluation results in a human-readable
    console format with colors and formatting for better readability.
    """
    
    def __init__(self):
        """Initialize the console formatter"""
        # Color codes for console output
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'magenta': '\033[95m'
        }
    
    def format_result(self, result: EvaluationResult) -> str:
        """
        Format evaluation result for console output
        
        Args:
            result: Evaluation result to format
            
        Returns:
            Console-formatted string representation of the result
        """
        lines = []
        
        # Title
        lines.append(self._format_title(f"{result.evaluation_type.value.title()} Evaluation Results"))
        lines.append("")
        
        # Summary section
        lines.append(self._format_section_header("Summary"))
        lines.append(f"Evaluation Type: {self._colorize(result.evaluation_type.value, 'cyan')}")
        lines.append(f"Models Evaluated: {self._colorize(str(len(result.model_results)), 'yellow')}")
        lines.append(f"Total Duration: {self._colorize(self._format_duration(result.duration), 'green')}")
        lines.append(f"Started: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Completed: {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overall metrics
        avg_metrics = result.get_average_metrics()
        lines.append(self._format_section_header("Overall Metrics"))
        
        success_rate = avg_metrics.success_rate or 0
        accuracy = avg_metrics.accuracy or 0
        
        lines.append(f"Success Rate: {self._colorize_percentage(success_rate)}")
        lines.append(f"Accuracy: {self._colorize_percentage(accuracy)}")
        lines.append(f"Average Time: {self._colorize(f'{avg_metrics.average_time:.2f}s', 'blue')}")
        lines.append("")
        
        # Test summary
        lines.append(self._format_section_header("Test Summary"))
        lines.append(f"Total Tests: {self._colorize(str(avg_metrics.total_tests), 'cyan')}")
        lines.append(f"Passed: {self._colorize(str(avg_metrics.passed_tests), 'green')}")
        lines.append(f"Failed: {self._colorize(str(avg_metrics.failed_tests), 'red')}")
        lines.append(f"Errors: {self._colorize(str(avg_metrics.error_tests), 'red')}")
        lines.append("")
        
        # Best model
        best_model = result.get_best_model()
        if best_model:
            lines.append(self._format_section_header("Best Performing Model"))
            lines.append(f"Model: {self._colorize(best_model.model_name, 'green')} ({best_model.provider})")
            lines.append(f"Success Rate: {self._colorize_percentage(best_model.metrics.success_rate or 0)}")
            lines.append(f"Duration: {self._colorize(self._format_duration(best_model.duration or 0), 'blue')}")
            lines.append("")
        
        # Model results
        lines.append(self._format_section_header("Model Results"))
        
        for i, model_result in enumerate(result.model_results):
            if i > 0:
                lines.append("")
            lines.extend(self._format_model_result_console(model_result))
        
        return "\n".join(lines)
    
    def format_summary(self, result: EvaluationResult) -> str:
        """
        Format evaluation summary for console output
        
        Args:
            result: Evaluation result to summarize
            
        Returns:
            Console-formatted summary string
        """
        lines = []
        
        # Title
        lines.append(self._format_title(f"{result.evaluation_type.value.title()} Evaluation Summary"))
        lines.append("")
        
        # Key metrics
        avg_metrics = result.get_average_metrics()
        success_rate = avg_metrics.success_rate or 0
        
        lines.append(f"🔍 Models Evaluated: {self._colorize(str(len(result.model_results)), 'yellow')}")
        lines.append(f"📊 Overall Success Rate: {self._colorize_percentage(success_rate)}")
        lines.append(f"⏱️  Total Duration: {self._colorize(self._format_duration(result.duration), 'green')}")
        lines.append("")
        
        # Best model
        best_model = result.get_best_model()
        if best_model:
            lines.append(f"🏆 Best Model: {self._colorize(best_model.model_name, 'green')} ({self._colorize_percentage(best_model.metrics.success_rate or 0)})")
            lines.append("")
        
        # Quick stats
        lines.append(f"✅ Passed: {self._colorize(str(avg_metrics.passed_tests), 'green')}")
        lines.append(f"❌ Failed: {self._colorize(str(avg_metrics.failed_tests), 'red')}")
        lines.append(f"⚠️  Errors: {self._colorize(str(avg_metrics.error_tests), 'red')}")
        
        return "\n".join(lines)
    
    def _format_model_result_console(self, model_result: ModelResult) -> list:
        """Format individual model result for console"""
        lines = []
        
        # Model header
        model_name = f"{model_result.model_name} ({model_result.provider})"
        lines.append(self._colorize(model_name, 'bold'))
        lines.append("─" * len(model_name))
        
        # Metrics
        success_rate = model_result.metrics.success_rate or 0
        accuracy = model_result.metrics.accuracy or 0
        
        lines.append(f"Success Rate: {self._colorize_percentage(success_rate)}")
        lines.append(f"Accuracy: {self._colorize_percentage(accuracy)}")
        lines.append(f"Average Time: {self._colorize(f'{model_result.metrics.average_time:.2f}s', 'blue')}")
        
        # Test breakdown
        lines.append(f"Tests: {model_result.metrics.total_tests} total, " +
                    f"{self._colorize(str(model_result.metrics.passed_tests), 'green')} passed, " +
                    f"{self._colorize(str(model_result.metrics.failed_tests), 'red')} failed")
        
        # Duration
        if model_result.duration:
            lines.append(f"Duration: {self._colorize(self._format_duration(model_result.duration), 'blue')}")
        
        # Errors
        if model_result.errors:
            lines.append(f"Errors: {self._colorize(str(len(model_result.errors)), 'red')}")
            for error in model_result.errors[:3]:  # Show first 3 errors
                lines.append(f"  • {self._truncate_text(error, 60)}")
            if len(model_result.errors) > 3:
                lines.append(f"  ... and {len(model_result.errors) - 3} more")
        
        return lines
    
    def format_model_result(self, model_result: Any) -> str:
        """
        Format individual model result for console
        
        Args:
            model_result: Model result to format
            
        Returns:
            Console-formatted model result string
        """
        if hasattr(model_result, 'model_name'):
            return "\n".join(self._format_model_result_console(model_result))
        else:
            return str(model_result)
    
    def format_metrics(self, metrics: Any) -> str:
        """
        Format metrics for console output
        
        Args:
            metrics: Metrics to format
            
        Returns:
            Console-formatted metrics string
        """
        if hasattr(metrics, 'to_dict'):
            lines = []
            lines.append(self._format_section_header("Metrics"))
            
            for key, value in metrics.to_dict().items():
                if isinstance(value, float):
                    if 'rate' in key or 'accuracy' in key:
                        value_str = self._colorize_percentage(value)
                    else:
                        value_str = self._colorize(f"{value:.2f}", 'blue')
                else:
                    value_str = self._colorize(str(value), 'yellow')
                
                key_formatted = key.replace('_', ' ').title()
                lines.append(f"{key_formatted}: {value_str}")
            
            return "\n".join(lines)
        else:
            return str(metrics)
    
    def _format_title(self, title: str) -> str:
        """Format title with decorative border"""
        border = "═" * len(title)
        return f"{self._colorize(border, 'cyan')}\n{self._colorize(title, 'bold')}\n{self._colorize(border, 'cyan')}"
    
    def _format_section_header(self, header: str) -> str:
        """Format section header"""
        return f"{self._colorize(header, 'bold')}\n{self._colorize('─' * len(header), 'cyan')}"
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        if color in self.colors:
            return f"{self.colors[color]}{text}{self.colors['reset']}"
        return text
    
    def _colorize_percentage(self, value: float) -> str:
        """Colorize percentage based on value"""
        percentage = self._format_percentage(value)
        
        if value >= 0.8:
            return self._colorize(percentage, 'green')
        elif value >= 0.6:
            return self._colorize(percentage, 'yellow')
        else:
            return self._colorize(percentage, 'red')
    
    def format_progress(self, current: int, total: int, model: str, message: str) -> str:
        """Format progress indicator"""
        percentage = (current / total) * 100 if total > 0 else 0
        progress_bar = self._create_progress_bar(percentage)
        
        return f"{progress_bar} [{current}/{total}] {self._colorize(model, 'cyan')}: {message}"
    
    def _create_progress_bar(self, percentage: float, width: int = 30) -> str:
        """Create a progress bar"""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"{self._colorize(bar, 'green')} {percentage:5.1f}%"