"""
Base formatter class for evaluation results

This module provides the base class for all result formatters.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..models import EvaluationResult


class BaseFormatter(ABC):
    """
    Base class for all evaluation result formatters
    
    This class defines the interface that all formatters must implement
    to provide consistent output formatting across different output types.
    """
    
    @abstractmethod
    def format_result(self, result: EvaluationResult) -> str:
        """
        Format evaluation result for output
        
        Args:
            result: Evaluation result to format
            
        Returns:
            Formatted string representation of the result
        """
        pass
    
    @abstractmethod
    def format_summary(self, result: EvaluationResult) -> str:
        """
        Format evaluation summary for output
        
        Args:
            result: Evaluation result to summarize
            
        Returns:
            Formatted summary string
        """
        pass
    
    def format_model_result(self, model_result: Any) -> str:
        """
        Format individual model result
        
        Args:
            model_result: Model result to format
            
        Returns:
            Formatted model result string
        """
        return str(model_result)
    
    def format_metrics(self, metrics: Any) -> str:
        """
        Format metrics for output
        
        Args:
            metrics: Metrics to format
            
        Returns:
            Formatted metrics string
        """
        return str(metrics)
    
    def _format_duration(self, duration: float) -> str:
        """Format duration in a human-readable format"""
        if duration < 60:
            return f"{duration:.1f}s"
        elif duration < 3600:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _format_percentage(self, value: float) -> str:
        """Format percentage value"""
        return f"{value * 100:.1f}%"
    
    def _truncate_text(self, text: str, max_length: int = 50) -> str:
        """Truncate text to maximum length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."