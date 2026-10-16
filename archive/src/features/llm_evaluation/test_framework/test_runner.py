"""
Test runner for LLM evaluation framework.
Orchestrates test execution across multiple models and clients.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from .base_test import BaseTest, TestResult, TestStatus
from .ollama_client import OllamaClient
from .llm_cli_client import LLMCLIClient
from .mock_client import MockLLMClient, MockAgent
from .. import config
from ..llm_service import get_llm_agent


class TestRunner:
    """Orchestrates test execution across multiple models and clients."""
    
    def __init__(self, test_config: Dict[str, Any]):
        self.config = test_config
        self.ollama_client = None
        self.llm_cli_client = None
        self.mock_client = None
        self.use_mock_mode = False
        self.test_results: List[TestResult] = []
        self.execution_summary = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Check if real APIs are available
        apis_available = await self._check_api_availability()
        
        if not apis_available:
            print("🎭 No API keys found, using mock mode for testing framework functionality")
            self.use_mock_mode = True
            self.mock_client = MockLLMClient()
        else:
            print("🔑 API keys found, using real LLM services")
        
        # Initialize clients
        if config.ENABLE_OLLAMA:
            self.ollama_client = OllamaClient()
            await self.ollama_client.__aenter__()
        
        self.llm_cli_client = LLMCLIClient()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.ollama_client:
            await self.ollama_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _check_api_availability(self) -> bool:
        """Check if real API services are available."""
        # Check for OpenRouter API key
        if config.ENABLE_OPENROUTER and config.OPENROUTER_API_KEY:
            return True
        
        # Check for Ollama availability
        if config.ENABLE_OLLAMA:
            try:
                from aiohttp import ClientSession
                async with ClientSession() as session:
                    async with session.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=2) as response:
                        if response.status == 200:
                            return True
            except:
                pass
        
        # Check for LLM CLI with API keys
        import os
        if os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'):
            return True
        
        return False
    
    def discover_tests(self, test_directory: Optional[Path] = None) -> List[BaseTest]:
        """
        Discover available tests.
        
        Args:
            test_directory: Directory to search for tests
        
        Returns:
            List[BaseTest]: List of discovered tests
        """
        tests = []
        
        # For now, return hardcoded tests based on config
        # In a real implementation, this would scan directories for test files
        
        if 'tests' in self.config:
            for test_config in self.config['tests']:
                test_name = test_config.get('name', 'unnamed_test')
                test_type = test_config.get('type', 'TextGenerationTest')
                test_description = test_config.get('description', f'Test: {test_name}')
                
                # Create test instance based on type
                if test_type == 'TextGenerationTest':
                    from .base_test import TextGenerationTest
                    test = TextGenerationTest(test_name, test_description, test_config)
                else:
                    # Default to TextGenerationTest for now
                    from .base_test import TextGenerationTest
                    test = TextGenerationTest(test_name, test_description, test_config)
                
                tests.append(test)
        
        return tests
    
    async def run_single_test(self, test: BaseTest, client: Any, model: str, 
                             client_type: str) -> TestResult:
        """
        Run a single test with a specific client and model.
        
        Args:
            test: Test to run
            client: LLM client
            model: Model identifier
            client_type: Type of client ('ollama', 'llm_cli', 'pydantic_ai')
        
        Returns:
            TestResult: Test execution result
        """
        print(f"Running test '{test.name}' with {client_type} model '{model}'")
        
        try:
            result = await test.run_with_timing(client, model)
            result.details['client_type'] = client_type
            return result
        except Exception as e:
            return TestResult(
                test_name=test.name,
                status=TestStatus.ERROR,
                error=f"Test execution failed: {str(e)}",
                details={'client_type': client_type, 'model': model}
            )
    
    async def run_test_suite(self, test_names: Optional[List[str]] = None,
                            models: Optional[List[str]] = None,
                            clients: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run specified tests or all tests.
        
        Args:
            test_names: List of test names to run (None for all)
            models: List of models to test (None for all configured)
            clients: List of clients to use (None for all available)
        
        Returns:
            Dict[str, Any]: Test execution results and summary
        """
        start_time = time.time()
        
        # Discover tests
        all_tests = self.discover_tests()
        
        # Filter tests if specified
        if test_names:
            tests_to_run = [t for t in all_tests if t.name in test_names]
        else:
            tests_to_run = all_tests
        
        print(f"Running {len(tests_to_run)} tests...")
        
        results = []
        
        # Run tests with different clients
        for test in tests_to_run:
            print(f"\n--- Running test: {test.name} ---")
            
            if self.use_mock_mode:
                # Use mock client for all test types
                mock_models = ['mock-gpt-4o', 'mock-claude-3.5-sonnet', 'mock-llama-3']
                test_models = models or mock_models[:1]  # Only use one model in mock mode
                
                for model in test_models:
                    result = await self.run_single_test(
                        test, self.mock_client, model, 'mock'
                    )
                    results.append(result)
            else:
                # Test with Ollama if enabled
                if (clients is None or 'ollama' in clients) and config.ENABLE_OLLAMA:
                    if self.ollama_client:
                        # Check if Ollama is available
                        is_healthy = await self.ollama_client.health_check()
                        if is_healthy:
                            ollama_models = models or config.OLLAMA_MODELS_TO_TEST
                            for model in ollama_models:
                                result = await self.run_single_test(
                                    test, self.ollama_client, model, 'ollama'
                                )
                                results.append(result)
                        else:
                            print("Ollama server not available, skipping Ollama tests")
                
                # Test with LLM CLI if available
                if (clients is None or 'llm_cli' in clients) and self.llm_cli_client and self.llm_cli_client.is_available():
                    try:
                        cli_models = await self.llm_cli_client.list_models()
                        if models:
                            cli_models = [m for m in cli_models if m in models]
                        
                        for model in cli_models[:3]:  # Limit to first 3 models
                            result = await self.run_single_test(
                                test, self.llm_cli_client, model, 'llm_cli'
                            )
                            results.append(result)
                    except Exception as e:
                        print(f"LLM CLI error: {e}")
                else:
                    if clients is None or 'llm_cli' in clients:
                        print("LLM CLI not available, skipping LLM CLI tests")
                
                # Test with PydanticAI (OpenRouter) if enabled
                if (clients is None or 'pydantic_ai' in clients) and config.ENABLE_OPENROUTER:
                    if config.OPENROUTER_API_KEY:
                        openrouter_models = models or config.OPENROUTER_MODELS_TO_TEST
                        for model in openrouter_models:
                            agent = get_llm_agent("openrouter", model, test.get_system_prompt())
                            if agent:
                                result = await self.run_single_test(
                                    test, agent, model, 'pydantic_ai'
                                )
                                results.append(result)
        
        # Store results
        self.test_results.extend(results)
        
        # Generate summary
        end_time = time.time()
        summary = self.generate_summary(results, end_time - start_time)
        
        return {
            'results': [r.to_dict() for r in results],
            'summary': summary,
            'execution_time': end_time - start_time
        }
    
    def generate_summary(self, results: List[TestResult], execution_time: float) -> Dict[str, Any]:
        """
        Generate test execution summary.
        
        Args:
            results: List of test results
            execution_time: Total execution time
        
        Returns:
            Dict[str, Any]: Summary statistics
        """
        if not results:
            return {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'skipped': 0,
                'success_rate': 0.0,
                'average_score': 0.0,
                'execution_time': execution_time
            }
        
        status_counts = {}
        scores = []
        
        for result in results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
            if result.score is not None:
                scores.append(result.score)
        
        passed = status_counts.get(TestStatus.PASSED, 0)
        total = len(results)
        
        summary = {
            'total_tests': total,
            'passed': passed,
            'failed': status_counts.get(TestStatus.FAILED, 0),
            'errors': status_counts.get(TestStatus.ERROR, 0),
            'skipped': status_counts.get(TestStatus.SKIPPED, 0),
            'success_rate': passed / total if total > 0 else 0.0,
            'average_score': sum(scores) / len(scores) if scores else 0.0,
            'execution_time': execution_time
        }
        
        return summary
    
    def generate_report(self, results: Dict[str, Any], 
                       output_file: Optional[Path] = None) -> str:
        """
        Generate detailed test report.
        
        Args:
            results: Test results from run_test_suite
            output_file: Optional file to write report to
        
        Returns:
            str: Formatted report
        """
        summary = results['summary']
        test_results = results['results']
        
        # Generate report
        report = []
        report.append("# LLM Evaluation Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("## Summary")
        report.append(f"- Total Tests: {summary['total_tests']}")
        report.append(f"- Passed: {summary['passed']}")
        report.append(f"- Failed: {summary['failed']}")
        report.append(f"- Errors: {summary['errors']}")
        report.append(f"- Success Rate: {summary['success_rate']:.1%}")
        report.append(f"- Average Score: {summary['average_score']:.2f}")
        report.append(f"- Execution Time: {summary['execution_time']:.2f}s")
        report.append("")
        
        # Individual test results
        report.append("## Test Results")
        for result in test_results:
            status_emoji = {
                'passed': "✓",
                'failed': "✗",
                'error': "⚠",
                'skipped': "⊝"
            }.get(result['status'], "?")
            
            report.append(f"### {status_emoji} {result['test_name']}")
            report.append(f"- Status: {result['status']}")
            report.append(f"- Model: {result['details'].get('model', 'Unknown')}")
            report.append(f"- Client: {result['details'].get('client_type', 'Unknown')}")
            
            if result['score'] is not None:
                report.append(f"- Score: {result['score']:.2f}")
            
            if result['execution_time'] is not None:
                report.append(f"- Execution Time: {result['execution_time']:.2f}s")
            
            if result['error']:
                report.append(f"- Error: {result['error']}")
            
            report.append("")
        
        report_text = "\n".join(report)
        
        # Write to file if specified
        if output_file:
            output_file.write_text(report_text)
            print(f"Report saved to: {output_file}")
        
        return report_text
    
    def save_results(self, results: Dict[str, Any], output_file: Path):
        """
        Save test results to JSON file.
        
        Args:
            results: Test results from run_test_suite
            output_file: Path to output file
        """
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results saved to: {output_file}")


# Example usage
async def main():
    """Example usage of the test runner."""
    # Sample test configuration
    test_config = {
        'name': 'Standard LLM Evaluation',
        'version': '1.0',
        'tests': [
            {
                'name': 'basic_text_generation',
                'type': 'TextGenerationTest',
                'description': 'Basic text generation test',
                'prompt': 'Write a short story about a robot learning to paint.',
                'system_prompt': 'You are a creative writing assistant.',
                'expected_length': 200,
                'min_length': 50
            },
            {
                'name': 'question_answering',
                'type': 'TextGenerationTest',
                'description': 'Question answering test',
                'prompt': 'What is the capital of France and why is it important?',
                'system_prompt': 'You are a helpful educational assistant.',
                'expected_length': 100,
                'min_length': 30
            }
        ]
    }
    
    async with TestRunner(test_config) as runner:
        print("Running test suite...")
        results = await runner.run_test_suite()
        
        # Generate report
        report = runner.generate_report(results)
        print(report)
        
        # Save results
        runner.save_results(results, Path("test_results.json"))


if __name__ == "__main__":
    asyncio.run(main())