"""
Code generation tests for LLM evaluation.
Tests programming capabilities and code quality.
"""

import ast
import re
from typing import Dict, Any, List, Optional
from src.features.llm_evaluation.test_framework.base_test import BaseTest, TestResult, TestStatus


class PythonCodeGenerationTest(BaseTest):
    """Test Python code generation capabilities."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run Python code generation test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Extract code from response
        code = self._extract_code(response)
        
        # Validate and score
        is_valid = self.validate_result(code)
        score = self.calculate_score(code)
        
        status = TestStatus.PASSED if is_valid and score > 0.6 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'extracted_code': code,
                'model': model,
                'syntax_valid': self._check_syntax(code),
                'has_function': self._has_function_definition(code),
                'has_docstring': self._has_docstring(code),
                'complexity_score': self._calculate_complexity_score(code)
            }
        )
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from response."""
        # Look for code blocks
        code_blocks = re.findall(r'```python\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        # Look for code blocks without language specification
        code_blocks = re.findall(r'```\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        # Look for indented code
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('class '):
                in_code = True
            
            if in_code:
                if line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                    if not (line.strip().startswith('def ') or line.strip().startswith('class ')):
                        break
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines)
        
        return response
    
    def _check_syntax(self, code: str) -> bool:
        """Check if code has valid Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _has_function_definition(self, code: str) -> bool:
        """Check if code contains function definition."""
        return 'def ' in code
    
    def _has_docstring(self, code: str) -> bool:
        """Check if code contains docstring."""
        return '"""' in code or "'''" in code
    
    def _calculate_complexity_score(self, code: str) -> float:
        """Calculate code complexity score."""
        if not code:
            return 0.0
        
        lines = [line.strip() for line in code.split('\n') if line.strip()]
        
        # Basic complexity indicators
        complexity_indicators = {
            'for ': 0.2,
            'while ': 0.2,
            'if ': 0.1,
            'elif ': 0.1,
            'try:': 0.15,
            'except': 0.15,
            'def ': 0.1,
            'class ': 0.2,
            'return ': 0.05
        }
        
        complexity_score = 0.0
        for line in lines:
            for indicator, score in complexity_indicators.items():
                if indicator in line:
                    complexity_score += score
        
        return min(complexity_score, 1.0)
    
    def validate_result(self, result: str) -> bool:
        """Validate code generation result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check syntax
        if not self._check_syntax(result):
            return False
        
        # Check minimum requirements
        requirements = self.get_validation_criteria()
        
        if requirements.get('requires_function', False):
            if not self._has_function_definition(result):
                return False
        
        if requirements.get('requires_docstring', False):
            if not self._has_docstring(result):
                return False
        
        return True
    
    def calculate_score(self, result: str) -> float:
        """Calculate code quality score."""
        if not self.validate_result(result):
            return 0.0
        
        score = 0.0
        
        # Syntax correctness (40%)
        if self._check_syntax(result):
            score += 0.4
        
        # Function definition (20%)
        if self._has_function_definition(result):
            score += 0.2
        
        # Documentation (20%)
        if self._has_docstring(result):
            score += 0.2
        
        # Complexity (20%)
        complexity = self._calculate_complexity_score(result)
        score += complexity * 0.2
        
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


class FunctionImplementationTest(BaseTest):
    """Test specific function implementation."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run function implementation test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Extract code
        code = self._extract_code(response)
        
        # Test the function if possible
        test_results = await self._test_function(code)
        
        # Validate and score
        is_valid = self.validate_result(code)
        score = self.calculate_score(code, test_results)
        
        status = TestStatus.PASSED if is_valid and score > 0.7 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'extracted_code': code,
                'model': model,
                'test_results': test_results,
                'syntax_valid': self._check_syntax(code),
                'function_name': self._get_function_name(code)
            }
        )
    
    async def _test_function(self, code: str) -> Dict[str, Any]:
        """Test the implemented function with test cases."""
        test_cases = self.config.get('test_cases', [])
        if not test_cases:
            return {'tested': False, 'reason': 'No test cases provided'}
        
        try:
            # Create a local namespace for execution
            namespace = {}
            exec(code, namespace)
            
            # Find the function
            function_name = self._get_function_name(code)
            if not function_name or function_name not in namespace:
                return {'tested': False, 'reason': 'Function not found in namespace'}
            
            func = namespace[function_name]
            
            # Run test cases
            results = []
            for test_case in test_cases:
                try:
                    args = test_case.get('args', [])
                    kwargs = test_case.get('kwargs', {})
                    expected = test_case.get('expected')
                    
                    result = func(*args, **kwargs)
                    passed = result == expected
                    
                    results.append({
                        'args': args,
                        'kwargs': kwargs,
                        'expected': expected,
                        'actual': result,
                        'passed': passed
                    })
                except Exception as e:
                    results.append({
                        'args': args,
                        'kwargs': kwargs,
                        'error': str(e),
                        'passed': False
                    })
            
            passed_count = sum(1 for r in results if r.get('passed', False))
            
            return {
                'tested': True,
                'total_tests': len(results),
                'passed_tests': passed_count,
                'success_rate': passed_count / len(results) if results else 0,
                'results': results
            }
            
        except Exception as e:
            return {'tested': False, 'reason': f'Execution error: {str(e)}'}
    
    def _get_function_name(self, code: str) -> Optional[str]:
        """Extract function name from code."""
        match = re.search(r'def\s+(\w+)\s*\(', code)
        return match.group(1) if match else None
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from response."""
        # Look for code blocks
        code_blocks = re.findall(r'```python\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        # Look for code blocks without language specification
        code_blocks = re.findall(r'```\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        return response
    
    def _check_syntax(self, code: str) -> bool:
        """Check if code has valid Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def validate_result(self, result: str) -> bool:
        """Validate function implementation result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check syntax
        if not self._check_syntax(result):
            return False
        
        # Check if function is defined
        if not self._get_function_name(result):
            return False
        
        return True
    
    def calculate_score(self, result: str, test_results: Dict[str, Any]) -> float:
        """Calculate function implementation score."""
        if not self.validate_result(result):
            return 0.0
        
        score = 0.0
        
        # Syntax correctness (30%)
        if self._check_syntax(result):
            score += 0.3
        
        # Function definition (20%)
        if self._get_function_name(result):
            score += 0.2
        
        # Test results (50%)
        if test_results.get('tested', False):
            success_rate = test_results.get('success_rate', 0)
            score += success_rate * 0.5
        else:
            # If we can't test, give partial credit for having a function
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


class CodeGenerationTests:
    """Collection of code generation tests."""
    
    @staticmethod
    def get_fibonacci_test() -> FunctionImplementationTest:
        """Get Fibonacci function implementation test."""
        config = {
            'prompt': 'Write a Python function called "fibonacci" that returns the nth Fibonacci number. Include proper documentation.',
            'system_prompt': 'You are a skilled Python programmer. Write clean, well-documented code.',
            'validation': {
                'requires_function': True,
                'requires_docstring': True
            },
            'test_cases': [
                {'args': [0], 'expected': 0},
                {'args': [1], 'expected': 1},
                {'args': [2], 'expected': 1},
                {'args': [3], 'expected': 2},
                {'args': [4], 'expected': 3},
                {'args': [5], 'expected': 5},
                {'args': [10], 'expected': 55}
            ]
        }
        return FunctionImplementationTest(
            name='fibonacci_function',
            description='Implement Fibonacci function with test cases',
            config=config
        )
    
    @staticmethod
    def get_prime_check_test() -> FunctionImplementationTest:
        """Get prime number check function test."""
        config = {
            'prompt': 'Write a Python function called "is_prime" that checks if a number is prime. Include proper documentation.',
            'system_prompt': 'You are a skilled Python programmer. Write efficient, well-documented code.',
            'validation': {
                'requires_function': True,
                'requires_docstring': True
            },
            'test_cases': [
                {'args': [2], 'expected': True},
                {'args': [3], 'expected': True},
                {'args': [4], 'expected': False},
                {'args': [5], 'expected': True},
                {'args': [6], 'expected': False},
                {'args': [17], 'expected': True},
                {'args': [18], 'expected': False},
                {'args': [1], 'expected': False}
            ]
        }
        return FunctionImplementationTest(
            name='is_prime_function',
            description='Implement prime number check function',
            config=config
        )
    
    @staticmethod
    def get_sorting_test() -> FunctionImplementationTest:
        """Get sorting algorithm implementation test."""
        config = {
            'prompt': 'Write a Python function called "bubble_sort" that sorts a list of numbers using bubble sort algorithm. Include proper documentation.',
            'system_prompt': 'You are a skilled Python programmer. Write clear, educational code with good documentation.',
            'validation': {
                'requires_function': True,
                'requires_docstring': True
            },
            'test_cases': [
                {'args': [[]], 'expected': []},
                {'args': [[1]], 'expected': [1]},
                {'args': [[3, 1, 2]], 'expected': [1, 2, 3]},
                {'args': [[5, 2, 8, 1, 9]], 'expected': [1, 2, 5, 8, 9]},
                {'args': [[1, 2, 3, 4, 5]], 'expected': [1, 2, 3, 4, 5]},
                {'args': [[5, 4, 3, 2, 1]], 'expected': [1, 2, 3, 4, 5]}
            ]
        }
        return FunctionImplementationTest(
            name='bubble_sort_function',
            description='Implement bubble sort algorithm',
            config=config
        )
    
    @staticmethod
    def get_class_design_test() -> PythonCodeGenerationTest:
        """Get class design test."""
        config = {
            'prompt': 'Design a Python class called "BankAccount" with methods to deposit, withdraw, and check balance. Include proper documentation.',
            'system_prompt': 'You are a skilled Python programmer. Write object-oriented code with proper encapsulation.',
            'validation': {
                'requires_function': True,
                'requires_docstring': True
            },
            'expected_length': 200,
            'min_length': 100
        }
        return PythonCodeGenerationTest(
            name='bank_account_class',
            description='Design a BankAccount class with OOP principles',
            config=config
        )
    
    @staticmethod
    def get_all_tests() -> List[BaseTest]:
        """Get all code generation tests."""
        return [
            CodeGenerationTests.get_fibonacci_test(),
            CodeGenerationTests.get_prime_check_test(),
            CodeGenerationTests.get_sorting_test(),
            CodeGenerationTests.get_class_design_test()
        ]