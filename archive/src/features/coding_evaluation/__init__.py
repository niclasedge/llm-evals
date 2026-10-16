"""
Coding Evaluation Feature

This module provides diverse coding evaluations that can be evaluated directly
in the interface and rendered in the browser for various programming languages.
"""

from .models import (
    TestCase,
    CodeSubmission,
    EvaluationResult,
    CodingProblem,
    ExecutionResult,
    TestResult,
    ProblemDifficulty,
    ProgrammingLanguage
)

from .evaluator import CodeEvaluator, EvaluationEngine
from .executor import CodeExecutor
from .service import CodingEvaluationService
from .endpoints import CodingEvaluationEndpoints

__all__ = [
    'TestCase',
    'CodeSubmission',
    'EvaluationResult',
    'CodingProblem',
    'ExecutionResult',
    'TestResult',
    'ProblemDifficulty',
    'ProgrammingLanguage',
    'CodeEvaluator',
    'EvaluationEngine',
    'CodeExecutor',
    'CodingEvaluationService',
    'CodingEvaluationEndpoints'
]