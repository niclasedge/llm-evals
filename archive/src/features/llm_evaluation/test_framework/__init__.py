"""
Test framework package for LLM evaluation based on Simon Willison's LLM CLI patterns.
"""

from .ollama_client import OllamaClient
from .llm_cli_client import LLMCLIClient
from .base_test import BaseTest
from .test_runner import TestRunner

__all__ = ['OllamaClient', 'LLMCLIClient', 'BaseTest', 'TestRunner']