"""
Reasoning tests for LLM evaluation.
Tests logical reasoning, mathematical problem solving, and analytical thinking.
"""

import re
from typing import Dict, Any, List, Optional
from src.features.llm_evaluation.test_framework.base_test import BaseTest, TestResult, TestStatus


class MathWordProblemTest(BaseTest):
    """Test mathematical word problem solving."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run math word problem test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        expected_answer = self.get_expected_result()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Extract answer from response
        extracted_answer = self._extract_numerical_answer(response)
        
        # Validate and score
        is_valid = self.validate_result(response)
        score = self.calculate_score(response, expected_answer)
        
        status = TestStatus.PASSED if is_valid and score > 0.8 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'extracted_answer': extracted_answer,
                'expected_answer': expected_answer,
                'model': model,
                'shows_work': self._shows_work(response),
                'logical_steps': self._count_logical_steps(response)
            }
        )
    
    def _extract_numerical_answer(self, response: str) -> Optional[float]:
        """Extract numerical answer from response."""
        # Look for numbers at the end of the response
        numbers = re.findall(r'-?\d+\.?\d*', response)
        if numbers:
            try:
                return float(numbers[-1])
            except ValueError:
                pass
        
        # Look for explicit answer statements
        answer_patterns = [
            r'answer is\s*(-?\d+\.?\d*)',
            r'solution is\s*(-?\d+\.?\d*)',
            r'result is\s*(-?\d+\.?\d*)',
            r'equals?\s*(-?\d+\.?\d*)',
            r'=\s*(-?\d+\.?\d*)'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        
        return None
    
    def _shows_work(self, response: str) -> bool:
        """Check if response shows mathematical work."""
        work_indicators = [
            r'\d+\s*[+\-*/]\s*\d+',  # Basic arithmetic
            r'step\s*\d+',            # Step indicators
            r'first[,\s]',            # Sequential language
            r'then[,\s]',
            r'next[,\s]',
            r'finally[,\s]'
        ]
        
        for pattern in work_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False
    
    def _count_logical_steps(self, response: str) -> int:
        """Count logical steps in the solution."""
        step_patterns = [
            r'step\s*\d+',
            r'first[,\s]',
            r'then[,\s]',
            r'next[,\s]',
            r'finally[,\s]',
            r'\d+\.\s*[A-Z]'  # Numbered points
        ]
        
        steps = 0
        for pattern in step_patterns:
            steps += len(re.findall(pattern, response, re.IGNORECASE))
        
        return steps
    
    def validate_result(self, result: str) -> bool:
        """Validate math problem result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check if it contains numerical answer
        if self._extract_numerical_answer(result) is None:
            return False
        
        # Check minimum length
        if len(result.strip()) < 20:
            return False
        
        return True
    
    def calculate_score(self, result: str, expected: Any) -> float:
        """Calculate math problem score."""
        if not self.validate_result(result):
            return 0.0
        
        score = 0.0
        
        # Correct answer (50%)
        extracted_answer = self._extract_numerical_answer(result)
        if extracted_answer is not None and expected is not None:
            try:
                expected_num = float(expected)
                if abs(extracted_answer - expected_num) < 0.001:
                    score += 0.5
                elif abs(extracted_answer - expected_num) / max(abs(expected_num), 1) < 0.1:
                    score += 0.3  # Close answer
            except (ValueError, TypeError):
                pass
        
        # Shows work (30%)
        if self._shows_work(result):
            score += 0.3
        
        # Logical steps (20%)
        steps = self._count_logical_steps(result)
        if steps >= 2:
            score += 0.2
        elif steps == 1:
            score += 0.1
        
        return min(score, 1.0)
    
    async def _get_response(self, client: Any, prompt: str, system_prompt: str, model: str) -> str:
        """Get response from different client types."""
        try:
            if hasattr(client, 'generate'):
                # Ollama client
                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            elif hasattr(client, 'run_prompt'):
                # LLM CLI client
                response = await client.run_prompt(
                    prompt=prompt,
                    model=model,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            else:
                # PydanticAI agent
                from src.features.llm_evaluation.llm_service import run_query
                response = await run_query(client, prompt)
                return str(response) if response else ''
                
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''


class LogicalReasoningTest(BaseTest):
    """Test logical reasoning capabilities."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run logical reasoning test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        expected_answer = self.get_expected_result()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Validate and score
        is_valid = self.validate_result(response)
        score = self.calculate_score(response, expected_answer)
        
        status = TestStatus.PASSED if is_valid and score > 0.7 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'expected_answer': expected_answer,
                'model': model,
                'logical_structure': self._analyze_logical_structure(response),
                'uses_premises': self._uses_premises(response),
                'reaches_conclusion': self._reaches_conclusion(response)
            }
        )
    
    def _analyze_logical_structure(self, response: str) -> Dict[str, Any]:
        """Analyze logical structure of response."""
        structure = {
            'has_premises': False,
            'has_reasoning': False,
            'has_conclusion': False,
            'uses_connectives': False
        }
        
        # Check for premises
        premise_indicators = ['given', 'if', 'assume', 'premise', 'since']
        for indicator in premise_indicators:
            if indicator in response.lower():
                structure['has_premises'] = True
                break
        
        # Check for reasoning
        reasoning_indicators = ['therefore', 'because', 'since', 'thus', 'hence', 'so']
        for indicator in reasoning_indicators:
            if indicator in response.lower():
                structure['has_reasoning'] = True
                break
        
        # Check for conclusion
        conclusion_indicators = ['conclusion', 'answer', 'result', 'therefore']
        for indicator in conclusion_indicators:
            if indicator in response.lower():
                structure['has_conclusion'] = True
                break
        
        # Check for logical connectives
        connectives = ['and', 'or', 'not', 'if', 'then', 'only if']
        for connective in connectives:
            if connective in response.lower():
                structure['uses_connectives'] = True
                break
        
        return structure
    
    def _uses_premises(self, response: str) -> bool:
        """Check if response uses given premises."""
        premise_keywords = self.config.get('premise_keywords', [])
        if not premise_keywords:
            return True  # No specific premises to check
        
        response_lower = response.lower()
        for keyword in premise_keywords:
            if keyword.lower() in response_lower:
                return True
        
        return False
    
    def _reaches_conclusion(self, response: str) -> bool:
        """Check if response reaches a clear conclusion."""
        conclusion_patterns = [
            r'conclusion[:.]',
            r'answer[:.]',
            r'therefore[:.]',
            r'thus[:.]',
            r'result[:.]'
        ]
        
        for pattern in conclusion_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False
    
    def validate_result(self, result: str) -> bool:
        """Validate logical reasoning result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check minimum length
        if len(result.strip()) < 30:
            return False
        
        # Check for logical structure
        structure = self._analyze_logical_structure(result)
        if not any(structure.values()):
            return False
        
        return True
    
    def calculate_score(self, result: str, expected: Any) -> float:
        """Calculate logical reasoning score."""
        if not self.validate_result(result):
            return 0.0
        
        score = 0.0
        
        # Correct conclusion (40%)
        if expected and isinstance(expected, str):
            if expected.lower() in result.lower():
                score += 0.4
        
        # Logical structure (40%)
        structure = self._analyze_logical_structure(result)
        structure_score = sum(structure.values()) / len(structure)
        score += structure_score * 0.4
        
        # Uses premises (20%)
        if self._uses_premises(result):
            score += 0.2
        
        return min(score, 1.0)
    
    async def _get_response(self, client: Any, prompt: str, system_prompt: str, model: str) -> str:
        """Get response from different client types."""
        try:
            if hasattr(client, 'generate'):
                # Ollama client
                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            elif hasattr(client, 'run_prompt'):
                # LLM CLI client
                response = await client.run_prompt(
                    prompt=prompt,
                    model=model,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            else:
                # PydanticAI agent
                from src.features.llm_evaluation.llm_service import run_query
                response = await run_query(client, prompt)
                return str(response) if response else ''
                
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''


class PatternRecognitionTest(BaseTest):
    """Test pattern recognition capabilities."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run pattern recognition test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        expected_answer = self.get_expected_result()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Extract pattern from response
        extracted_pattern = self._extract_pattern(response)
        
        # Validate and score
        is_valid = self.validate_result(response)
        score = self.calculate_score(response, expected_answer)
        
        status = TestStatus.PASSED if is_valid and score > 0.7 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'extracted_pattern': extracted_pattern,
                'expected_answer': expected_answer,
                'model': model,
                'identifies_pattern': self._identifies_pattern(response),
                'explains_reasoning': self._explains_reasoning(response)
            }
        )
    
    def _extract_pattern(self, response: str) -> Optional[str]:
        """Extract identified pattern from response."""
        # Look for pattern descriptions
        pattern_indicators = [
            r'pattern is\s*([^.]+)',
            r'sequence is\s*([^.]+)',
            r'rule is\s*([^.]+)',
            r'follows\s*([^.]+)'
        ]
        
        for pattern in pattern_indicators:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _identifies_pattern(self, response: str) -> bool:
        """Check if response identifies a pattern."""
        pattern_keywords = [
            'pattern', 'sequence', 'rule', 'increase', 'decrease',
            'multiply', 'divide', 'add', 'subtract', 'follows'
        ]
        
        response_lower = response.lower()
        for keyword in pattern_keywords:
            if keyword in response_lower:
                return True
        
        return False
    
    def _explains_reasoning(self, response: str) -> bool:
        """Check if response explains the reasoning."""
        reasoning_indicators = [
            'because', 'since', 'therefore', 'thus', 'hence',
            'reason', 'explanation', 'logic', 'rule'
        ]
        
        response_lower = response.lower()
        for indicator in reasoning_indicators:
            if indicator in response_lower:
                return True
        
        return False
    
    def validate_result(self, result: str) -> bool:
        """Validate pattern recognition result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check minimum length
        if len(result.strip()) < 20:
            return False
        
        # Check if it identifies a pattern
        if not self._identifies_pattern(result):
            return False
        
        return True
    
    def calculate_score(self, result: str, expected: Any) -> float:
        """Calculate pattern recognition score."""
        if not self.validate_result(result):
            return 0.0
        
        score = 0.0
        
        # Correct pattern (50%)
        if expected and isinstance(expected, str):
            if expected.lower() in result.lower():
                score += 0.5
        
        # Identifies pattern (30%)
        if self._identifies_pattern(result):
            score += 0.3
        
        # Explains reasoning (20%)
        if self._explains_reasoning(result):
            score += 0.2
        
        return min(score, 1.0)
    
    async def _get_response(self, client: Any, prompt: str, system_prompt: str, model: str) -> str:
        """Get response from different client types."""
        try:
            if hasattr(client, 'generate'):
                # Ollama client
                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            elif hasattr(client, 'run_prompt'):
                # LLM CLI client
                response = await client.run_prompt(
                    prompt=prompt,
                    model=model,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            else:
                # PydanticAI agent
                from src.features.llm_evaluation.llm_service import run_query
                response = await run_query(client, prompt)
                return str(response) if response else ''
                
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''


class ReasoningTests:
    """Collection of reasoning tests."""
    
    @staticmethod
    def get_math_word_problem_test() -> MathWordProblemTest:
        """Get math word problem test."""
        config = {
            'prompt': 'Sarah has 24 apples. She gives 1/3 of them to her friend Tom, and then buys 8 more apples. How many apples does Sarah have now?',
            'system_prompt': 'You are a math tutor. Solve problems step by step, showing your work clearly.',
            'expected_result': 24,  # 24 - 8 + 8 = 24
            'min_length': 50
        }
        return MathWordProblemTest(
            name='math_word_problem_apples',
            description='Math word problem with fractions',
            config=config
        )
    
    @staticmethod
    def get_logical_reasoning_test() -> LogicalReasoningTest:
        """Get logical reasoning test."""
        config = {
            'prompt': 'All birds can fly. Penguins are birds. Can penguins fly? Explain your reasoning.',
            'system_prompt': 'You are a logic teacher. Analyze arguments carefully and identify logical fallacies.',
            'expected_result': 'premise is incorrect',
            'premise_keywords': ['birds', 'fly', 'penguins'],
            'min_length': 50
        }
        return LogicalReasoningTest(
            name='logical_reasoning_birds',
            description='Logical reasoning with false premise',
            config=config
        )
    
    @staticmethod
    def get_pattern_recognition_test() -> PatternRecognitionTest:
        """Get pattern recognition test."""
        config = {
            'prompt': 'What comes next in this sequence: 2, 6, 18, 54, ?',
            'system_prompt': 'You are a pattern recognition expert. Identify the pattern and explain your reasoning.',
            'expected_result': 'multiply by 3',
            'min_length': 30
        }
        return PatternRecognitionTest(
            name='pattern_recognition_sequence',
            description='Number sequence pattern recognition',
            config=config
        )
    
    @staticmethod
    def get_complex_reasoning_test() -> LogicalReasoningTest:
        """Get complex reasoning test."""
        config = {
            'prompt': 'In a group of 100 people, 70 like chocolate, 80 like vanilla, and 60 like both. How many people like neither chocolate nor vanilla?',
            'system_prompt': 'You are a mathematics teacher. Use set theory and logical reasoning to solve this problem.',
            'expected_result': '10',
            'premise_keywords': ['chocolate', 'vanilla', 'both', 'neither'],
            'min_length': 100
        }
        return LogicalReasoningTest(
            name='complex_reasoning_sets',
            description='Complex reasoning with set theory',
            config=config
        )
    
    @staticmethod
    def get_all_tests() -> List[BaseTest]:
        """Get all reasoning tests."""
        return [
            ReasoningTests.get_math_word_problem_test(),
            ReasoningTests.get_logical_reasoning_test(),
            ReasoningTests.get_pattern_recognition_test(),
            ReasoningTests.get_complex_reasoning_test()
        ]