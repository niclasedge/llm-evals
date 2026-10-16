"""
Base test class for LLM evaluation framework.
Provides common interface and utilities for all test implementations.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from enum import Enum


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestResult:
    """Container for test results."""
    
    def __init__(self, test_name: str, status: TestStatus, 
                 score: Optional[float] = None, 
                 details: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None,
                 execution_time: Optional[float] = None):
        self.test_name = test_name
        self.status = status
        self.score = score
        self.details = details or {}
        self.error = error
        self.execution_time = execution_time
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'test_name': self.test_name,
            'status': self.status.value,
            'score': self.score,
            'details': self.details,
            'error': self.error,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp
        }
    
    def __str__(self) -> str:
        status_emoji = {
            TestStatus.PASSED: "✓",
            TestStatus.FAILED: "✗",
            TestStatus.SKIPPED: "⊝",
            TestStatus.ERROR: "⚠",
            TestStatus.RUNNING: "⟳",
            TestStatus.PENDING: "○"
        }
        emoji = status_emoji.get(self.status, "?")
        score_str = f" ({self.score:.2f})" if self.score is not None else ""
        time_str = f" [{self.execution_time:.2f}s]" if self.execution_time else ""
        return f"{emoji} {self.test_name}{score_str}{time_str}"


class BaseTest(ABC):
    """Base class for all LLM evaluation tests."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any]):
        self.name = name
        self.description = description
        self.config = config
        self.results: List[TestResult] = []
        self.setup_done = False
        self.teardown_done = False
    
    @abstractmethod
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """
        Execute the test.
        
        Args:
            client: The LLM client (OllamaClient, LLMCLIClient, etc.)
            model: Model identifier to test
            **kwargs: Additional test parameters
        
        Returns:
            TestResult: Result of the test execution
        """
        pass
    
    async def setup(self) -> bool:
        """
        Setup test environment.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        self.setup_done = True
        return True
    
    async def teardown(self) -> bool:
        """
        Cleanup after test.
        
        Returns:
            bool: True if teardown successful, False otherwise
        """
        self.teardown_done = True
        return True
    
    def validate_result(self, result: Any) -> bool:
        """
        Validate test result.
        
        Args:
            result: Raw result from LLM
        
        Returns:
            bool: True if result is valid, False otherwise
        """
        return result is not None
    
    def calculate_score(self, result: Any, expected: Any = None) -> float:
        """
        Calculate test score.
        
        Args:
            result: Actual result
            expected: Expected result (optional)
        
        Returns:
            float: Score between 0.0 and 1.0
        """
        if not self.validate_result(result):
            return 0.0
        return 1.0
    
    def get_test_prompt(self) -> str:
        """Get the test prompt."""
        return self.config.get('prompt', '')
    
    def get_system_prompt(self) -> Optional[str]:
        """Get the system prompt."""
        return self.config.get('system_prompt')
    
    def get_expected_result(self) -> Any:
        """Get expected result if available."""
        return self.config.get('expected_result')
    
    def get_validation_criteria(self) -> Dict[str, Any]:
        """Get validation criteria."""
        return self.config.get('validation', {})
    
    async def run_with_timing(self, client: Any, model: str, **kwargs) -> TestResult:
        """
        Execute test with timing and error handling.
        
        Args:
            client: The LLM client
            model: Model identifier
            **kwargs: Additional parameters
        
        Returns:
            TestResult: Complete test result with timing
        """
        start_time = time.time()
        
        try:
            # Setup if not already done
            if not self.setup_done:
                setup_success = await self.setup()
                if not setup_success:
                    return TestResult(
                        test_name=self.name,
                        status=TestStatus.ERROR,
                        error="Setup failed",
                        execution_time=time.time() - start_time
                    )
            
            # Run the actual test
            result = await self.run(client, model, **kwargs)
            result.execution_time = time.time() - start_time
            
            # Store result
            self.results.append(result)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_result = TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error=str(e),
                execution_time=execution_time
            )
            self.results.append(error_result)
            return error_result
        
        finally:
            # Teardown if not already done
            if not self.teardown_done:
                await self.teardown()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics."""
        if not self.results:
            return {
                'total_runs': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'skipped': 0,
                'average_score': 0.0,
                'average_time': 0.0
            }
        
        status_counts = {}
        scores = []
        times = []
        
        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
            if result.score is not None:
                scores.append(result.score)
            if result.execution_time is not None:
                times.append(result.execution_time)
        
        return {
            'total_runs': len(self.results),
            'passed': status_counts.get(TestStatus.PASSED, 0),
            'failed': status_counts.get(TestStatus.FAILED, 0),
            'errors': status_counts.get(TestStatus.ERROR, 0),
            'skipped': status_counts.get(TestStatus.SKIPPED, 0),
            'average_score': sum(scores) / len(scores) if scores else 0.0,
            'average_time': sum(times) / len(times) if times else 0.0
        }


class TextGenerationTest(BaseTest):
    """Simple text generation test implementation."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run text generation test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
        # Handle different client types
        if hasattr(client, 'generate'):
            # Ollama client
            response = await client.generate(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt
            )
            text_response = response.get('response', '') if response else ''
            
        elif hasattr(client, 'run_prompt'):
            # LLM CLI client
            response = await client.run_prompt(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt
            )
            text_response = response.get('response', '') if response else ''
            
        else:
            # PydanticAI agent or other
            try:
                from ..llm_service import run_query
                response = await run_query(client, prompt)
                text_response = str(response) if response else ''
            except Exception as e:
                return TestResult(
                    test_name=self.name,
                    status=TestStatus.ERROR,
                    error=f"Unsupported client type: {type(client)}"
                )
        
        # Validate and score
        is_valid = self.validate_result(text_response)
        score = self.calculate_score(text_response)
        
        status = TestStatus.PASSED if is_valid and score > 0.5 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': text_response,
                'response_length': len(text_response),
                'model': model
            }
        )
    
    def validate_result(self, result: str) -> bool:
        """Validate text generation result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check minimum length
        min_length = self.config.get('min_length', 10)
        if len(result.strip()) < min_length:
            return False
        
        # Check if it's not just repeated text
        words = result.split()
        if len(set(words)) < len(words) * 0.5:  # Less than 50% unique words
            return False
        
        return True
    
    def calculate_score(self, result: str) -> float:
        """Calculate score based on response quality."""
        if not self.validate_result(result):
            return 0.0
        
        score = 1.0
        
        # Length factor
        expected_length = self.config.get('expected_length', 100)
        actual_length = len(result)
        length_ratio = min(actual_length / expected_length, 1.0)
        score *= length_ratio
        
        # Diversity factor
        words = result.split()
        unique_words = len(set(words))
        diversity_ratio = unique_words / len(words) if words else 0
        score *= diversity_ratio
        
        return min(score, 1.0)