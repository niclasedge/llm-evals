"""
Test scenarios for evaluating LLM tool calling capabilities.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class TestDifficulty(Enum):
    """Test difficulty levels."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class ExpectedToolCall:
    """Expected tool call specification."""
    tool_name: str
    parameters: Dict[str, Any]
    expected_result: Optional[Any] = None
    allow_parameter_variations: bool = False


@dataclass
class ToolCallTestCase:
    """A single tool call test case."""
    name: str
    description: str
    prompt: str
    expected_tools: List[ExpectedToolCall]
    difficulty: TestDifficulty = TestDifficulty.BASIC
    scoring_weight: float = 1.0
    timeout: int = 30
    expected_sequence: Optional[List[str]] = None
    error_handling: bool = False
    
    def validate_tool_calls(self, actual_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate actual tool calls against expected ones."""
        validation_result = {
            "passed": False,
            "score": 0.0,
            "details": {
                "expected_count": len(self.expected_tools),
                "actual_count": len(actual_calls),
                "tool_matches": [],
                "parameter_matches": [],
                "sequence_correct": True
            }
        }
        
        if not self.expected_tools:
            validation_result["passed"] = len(actual_calls) == 0
            validation_result["score"] = 1.0 if validation_result["passed"] else 0.0
            return validation_result
        
        # Check tool selection
        expected_tool_names = [tool.tool_name for tool in self.expected_tools]
        actual_tool_names = [call.get("tool_name", call.get("name", "")) for call in actual_calls]
        
        tool_score = 0.0
        for expected_tool in expected_tool_names:
            if expected_tool in actual_tool_names:
                tool_score += 1.0
                validation_result["details"]["tool_matches"].append(expected_tool)
        
        if len(expected_tool_names) > 0:
            tool_score /= len(expected_tool_names)
        
        # Check parameter accuracy
        param_score = 0.0
        for i, expected_tool in enumerate(self.expected_tools):
            if i < len(actual_calls):
                actual_call = actual_calls[i]
                actual_params = actual_call.get("parameters", actual_call.get("args", {}))
                
                param_match = self._compare_parameters(expected_tool.parameters, actual_params)
                param_score += param_match
                validation_result["details"]["parameter_matches"].append({
                    "tool": expected_tool.tool_name,
                    "match_score": param_match
                })
        
        if len(self.expected_tools) > 0:
            param_score /= len(self.expected_tools)
        
        # Check sequence if specified
        sequence_score = 1.0
        if self.expected_sequence:
            if len(actual_tool_names) != len(self.expected_sequence):
                sequence_score = 0.0
                validation_result["details"]["sequence_correct"] = False
            else:
                for i, expected_name in enumerate(self.expected_sequence):
                    if i >= len(actual_tool_names) or actual_tool_names[i] != expected_name:
                        sequence_score = 0.0
                        validation_result["details"]["sequence_correct"] = False
                        break
        
        # Calculate overall score
        overall_score = (tool_score * 0.5) + (param_score * 0.3) + (sequence_score * 0.2)
        validation_result["score"] = overall_score
        validation_result["passed"] = overall_score >= 0.7
        
        return validation_result
    
    def _compare_parameters(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
        """Compare expected vs actual parameters."""
        if not expected:
            return 1.0
        
        matches = 0
        for key, expected_value in expected.items():
            if key in actual:
                actual_value = actual[key]
                if self._values_match(expected_value, actual_value):
                    matches += 1
        
        return matches / len(expected) if expected else 1.0
    
    def _values_match(self, expected: Any, actual: Any) -> bool:
        """Check if two values match (with some tolerance)."""
        if type(expected) != type(actual):
            # Try to convert for comparison
            try:
                if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                    return abs(expected - actual) < 0.001
                elif isinstance(expected, str) and isinstance(actual, str):
                    return expected.lower().strip() == actual.lower().strip()
            except:
                pass
            return False
        
        if isinstance(expected, (int, float)):
            return abs(expected - actual) < 0.001
        elif isinstance(expected, str):
            return expected.lower().strip() == actual.lower().strip()
        elif isinstance(expected, list):
            if len(expected) != len(actual):
                return False
            return all(self._values_match(e, a) for e, a in zip(expected, actual))
        elif isinstance(expected, dict):
            if set(expected.keys()) != set(actual.keys()):
                return False
            return all(self._values_match(expected[k], actual[k]) for k in expected.keys())
        else:
            return expected == actual


class ScenarioGroup:
    """A group of related test scenarios."""
    
    def __init__(self, name: str, description: str, test_cases: List[ToolCallTestCase]):
        self.name = name
        self.description = description
        self.test_cases = test_cases
    
    def get_test_cases(self) -> List[ToolCallTestCase]:
        """Get all test cases in this group."""
        return self.test_cases
    
    def get_test_case(self, name: str) -> Optional[ToolCallTestCase]:
        """Get a specific test case by name."""
        for test_case in self.test_cases:
            if test_case.name == name:
                return test_case
        return None


class ToolCallScenarioFactory:
    """Factory for creating tool call test scenarios."""
    
    @staticmethod
    def create_basic_scenarios() -> ScenarioGroup:
        """Create basic tool call scenarios."""
        scenarios = [
            ToolCallTestCase(
                name="basic_calculation",
                description="Test basic arithmetic calculation",
                prompt="Calculate the square root of 144",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="calculator",
                        parameters={"operation": "sqrt", "values": [144]}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="weather_lookup",
                description="Test weather information retrieval",
                prompt="What's the weather like in London?",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="weather_api",
                        parameters={"location": "London"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="text_formatting",
                description="Test text formatting operation",
                prompt="Convert 'hello world' to uppercase",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="text_formatter",
                        parameters={"text": "hello world", "operation": "uppercase"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="unit_conversion",
                description="Test unit conversion",
                prompt="Convert 50 miles to kilometers",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="unit_converter",
                        parameters={"value": 50, "from_unit": "miles", "to_unit": "kilometers"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="current_time",
                description="Test getting current time",
                prompt="What time is it now?",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="datetime_tool",
                        parameters={"operation": "current_time"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            )
        ]
        
        return ScenarioGroup("Basic Tool Calls", "Basic single-tool scenarios", scenarios)
    
    @staticmethod
    def create_multi_tool_scenarios() -> ScenarioGroup:
        """Create multi-tool scenarios."""
        scenarios = [
            ToolCallTestCase(
                name="unit_conversion_calculation",
                description="Convert units then perform calculation",
                prompt="Convert 50 miles to kilometers, then calculate how long it takes to travel at 60 km/h",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="unit_converter",
                        parameters={"value": 50, "from_unit": "miles", "to_unit": "kilometers"}
                    ),
                    ExpectedToolCall(
                        tool_name="calculator",
                        parameters={"operation": "divide", "values": [80.47, 60]}
                    )
                ],
                expected_sequence=["unit_converter", "calculator"],
                difficulty=TestDifficulty.INTERMEDIATE,
                scoring_weight=20
            ),
            
            ToolCallTestCase(
                name="weather_and_formatting",
                description="Get weather data and format the response",
                prompt="Get the weather for Paris and format the location name in uppercase",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="weather_api",
                        parameters={"location": "Paris"}
                    ),
                    ExpectedToolCall(
                        tool_name="text_formatter",
                        parameters={"text": "Paris", "operation": "uppercase"}
                    )
                ],
                difficulty=TestDifficulty.INTERMEDIATE,
                scoring_weight=20
            ),
            
            ToolCallTestCase(
                name="date_calculation_formatting",
                description="Add days to a date and format the result",
                prompt="Add 30 days to 2024-01-15 and format the result as 'January 15, 2024'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="datetime_tool",
                        parameters={"operation": "add_days", "date": "2024-01-15", "days": 30}
                    ),
                    ExpectedToolCall(
                        tool_name="datetime_tool",
                        parameters={"operation": "format_date", "date": "2024-02-14", "format": "%B %d, %Y"}
                    )
                ],
                expected_sequence=["datetime_tool", "datetime_tool"],
                difficulty=TestDifficulty.INTERMEDIATE,
                scoring_weight=20
            )
        ]
        
        return ScenarioGroup("Multi-Tool Scenarios", "Scenarios requiring multiple tools", scenarios)
    
    @staticmethod
    def create_complex_scenarios() -> ScenarioGroup:
        """Create complex scenarios with error handling."""
        scenarios = [
            ToolCallTestCase(
                name="invalid_calculation",
                description="Test handling of invalid mathematical operations",
                prompt="Calculate the square root of -100",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="calculator",
                        parameters={"operation": "sqrt", "values": [-100]}
                    )
                ],
                error_handling=True,
                difficulty=TestDifficulty.ADVANCED,
                scoring_weight=15
            ),
            
            ToolCallTestCase(
                name="division_by_zero",
                description="Test handling of division by zero",
                prompt="Divide 10 by 0",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="calculator",
                        parameters={"operation": "divide", "values": [10, 0]}
                    )
                ],
                error_handling=True,
                difficulty=TestDifficulty.ADVANCED,
                scoring_weight=15
            ),
            
            ToolCallTestCase(
                name="invalid_json",
                description="Test handling of invalid JSON",
                prompt="Parse this JSON: '{invalid json'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="json_processor",
                        parameters={"json_data": "{invalid json", "operation": "parse"}
                    )
                ],
                error_handling=True,
                difficulty=TestDifficulty.ADVANCED,
                scoring_weight=15
            )
        ]
        
        return ScenarioGroup("Complex Scenarios", "Advanced scenarios with error handling", scenarios)
    
    @staticmethod
    def create_json_processing_scenarios() -> ScenarioGroup:
        """Create JSON processing scenarios."""
        scenarios = [
            ToolCallTestCase(
                name="json_parsing",
                description="Test JSON parsing",
                prompt="Parse this JSON data: '{\"name\": \"John\", \"age\": 30}'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="json_processor",
                        parameters={"json_data": "{\"name\": \"John\", \"age\": 30}", "operation": "parse"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="json_validation",
                description="Test JSON validation",
                prompt="Validate this JSON: '[1, 2, 3]'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="json_processor",
                        parameters={"json_data": "[1, 2, 3]", "operation": "validate"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            )
        ]
        
        return ScenarioGroup("JSON Processing", "JSON manipulation scenarios", scenarios)
    
    @staticmethod
    def create_file_operations_scenarios() -> ScenarioGroup:
        """Create file operations scenarios."""
        scenarios = [
            ToolCallTestCase(
                name="read_file",
                description="Test reading a file",
                prompt="Read the contents of the file 'data.txt'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="file_operations",
                        parameters={"operation": "read", "file_path": "data.txt"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="write_file",
                description="Test writing to a file",
                prompt="Write 'Hello World' to a file named 'output.txt'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="file_operations",
                        parameters={"operation": "write", "file_path": "output.txt", "content": "Hello World"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="file_workflow",
                description="Test file operations workflow",
                prompt="Check if 'config.json' exists, and if it does, read its contents",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="file_operations",
                        parameters={"operation": "exists", "file_path": "config.json"}
                    ),
                    ExpectedToolCall(
                        tool_name="file_operations",
                        parameters={"operation": "read", "file_path": "config.json"}
                    )
                ],
                expected_sequence=["file_operations", "file_operations"],
                difficulty=TestDifficulty.INTERMEDIATE,
                scoring_weight=15
            )
        ]
        
        return ScenarioGroup("File Operations", "File manipulation scenarios", scenarios)
    
    @staticmethod
    def create_communication_scenarios() -> ScenarioGroup:
        """Create communication scenarios (email, API, etc.)."""
        scenarios = [
            ToolCallTestCase(
                name="send_email",
                description="Test sending an email",
                prompt="Send an email to john@example.com with subject 'Meeting Tomorrow' and body 'Don't forget about our meeting'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="email_tool",
                        parameters={"operation": "send", "to": "john@example.com", "subject": "Meeting Tomorrow", "body": "Don't forget about our meeting"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="api_request",
                description="Test making an API request",
                prompt="Make a GET request to https://api.example.com/users",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="api_client",
                        parameters={"url": "https://api.example.com/users", "method": "GET"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="web_scraping",
                description="Test web scraping",
                prompt="Extract all links from https://example.com",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="web_scraper",
                        parameters={"url": "https://example.com", "operation": "extract_links"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            ),
            
            ToolCallTestCase(
                name="database_query",
                description="Test database operations",
                prompt="Query the users table to get all records",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="database_tool",
                        parameters={"operation": "query", "table": "users"}
                    )
                ],
                difficulty=TestDifficulty.BASIC,
                scoring_weight=10
            )
        ]
        
        return ScenarioGroup("Communication & Data", "Communication and data access scenarios", scenarios)
    
    @staticmethod
    def create_advanced_workflows() -> ScenarioGroup:
        """Create advanced workflow scenarios."""
        scenarios = [
            ToolCallTestCase(
                name="data_processing_pipeline",
                description="Test complex data processing pipeline",
                prompt="Extract data from https://api.example.com/data, parse it as JSON, then save it to 'processed_data.json'",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="api_client",
                        parameters={"url": "https://api.example.com/data", "method": "GET"}
                    ),
                    ExpectedToolCall(
                        tool_name="json_processor",
                        parameters={"json_data": "{\"data\": \"example\"}", "operation": "parse"}
                    ),
                    ExpectedToolCall(
                        tool_name="file_operations",
                        parameters={"operation": "write", "file_path": "processed_data.json", "content": "{\"data\": \"example\"}"}
                    )
                ],
                expected_sequence=["api_client", "json_processor", "file_operations"],
                difficulty=TestDifficulty.ADVANCED,
                scoring_weight=25
            ),
            
            ToolCallTestCase(
                name="email_data_workflow",
                description="Test email and data workflow",
                prompt="Query the users table for active users, then send a welcome email to each user",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="database_tool",
                        parameters={"operation": "query", "table": "users"}
                    ),
                    ExpectedToolCall(
                        tool_name="email_tool",
                        parameters={"operation": "send", "to": "user@example.com", "subject": "Welcome", "body": "Welcome to our platform"}
                    )
                ],
                expected_sequence=["database_tool", "email_tool"],
                difficulty=TestDifficulty.ADVANCED,
                scoring_weight=20
            ),
            
            ToolCallTestCase(
                name="web_to_database_workflow",
                description="Test web scraping to database workflow",
                prompt="Scrape text from https://news.example.com, then insert it into the articles table",
                expected_tools=[
                    ExpectedToolCall(
                        tool_name="web_scraper",
                        parameters={"url": "https://news.example.com", "operation": "extract_text"}
                    ),
                    ExpectedToolCall(
                        tool_name="database_tool",
                        parameters={"operation": "insert", "table": "articles", "query": "INSERT INTO articles (content) VALUES ('scraped content')"}
                    )
                ],
                expected_sequence=["web_scraper", "database_tool"],
                difficulty=TestDifficulty.ADVANCED,
                scoring_weight=20
            )
        ]
        
        return ScenarioGroup("Advanced Workflows", "Complex multi-step workflows", scenarios)
    
    @staticmethod
    def get_all_scenario_groups() -> List[ScenarioGroup]:
        """Get all predefined scenario groups."""
        return [
            ToolCallScenarioFactory.create_basic_scenarios(),
            ToolCallScenarioFactory.create_multi_tool_scenarios(),
            ToolCallScenarioFactory.create_complex_scenarios(),
            ToolCallScenarioFactory.create_json_processing_scenarios(),
            ToolCallScenarioFactory.create_file_operations_scenarios(),
            ToolCallScenarioFactory.create_communication_scenarios(),
            ToolCallScenarioFactory.create_advanced_workflows()
        ]
    
    @staticmethod
    def get_all_scenarios() -> List[ToolCallTestCase]:
        """Get all predefined scenarios as a flat list."""
        all_scenarios = []
        for group in ToolCallScenarioFactory.get_all_scenario_groups():
            all_scenarios.extend(group.get_test_cases())
        return all_scenarios