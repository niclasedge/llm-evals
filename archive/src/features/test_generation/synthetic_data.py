"""
Synthetic Data Generator Module
Generates synthetic data for testing LLM capabilities
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import random
import string
import json

@dataclass
class SyntheticDataPoint:
    """Represents a synthetic data point"""
    data_id: str
    content: str
    data_type: str
    category: str
    metadata: Dict[str, Any]

class SyntheticDataGenerator:
    """Generates synthetic data for various test scenarios"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.data_types = [
            'text_completion',
            'qa_pairs',
            'code_snippets',
            'structured_data',
            'conversation_threads',
            'technical_documents'
        ]
    
    def generate_text_completion_data(self, count: int = 10) -> List[SyntheticDataPoint]:
        """Generate text completion test data"""
        data_points = []
        
        templates = [
            "The weather today is {weather}, which makes me feel {emotion}.",
            "In the year {year}, scientists discovered that {discovery}.",
            "The best way to {action} is to {method} because {reason}.",
            "When I think about {topic}, I remember {memory}.",
            "The solution to {problem} involves {solution_step}.",
        ]
        
        for i in range(count):
            template = random.choice(templates)
            partial_text = template.split('{')[0]  # Get text before first placeholder
            
            data_point = SyntheticDataPoint(
                data_id=f"text_completion_{i+1}",
                content=partial_text,
                data_type="text_completion",
                category="language_modeling",
                metadata={
                    "template": template,
                    "expected_completion": True,
                    "difficulty": "medium"
                }
            )
            data_points.append(data_point)
        
        return data_points
    
    def generate_qa_pairs(self, count: int = 10) -> List[SyntheticDataPoint]:
        """Generate question-answer pairs"""
        data_points = []
        
        qa_templates = [
            ("What is the capital of {country}?", "factual_geography"),
            ("How do you calculate {math_concept}?", "mathematical_explanation"),
            ("What are the benefits of {activity}?", "analysis_benefits"),
            ("Why does {phenomenon} occur?", "causal_explanation"),
            ("What is the difference between {concept1} and {concept2}?", "comparison"),
        ]
        
        for i, (question_template, category) in enumerate(qa_templates[:count]):
            data_point = SyntheticDataPoint(
                data_id=f"qa_pair_{i+1}",
                content=question_template,
                data_type="qa_pairs",
                category=category,
                metadata={
                    "question_type": category,
                    "requires_knowledge": True,
                    "difficulty": "medium"
                }
            )
            data_points.append(data_point)
        
        return data_points
    
    def generate_code_snippets(self, count: int = 10) -> List[SyntheticDataPoint]:
        """Generate code snippet test data"""
        data_points = []
        
        code_templates = [
            ("def calculate_sum(a, b):\n    # Complete this function", "function_completion"),
            ("# Sort this list: [3, 1, 4, 1, 5, 9, 2, 6]", "algorithm_implementation"),
            ("class Calculator:\n    def __init__(self):\n        # Initialize", "class_completion"),
            ("# Find all prime numbers up to n", "mathematical_programming"),
            ("# Parse this JSON and extract the name field", "data_processing"),
        ]
        
        for i, (code_template, category) in enumerate(code_templates[:count]):
            data_point = SyntheticDataPoint(
                data_id=f"code_snippet_{i+1}",
                content=code_template,
                data_type="code_snippets",
                category=category,
                metadata={
                    "language": "python",
                    "task_type": category,
                    "difficulty": "medium"
                }
            )
            data_points.append(data_point)
        
        return data_points
    
    def generate_structured_data(self, count: int = 10) -> List[SyntheticDataPoint]:
        """Generate structured data test cases"""
        data_points = []
        
        structured_examples = [
            ('{"name": "John", "age": 30, "city": "New York"}', "json_parsing"),
            ("name,age,city\nJohn,30,New York\nJane,25,Boston", "csv_processing"),
            ("<person><name>John</name><age>30</age></person>", "xml_processing"),
            ("Name: John\nAge: 30\nCity: New York", "key_value_parsing"),
            ("John | 30 | New York | Software Engineer", "delimiter_parsing"),
        ]
        
        for i, (data_content, category) in enumerate(structured_examples[:count]):
            data_point = SyntheticDataPoint(
                data_id=f"structured_{i+1}",
                content=data_content,
                data_type="structured_data",
                category=category,
                metadata={
                    "format": category.split('_')[0],
                    "parsing_required": True,
                    "difficulty": "medium"
                }
            )
            data_points.append(data_point)
        
        return data_points
    
    def generate_conversation_threads(self, count: int = 10) -> List[SyntheticDataPoint]:
        """Generate conversation thread test data"""
        data_points = []
        
        conversation_templates = [
            ("User: Hello, how are you?\nAssistant: I'm doing well, thank you! How can I help you today?\nUser: I need help with", "customer_service"),
            ("A: What do you think about the new policy?\nB: I think it has both pros and cons.\nA: Can you elaborate on", "discussion_continuation"),
            ("Teacher: What is 2+2?\nStudent: 4\nTeacher: Correct! Now what about", "educational_dialogue"),
            ("Doctor: How are you feeling today?\nPatient: I've been having headaches.\nDoctor: Can you tell me more about", "medical_consultation"),
            ("Interviewer: Tell me about yourself.\nCandidate: I'm a software engineer with 5 years experience.\nInterviewer: What", "job_interview"),
        ]
        
        for i, (conversation, category) in enumerate(conversation_templates[:count]):
            data_point = SyntheticDataPoint(
                data_id=f"conversation_{i+1}",
                content=conversation,
                data_type="conversation_threads",
                category=category,
                metadata={
                    "dialogue_type": category,
                    "context_dependent": True,
                    "difficulty": "medium"
                }
            )
            data_points.append(data_point)
        
        return data_points
    
    def generate_all_synthetic_data(self, count_per_type: int = 5) -> List[SyntheticDataPoint]:
        """Generate all types of synthetic data"""
        all_data = []
        all_data.extend(self.generate_text_completion_data(count_per_type))
        all_data.extend(self.generate_qa_pairs(count_per_type))
        all_data.extend(self.generate_code_snippets(count_per_type))
        all_data.extend(self.generate_structured_data(count_per_type))
        all_data.extend(self.generate_conversation_threads(count_per_type))
        
        return all_data