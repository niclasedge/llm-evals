"""
JSON formatter for evaluation results

This module provides JSON formatting for evaluation results.
"""

import json
from typing import Dict, Any

from .base_formatter import BaseFormatter
from ..models import EvaluationResult


class JSONFormatter(BaseFormatter):
    """
    JSON formatter for evaluation results
    
    This formatter outputs evaluation results in JSON format,
    suitable for programmatic consumption and API responses.
    """
    
    def format_result(self, result: EvaluationResult) -> str:
        """
        Format evaluation result as JSON
        
        Args:
            result: Evaluation result to format
            
        Returns:
            JSON string representation of the result
        """
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    
    def format_summary(self, result: EvaluationResult) -> str:
        """
        Format evaluation summary as JSON
        
        Args:
            result: Evaluation result to summarize
            
        Returns:
            JSON summary string
        """
        summary_data = {
            "evaluation_type": result.evaluation_type.value,
            "total_models": len(result.model_results),
            "duration": result.duration,
            "summary": result.summary,
            "average_metrics": result.get_average_metrics().to_dict(),
            "best_model": result.get_best_model().to_dict() if result.get_best_model() else None
        }
        
        return json.dumps(summary_data, indent=2, ensure_ascii=False)
    
    def format_model_result(self, model_result: Any) -> str:
        """
        Format individual model result as JSON
        
        Args:
            model_result: Model result to format
            
        Returns:
            JSON model result string
        """
        if hasattr(model_result, 'to_dict'):
            return json.dumps(model_result.to_dict(), indent=2, ensure_ascii=False)
        else:
            return json.dumps(model_result, indent=2, ensure_ascii=False)
    
    def format_metrics(self, metrics: Any) -> str:
        """
        Format metrics as JSON
        
        Args:
            metrics: Metrics to format
            
        Returns:
            JSON metrics string
        """
        if hasattr(metrics, 'to_dict'):
            return json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False)
        else:
            return json.dumps(metrics, indent=2, ensure_ascii=False)