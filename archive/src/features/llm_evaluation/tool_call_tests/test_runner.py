"""
Test runner for executing tool call evaluations.
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import json

from .test_scenarios import ToolCallTestCase, ScenarioGroup, ToolCallScenarioFactory
from .scoring_engine import ToolCallScorer, ToolCallResult, ScoringConfig
from .tool_definitions import ToolRegistry, default_registry


class ToolCallTestRunner:
    """Main test runner for tool call evaluations."""
    
    def __init__(self, config: ScoringConfig = None, tool_registry: ToolRegistry = None):
        self.config = config or ScoringConfig.default()
        self.scorer = ToolCallScorer(self.config)
        self.registry = tool_registry or default_registry
        self.results: List[ToolCallResult] = []
    
    async def run_single_test(self, test_case: ToolCallTestCase, 
                            agent, timeout: int = 30) -> ToolCallResult:
        """Run a single test case."""
        start_time = time.time()
        error_message = None
        response = ""
        
        try:
            # Run the test with timeout
            response_task = asyncio.create_task(
                self._execute_test(agent, test_case)
            )
            response = await asyncio.wait_for(response_task, timeout=timeout)
            
        except asyncio.TimeoutError:
            error_message = f"Test timed out after {timeout} seconds"
            response = "Test timed out"
        except Exception as e:
            error_message = f"Test execution error: {str(e)}"
            response = f"Error: {str(e)}"
        
        execution_time = time.time() - start_time
        
        # Score the result
        result = self.scorer.score_tool_call_result(
            test_case, response, execution_time, error_message
        )
        
        return result
    
    async def run_test_suite(self, test_cases: List[ToolCallTestCase], 
                           agent, max_concurrent: int = 3) -> Dict[str, Any]:
        """Run a suite of test cases."""
        print(f"Running {len(test_cases)} tool call tests...")
        
        # Create semaphore to limit concurrent tests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(test_case):
            async with semaphore:
                return await self.run_single_test(test_case, agent)
        
        # Run tests concurrently
        tasks = [run_with_semaphore(test_case) for test_case in test_cases]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and collect valid results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Test {test_cases[i].name} failed with exception: {result}")
                # Create a failed result
                failed_result = ToolCallResult(
                    test_case=test_cases[i],
                    response=f"Exception: {str(result)}",
                    extracted_tool_calls=[],
                    scores={dim: 0.0 for dim in self.scorer.config.weights.keys()},
                    overall_score=0.0,
                    passed=False,
                    execution_time=0.0,
                    error_message=str(result)
                )
                valid_results.append(failed_result)
            else:
                valid_results.append(result)
        
        self.results.extend(valid_results)
        
        # Calculate final scores
        final_scores = self.scorer.calculate_final_score(valid_results)
        
        return {
            "results": valid_results,
            "summary": final_scores,
            "timestamp": datetime.now().isoformat(),
            "test_count": len(test_cases),
            "config": {
                "weights": {dim.value: weight for dim, weight in self.config.weights.items()},
                "thresholds": self.config.thresholds
            }
        }
    
    async def run_scenario_group(self, group: ScenarioGroup, 
                               agent, max_concurrent: int = 3) -> Dict[str, Any]:
        """Run all tests in a scenario group."""
        print(f"Running scenario group: {group.name}")
        return await self.run_test_suite(group.get_test_cases(), agent, max_concurrent)
    
    async def run_all_scenarios(self, agent, max_concurrent: int = 3) -> Dict[str, Any]:
        """Run all predefined scenarios."""
        all_scenarios = ToolCallScenarioFactory.get_all_scenarios()
        return await self.run_test_suite(all_scenarios, agent, max_concurrent)
    
    async def _execute_test(self, agent, test_case: ToolCallTestCase) -> str:
        """Execute a single test case with the agent."""
        # For now, we'll use a mock response since we need to integrate with the actual LLM
        # This will be replaced with actual agent.run(test_case.prompt) when integrated
        
        # Mock response based on test case
        if "mock" in str(type(agent)).lower():
            return self._generate_mock_response(test_case)
        
        # Actual agent execution
        try:
            result = await agent.run(test_case.prompt)
            
            # Handle different response types
            if hasattr(result, 'output'):
                return str(result.output)
            elif hasattr(result, 'data'):
                return str(result.data)
            else:
                return str(result)
        except Exception as e:
            raise Exception(f"Agent execution failed: {str(e)}")
    
    def _generate_mock_response(self, test_case: ToolCallTestCase) -> str:
        """Generate a mock response for testing purposes."""
        if not test_case.expected_tools:
            return "I understand your request."
        
        # Generate a response that includes the expected tool calls in JSON format
        responses = []
        
        for expected_tool in test_case.expected_tools:
            tool_name = expected_tool.tool_name
            params = expected_tool.parameters
            
            # Create a properly formatted tool call that the parser can extract
            tool_call_json = {
                "tool_name": tool_name,
                "parameters": params
            }
            
            # Generate a realistic response with embedded JSON
            if tool_name == "calculator":
                op = params.get("operation", "")
                values = params.get("values", [])
                responses.append(f"I'll calculate {op} of {values} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "weather_api":
                location = params.get("location", "")
                responses.append(f"Let me get the weather for {location} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "unit_converter":
                value = params.get("value", 0)
                from_unit = params.get("from_unit", "")
                to_unit = params.get("to_unit", "")
                responses.append(f"Converting {value} {from_unit} to {to_unit} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "text_formatter":
                text = params.get("text", "")
                operation = params.get("operation", "")
                responses.append(f"Formatting '{text}' with {operation} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "datetime_tool":
                operation = params.get("operation", "")
                responses.append(f"Performing {operation} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "json_processor":
                operation = params.get("operation", "")
                responses.append(f"Processing JSON with {operation} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "file_operations":
                operation = params.get("operation", "")
                file_path = params.get("file_path", "")
                responses.append(f"Performing {operation} on {file_path} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "email_tool":
                operation = params.get("operation", "")
                to = params.get("to", "")
                responses.append(f"Performing email {operation} to {to} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "database_tool":
                operation = params.get("operation", "")
                table = params.get("table", "")
                responses.append(f"Performing database {operation} on {table} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "web_scraper":
                url = params.get("url", "")
                operation = params.get("operation", "")
                responses.append(f"Performing web scraping {operation} on {url} using {json.dumps(tool_call_json)}")
            
            elif tool_name == "api_client":
                url = params.get("url", "")
                method = params.get("method", "")
                responses.append(f"Making {method} request to {url} using {json.dumps(tool_call_json)}")
            
            else:
                responses.append(f"Using {tool_name} with {json.dumps(tool_call_json)}")
        
        return ". ".join(responses) + "."
    
    def generate_report(self, results: Dict[str, Any], output_file: Path = None) -> str:
        """Generate a detailed test report."""
        summary = results["summary"]
        test_results = results["results"]
        
        report_lines = [
            "# Tool Call Test Report",
            f"**Generated:** {results['timestamp']}",
            f"**Total Tests:** {summary['total_tests']}",
            f"**Overall Score:** {summary['overall_score']:.2%}",
            f"**Classification:** {summary['classification'].title()}",
            f"**Success Rate:** {summary['success_rate']:.2%}",
            f"**Average Execution Time:** {summary['average_execution_time']:.2f}s",
            "",
            "## Score Breakdown",
            ""
        ]
        
        # Add dimension scores
        for dimension, score in summary["dimension_scores"].items():
            report_lines.append(f"- **{dimension.replace('_', ' ').title()}:** {score:.2%}")
        
        report_lines.extend([
            "",
            "## Test Results",
            ""
        ])
        
        # Add individual test results
        for result in test_results:
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            report_lines.extend([
                f"### {result.test_case.name} {status}",
                f"**Score:** {result.overall_score:.2%}",
                f"**Difficulty:** {result.test_case.difficulty.value}",
                f"**Execution Time:** {result.execution_time:.2f}s",
                ""
            ])
            
            if result.error_message:
                report_lines.extend([
                    f"**Error:** {result.error_message}",
                    ""
                ])
            
            # Add extracted tool calls
            if result.extracted_tool_calls:
                report_lines.append("**Extracted Tool Calls:**")
                for call in result.extracted_tool_calls:
                    report_lines.append(f"- {call.get('tool_name', 'Unknown')}: {call.get('parameters', {})}")
                report_lines.append("")
            
            # Add response excerpt
            response_excerpt = result.response[:200] + "..." if len(result.response) > 200 else result.response
            report_lines.extend([
                "**Response:**",
                f"```",
                response_excerpt,
                f"```",
                ""
            ])
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report_content)
        
        return report_content
    
    def save_results(self, results: Dict[str, Any], output_file: Path):
        """Save detailed results to JSON file."""
        # Convert results to JSON-serializable format
        serializable_results = {
            "timestamp": results["timestamp"],
            "test_count": results["test_count"],
            "summary": results["summary"],
            "config": results["config"],
            "results": []
        }
        
        for result in results["results"]:
            serializable_result = {
                "test_case": {
                    "name": result.test_case.name,
                    "description": result.test_case.description,
                    "prompt": result.test_case.prompt,
                    "difficulty": result.test_case.difficulty.value,
                    "scoring_weight": result.test_case.scoring_weight
                },
                "response": result.response,
                "extracted_tool_calls": result.extracted_tool_calls,
                "scores": {dim.value: score for dim, score in result.scores.items()},
                "overall_score": result.overall_score,
                "passed": result.passed,
                "execution_time": result.execution_time,
                "error_message": result.error_message
            }
            serializable_results["results"].append(serializable_result)
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of test results."""
        summary = results["summary"]
        
        print("\n" + "="*60)
        print("TOOL CALL TEST SUMMARY")
        print("="*60)
        print(f"Overall Score: {summary['overall_score']:.2%} ({summary['classification'].title()})")
        print(f"Tests Passed: {summary['passed_tests']}/{summary['total_tests']} ({summary['success_rate']:.1%})")
        print(f"Average Execution Time: {summary['average_execution_time']:.2f}s")
        print("\nDimension Scores:")
        
        for dimension, score in summary["dimension_scores"].items():
            print(f"  {dimension.replace('_', ' ').title()}: {score:.2%}")
        
        print("="*60)