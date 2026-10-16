"""
Unified Evaluation Feature

This module provides a unified CLI interface for all evaluation types,
consolidating coding, vision, tool calls, and intelligence evaluations
into a single command-line interface.
"""

from .models import (
    EvaluationRequest,
    EvaluationResult,
    ModelSelection,
    OutputConfig,
    EvaluationType
)
from .service import EvaluationService
from .cli import main as cli_main

__all__ = [
    'EvaluationRequest',
    'EvaluationResult', 
    'ModelSelection',
    'OutputConfig',
    'EvaluationType',
    'EvaluationService',
    'cli_main'
]