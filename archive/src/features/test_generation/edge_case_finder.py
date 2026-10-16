"""
Edge Case Finder Module
Identifies and generates edge cases for LLM testing
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import random

@dataclass
class EdgeCase:
    """Represents an edge case scenario"""
    case_id: str
    description: str
    input_data: str
    expected_challenge: str
    category: str
    metadata: Dict[str, Any]

class EdgeCaseFinder:
    """Finds and generates edge cases for comprehensive testing"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.categories = [
            'boundary_conditions',
            'empty_inputs',
            'malformed_data',
            'extreme_values',
            'unicode_edge_cases',
            'context_switching'
        ]
    
    def find_boundary_conditions(self, count: int = 10) -> List[EdgeCase]:
        """Generate boundary condition test cases"""
        cases = []
        
        boundary_tests = [
            ("empty_string", "", "handle_empty_input"),
            ("single_character", "a", "handle_minimal_input"),
            ("maximum_length", "a" * 10000, "handle_very_long_input"),
            ("special_characters", "!@#$%^&*()", "handle_special_chars"),
            ("unicode_mix", "Hello 世界 🌍", "handle_unicode_properly"),
        ]
        
        for i, (desc, input_data, challenge) in enumerate(boundary_tests[:count]):
            case = EdgeCase(
                case_id=f"boundary_{i+1}",
                description=desc,
                input_data=input_data,
                expected_challenge=challenge,
                category="boundary_conditions",
                metadata={"test_type": "boundary", "length": len(input_data)}
            )
            cases.append(case)
        
        return cases
    
    def find_malformed_data_cases(self, count: int = 10) -> List[EdgeCase]:
        """Generate malformed data test cases"""
        cases = []
        
        malformed_examples = [
            ("unmatched_brackets", "This is a test [with unmatched brackets", "handle_malformed_syntax"),
            ("broken_json", '{"key": "value", "broken": }', "handle_invalid_json"),
            ("mixed_languages", "Hello こんにちは مرحبا", "handle_mixed_scripts"),
            ("control_characters", "Text\x00with\x01control\x02chars", "handle_control_chars"),
            ("deeply_nested", "((((((((((nested))))))))))", "handle_deep_nesting"),
        ]
        
        for i, (desc, input_data, challenge) in enumerate(malformed_examples[:count]):
            case = EdgeCase(
                case_id=f"malformed_{i+1}",
                description=desc,
                input_data=input_data,
                expected_challenge=challenge,
                category="malformed_data",
                metadata={"test_type": "malformed", "contains_special": True}
            )
            cases.append(case)
        
        return cases
    
    def find_extreme_value_cases(self, count: int = 10) -> List[EdgeCase]:
        """Generate extreme value test cases"""
        cases = []
        
        extreme_examples = [
            ("very_large_number", "Calculate 999999999999999999999 + 1", "handle_large_numbers"),
            ("very_small_number", "Calculate 0.00000000000000001 * 2", "handle_small_numbers"),
            ("negative_extreme", "What is -999999999999999999999?", "handle_negative_extremes"),
            ("scientific_notation", "Convert 1.23e-45 to decimal", "handle_scientific_notation"),
            ("infinity_concept", "What is infinity divided by infinity?", "handle_infinity_concepts"),
        ]
        
        for i, (desc, input_data, challenge) in enumerate(extreme_examples[:count]):
            case = EdgeCase(
                case_id=f"extreme_{i+1}",
                description=desc,
                input_data=input_data,
                expected_challenge=challenge,
                category="extreme_values",
                metadata={"test_type": "extreme", "numerical": True}
            )
            cases.append(case)
        
        return cases
    
    def find_context_switching_cases(self, count: int = 10) -> List[EdgeCase]:
        """Generate context switching test cases"""
        cases = []
        
        context_examples = [
            ("language_switch", "Explain in English, then switch to Spanish: Como estas?", "handle_language_switch"),
            ("topic_switch", "Tell me about cats. Now tell me about quantum physics.", "handle_topic_switch"),
            ("format_switch", "Write a poem, then a technical manual entry.", "handle_format_switch"),
            ("mood_switch", "Write something happy, then something sad.", "handle_mood_switch"),
            ("perspective_switch", "Explain from a child's view, then an expert's view.", "handle_perspective_switch"),
        ]
        
        for i, (desc, input_data, challenge) in enumerate(context_examples[:count]):
            case = EdgeCase(
                case_id=f"context_{i+1}",
                description=desc,
                input_data=input_data,
                expected_challenge=challenge,
                category="context_switching",
                metadata={"test_type": "context", "requires_adaptation": True}
            )
            cases.append(case)
        
        return cases
    
    def find_all_edge_cases(self, count_per_category: int = 5) -> List[EdgeCase]:
        """Find all categories of edge cases"""
        all_cases = []
        all_cases.extend(self.find_boundary_conditions(count_per_category))
        all_cases.extend(self.find_malformed_data_cases(count_per_category))
        all_cases.extend(self.find_extreme_value_cases(count_per_category))
        all_cases.extend(self.find_context_switching_cases(count_per_category))
        
        return all_cases