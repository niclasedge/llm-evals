"""
Scoring engine for evaluating LLM tool calling performance.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .test_scenarios import ToolCallTestCase, TestDifficulty


class ScoringDimension(Enum):
    """Scoring dimensions for tool call evaluation."""
    TOOL_SELECTION = "tool_selection"
    PARAMETER_ACCURACY = "parameter_accuracy"
    EXECUTION_LOGIC = "execution_logic"
    ERROR_HANDLING = "error_handling"
    RESPONSE_QUALITY = "response_quality"


@dataclass
class ScoringConfig:
    """Configuration for scoring algorithm."""
    weights: Dict[ScoringDimension, float]
    thresholds: Dict[str, float]
    
    @classmethod
    def default(cls) -> 'ScoringConfig':
        """Get default scoring configuration."""
        return cls(
            weights={
                ScoringDimension.TOOL_SELECTION: 0.30,
                ScoringDimension.PARAMETER_ACCURACY: 0.25,
                ScoringDimension.EXECUTION_LOGIC: 0.20,
                ScoringDimension.ERROR_HANDLING: 0.15,
                ScoringDimension.RESPONSE_QUALITY: 0.10
            },
            thresholds={
                "excellent": 0.90,
                "good": 0.75,
                "fair": 0.60,
                "poor": 0.40
            }
        )


@dataclass
class ToolCallResult:
    """Result of a tool call evaluation."""
    test_case: ToolCallTestCase
    response: str
    extracted_tool_calls: List[Dict[str, Any]]
    scores: Dict[ScoringDimension, float]
    overall_score: float
    passed: bool
    execution_time: float
    error_message: Optional[str] = None


class ToolCallParser:
    """Parser for extracting tool calls from LLM responses."""
    
    def __init__(self):
        self.patterns = [
            # JSON format: {"tool_name": "...", "parameters": {...}}
            r'\{[^}]*"tool_name"\s*:\s*"([^"]+)"[^}]*"parameters"\s*:\s*\{[^}]*\}[^}]*\}',
            # Function call format: function_name(param1=value1, param2=value2)
            r'(\w+)\s*\([^)]*\)',
            # Structured format: Tool: name, Parameters: {...}
            r'Tool:\s*(\w+).*?Parameters:\s*\{[^}]*\}',
        ]
    
    def parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract tool calls from LLM response."""
        tool_calls = []
        
        # Try to find JSON-like structures first
        json_calls = self._extract_json_calls(response)
        if json_calls:
            tool_calls.extend(json_calls)
        
        # Try to find function call patterns
        function_calls = self._extract_function_calls(response)
        if function_calls:
            tool_calls.extend(function_calls)
        
        # Try to find structured text patterns
        structured_calls = self._extract_structured_calls(response)
        if structured_calls:
            tool_calls.extend(structured_calls)
        
        return tool_calls
    
    def _extract_json_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract JSON-formatted tool calls."""
        tool_calls = []
        
        # Look for JSON objects in the response
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response)
        
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict):
                    # Check if it looks like a tool call
                    if "tool_name" in data or "name" in data:
                        tool_call = {
                            "tool_name": data.get("tool_name", data.get("name", "")),
                            "parameters": data.get("parameters", data.get("args", {}))
                        }
                        tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract function call patterns."""
        tool_calls = []
        
        # Pattern: function_name(param1=value1, param2=value2)
        pattern = r'(\w+)\s*\(([^)]*)\)'
        matches = re.findall(pattern, response)
        
        for func_name, params_str in matches:
            # Skip common words that aren't function names
            if func_name.lower() in ['the', 'and', 'for', 'with', 'this', 'that', 'can', 'will']:
                continue
            
            parameters = {}
            if params_str.strip():
                # Parse parameters
                param_matches = re.findall(r'(\w+)\s*=\s*([^,)]+)', params_str)
                for param_name, param_value in param_matches:
                    # Try to parse the value
                    try:
                        # Remove quotes if present
                        param_value = param_value.strip().strip('"\'')
                        # Try to convert to number
                        if '.' in param_value:
                            param_value = float(param_value)
                        else:
                            try:
                                param_value = int(param_value)
                            except ValueError:
                                pass  # Keep as string
                    except:
                        pass  # Keep as string
                    
                    parameters[param_name] = param_value
            
            tool_calls.append({
                "tool_name": func_name,
                "parameters": parameters
            })
        
        return tool_calls
    
    def _extract_structured_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract structured text patterns."""
        tool_calls = []
        
        # Pattern: Tool: name, Parameters: {...}
        lines = response.split('\n')
        current_tool = None
        current_params = {}
        
        for line in lines:
            line = line.strip()
            
            # Look for tool declarations
            tool_match = re.search(r'Tool:\s*(\w+)', line, re.IGNORECASE)
            if tool_match:
                if current_tool:
                    tool_calls.append({
                        "tool_name": current_tool,
                        "parameters": current_params
                    })
                current_tool = tool_match.group(1)
                current_params = {}
            
            # Look for parameter declarations
            param_match = re.search(r'Parameters?:\s*(.+)', line, re.IGNORECASE)
            if param_match and current_tool:
                param_str = param_match.group(1)
                try:
                    # Try to parse as JSON
                    current_params = json.loads(param_str)
                except:
                    # Parse as key=value pairs
                    param_pairs = re.findall(r'(\w+)\s*=\s*([^,]+)', param_str)
                    for key, value in param_pairs:
                        current_params[key] = value.strip().strip('"\'')
        
        # Add the last tool if any
        if current_tool:
            tool_calls.append({
                "tool_name": current_tool,
                "parameters": current_params
            })
        
        return tool_calls


class ToolCallScorer:
    """Scorer for tool call evaluation."""
    
    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig.default()
        self.parser = ToolCallParser()
    
    def score_tool_call_result(self, test_case: ToolCallTestCase, response: str, 
                             execution_time: float, error_message: str = None) -> ToolCallResult:
        """Score a complete tool call result."""
        
        # Extract tool calls from response
        extracted_calls = self.parser.parse_tool_calls(response)
        
        # Calculate individual scores
        scores = {}
        scores[ScoringDimension.TOOL_SELECTION] = self._score_tool_selection(
            test_case, extracted_calls
        )
        scores[ScoringDimension.PARAMETER_ACCURACY] = self._score_parameter_accuracy(
            test_case, extracted_calls
        )
        scores[ScoringDimension.EXECUTION_LOGIC] = self._score_execution_logic(
            test_case, extracted_calls
        )
        scores[ScoringDimension.ERROR_HANDLING] = self._score_error_handling(
            test_case, response, error_message
        )
        scores[ScoringDimension.RESPONSE_QUALITY] = self._score_response_quality(
            test_case, response
        )
        
        # Calculate overall score
        overall_score = sum(
            scores[dim] * self.config.weights[dim] 
            for dim in ScoringDimension
        )
        
        # Determine if passed
        passed = overall_score >= self.config.thresholds["fair"]
        
        return ToolCallResult(
            test_case=test_case,
            response=response,
            extracted_tool_calls=extracted_calls,
            scores=scores,
            overall_score=overall_score,
            passed=passed,
            execution_time=execution_time,
            error_message=error_message
        )
    
    def _score_tool_selection(self, test_case: ToolCallTestCase, 
                            extracted_calls: List[Dict[str, Any]]) -> float:
        """Score tool selection accuracy."""
        if not test_case.expected_tools:
            return 1.0 if not extracted_calls else 0.0
        
        expected_tools = {tool.tool_name for tool in test_case.expected_tools}
        actual_tools = {call.get("tool_name", "") for call in extracted_calls}
        
        if not actual_tools:
            return 0.0
        
        # Calculate precision and recall
        intersection = expected_tools.intersection(actual_tools)
        precision = len(intersection) / len(actual_tools) if actual_tools else 0
        recall = len(intersection) / len(expected_tools) if expected_tools else 0
        
        # F1 score
        if precision + recall == 0:
            return 0.0
        
        f1_score = 2 * (precision * recall) / (precision + recall)
        return f1_score
    
    def _score_parameter_accuracy(self, test_case: ToolCallTestCase,
                                extracted_calls: List[Dict[str, Any]]) -> float:
        """Score parameter accuracy."""
        if not test_case.expected_tools:
            return 1.0
        
        total_score = 0.0
        for i, expected_tool in enumerate(test_case.expected_tools):
            if i < len(extracted_calls):
                actual_call = extracted_calls[i]
                actual_params = actual_call.get("parameters", {})
                
                param_score = self._compare_parameters(
                    expected_tool.parameters, actual_params
                )
                total_score += param_score
        
        return total_score / len(test_case.expected_tools) if test_case.expected_tools else 1.0
    
    def _score_execution_logic(self, test_case: ToolCallTestCase,
                             extracted_calls: List[Dict[str, Any]]) -> float:
        """Score execution logic and sequencing."""
        if not test_case.expected_sequence:
            return 1.0
        
        actual_sequence = [call.get("tool_name", "") for call in extracted_calls]
        
        if len(actual_sequence) != len(test_case.expected_sequence):
            return 0.0
        
        matches = sum(1 for expected, actual in zip(test_case.expected_sequence, actual_sequence)
                     if expected == actual)
        
        return matches / len(test_case.expected_sequence)
    
    def _score_error_handling(self, test_case: ToolCallTestCase, response: str,
                            error_message: str = None) -> float:
        """Score error handling capability."""
        if not test_case.error_handling:
            return 1.0  # Not applicable
        
        # Check if the response acknowledges the error appropriately
        error_indicators = [
            "error", "cannot", "unable", "invalid", "failed", "impossible",
            "not possible", "not supported", "not allowed"
        ]
        
        response_lower = response.lower()
        has_error_acknowledgment = any(indicator in response_lower for indicator in error_indicators)
        
        if has_error_acknowledgment:
            return 1.0
        elif error_message:
            return 0.5  # Partial credit for system error
        else:
            return 0.0
    
    def _score_response_quality(self, test_case: ToolCallTestCase, response: str) -> float:
        """Score overall response quality."""
        if not response or not response.strip():
            return 0.0
        
        quality_score = 0.0
        
        # Check length (not too short, not too long)
        word_count = len(response.split())
        if 10 <= word_count <= 200:
            quality_score += 0.3
        elif 5 <= word_count <= 300:
            quality_score += 0.2
        else:
            quality_score += 0.1
        
        # Check coherence (basic heuristics)
        if response.count('.') > 0:  # Has sentences
            quality_score += 0.2
        if response.count('?') <= 2:  # Not too many questions
            quality_score += 0.1
        
        # Check relevance to prompt
        prompt_words = set(test_case.prompt.lower().split())
        response_words = set(response.lower().split())
        overlap = len(prompt_words.intersection(response_words))
        if overlap > 0:
            quality_score += 0.4
        
        return min(quality_score, 1.0)
    
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
        
        return matches / len(expected)
    
    def _values_match(self, expected: Any, actual: Any) -> bool:
        """Check if two values match with tolerance."""
        if type(expected) == type(actual):
            if isinstance(expected, (int, float)):
                return abs(expected - actual) < 0.001
            elif isinstance(expected, str):
                return expected.lower().strip() == actual.lower().strip()
            else:
                return expected == actual
        
        # Try type conversion
        try:
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                return abs(expected - actual) < 0.001
            elif isinstance(expected, str) and isinstance(actual, str):
                return expected.lower().strip() == actual.lower().strip()
        except:
            pass
        
        return False
    
    def calculate_final_score(self, results: List[ToolCallResult]) -> Dict[str, Any]:
        """Calculate final aggregated score across all test results."""
        if not results:
            return {"overall_score": 0.0, "breakdown": {}}
        
        total_weighted_score = 0.0
        total_weight = 0.0
        dimension_scores = {dim: [] for dim in ScoringDimension}
        
        for result in results:
            weight = result.test_case.scoring_weight
            total_weighted_score += result.overall_score * weight
            total_weight += weight
            
            for dim in ScoringDimension:
                dimension_scores[dim].append(result.scores[dim])
        
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Calculate dimension averages
        avg_dimension_scores = {}
        for dim in ScoringDimension:
            scores = dimension_scores[dim]
            avg_dimension_scores[dim.value] = sum(scores) / len(scores) if scores else 0.0
        
        # Performance classification
        if overall_score >= self.config.thresholds["excellent"]:
            classification = "excellent"
        elif overall_score >= self.config.thresholds["good"]:
            classification = "good"
        elif overall_score >= self.config.thresholds["fair"]:
            classification = "fair"
        else:
            classification = "poor"
        
        return {
            "overall_score": overall_score,
            "classification": classification,
            "dimension_scores": avg_dimension_scores,
            "total_tests": len(results),
            "passed_tests": sum(1 for r in results if r.passed),
            "failed_tests": sum(1 for r in results if not r.passed),
            "success_rate": sum(1 for r in results if r.passed) / len(results),
            "average_execution_time": sum(r.execution_time for r in results) / len(results)
        }