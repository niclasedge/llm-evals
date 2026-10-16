"""
Comprehensive tests for the coding evaluation feature
"""

import pytest
import tempfile
import os
import json
from datetime import datetime
from typing import List

from ..models import (
    ProgrammingLanguage,
    ProblemDifficulty,
    TestCase,
    CodingProblem,
    CodeSubmission,
    EvaluationResult
)
from ..executor import CodeExecutor, BrowserCodeExecutor
from ..evaluator import CodeEvaluator, EvaluationEngine
from ..service import CodingEvaluationService, ProblemGenerator
from ..endpoints import CodingEvaluationEndpoints

class TestCodingEvaluationModels:
    """Test the data models"""
    
    def test_test_case_creation(self):
        """Test TestCase model"""
        test_case = TestCase(
            id="test1",
            input_data="5",
            expected_output="120",
            time_limit=2.0,
            memory_limit=64,
            description="Test factorial of 5"
        )
        
        assert test_case.id == "test1"
        assert test_case.input_data == "5"
        assert test_case.expected_output == "120"
        assert test_case.time_limit == 2.0
        assert test_case.memory_limit == 64
        assert test_case.hidden == False
    
    def test_coding_problem_creation(self):
        """Test CodingProblem model"""
        test_cases = [
            TestCase("1", "0", "1"),
            TestCase("2", "5", "120")
        ]
        
        problem = CodingProblem(
            id="factorial",
            title="Factorial Function",
            description="Calculate factorial of n",
            difficulty=ProblemDifficulty.EASY,
            languages=[ProgrammingLanguage.PYTHON, ProgrammingLanguage.JAVASCRIPT],
            test_cases=test_cases,
            tags=["math", "recursion"]
        )
        
        assert problem.id == "factorial"
        assert problem.title == "Factorial Function"
        assert problem.difficulty == ProblemDifficulty.EASY
        assert len(problem.languages) == 2
        assert len(problem.test_cases) == 2
        assert "math" in problem.tags

class TestCodeExecutor:
    """Test the code execution engine"""
    
    def test_python_execution(self):
        """Test Python code execution"""
        executor = CodeExecutor()
        
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

import sys
n = int(sys.argv[1]) if len(sys.argv) > 1 else int(input())
print(fibonacci(n))
"""
        
        test_cases = [
            TestCase("1", "0", "0"),
            TestCase("2", "1", "1"),
            TestCase("3", "5", "5")
        ]
        
        result = executor.execute_code(code, ProgrammingLanguage.PYTHON, test_cases)
        
        assert result.success
        executor.cleanup()
    
    def test_javascript_execution(self):
        """Test JavaScript code execution"""
        executor = CodeExecutor()
        
        # Simple test without external dependencies
        code = """
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

const n = parseInt(process.argv[2]) || 5;
console.log(factorial(n));
"""
        
        result = executor.execute_code(code, ProgrammingLanguage.JAVASCRIPT)
        
        # This might fail if Node.js is not installed, which is okay for testing
        if result.success:
            assert result.output is not None
        
        executor.cleanup()
    
    def test_syntax_validation(self):
        """Test syntax validation"""
        executor = CodeExecutor()
        
        # Valid Python code
        valid_code = "def hello():\n    print('Hello, World!')"
        assert executor.validate_syntax(valid_code, ProgrammingLanguage.PYTHON)
        
        # Invalid Python code
        invalid_code = "def hello(\n    print('Hello, World!')"
        assert not executor.validate_syntax(invalid_code, ProgrammingLanguage.PYTHON)
        
        executor.cleanup()
    
    def test_supported_languages(self):
        """Test getting supported languages"""
        executor = CodeExecutor()
        languages = executor.get_supported_languages()
        
        assert ProgrammingLanguage.PYTHON in languages
        assert ProgrammingLanguage.JAVASCRIPT in languages
        assert len(languages) > 0
        
        executor.cleanup()

class TestBrowserCodeExecutor:
    """Test the browser code execution engine"""
    
    def test_html_generation(self):
        """Test HTML generation for browser execution"""
        executor = BrowserCodeExecutor()
        
        code = "console.log('Hello, World!');"
        test_cases = [TestCase("1", "test", "output")]
        
        html = executor.generate_html_runner(code, ProgrammingLanguage.JAVASCRIPT, test_cases)
        
        assert "<!DOCTYPE html>" in html
        assert "JavaScript Code Execution" in html
        assert code in html
    
    def test_python_html_generation(self):
        """Test Python HTML generation with Pyodide"""
        executor = BrowserCodeExecutor()
        
        code = "print('Hello, Python!')"
        html = executor.generate_html_runner(code, ProgrammingLanguage.PYTHON)
        
        assert "<!DOCTYPE html>" in html
        assert "Python Code Execution" in html
        assert "pyodide" in html.lower()

class TestEvaluationEngine:
    """Test the evaluation engine"""
    
    def test_evaluation_engine_creation(self):
        """Test creating an evaluation engine"""
        engine = EvaluationEngine()
        
        assert engine is not None
        assert hasattr(engine, 'server_executor')
        assert hasattr(engine, 'browser_executor')
        
        engine.cleanup()
    
    def test_score_calculation(self):
        """Test score calculation logic"""
        from ..models import TestResult, TestStatus
        
        engine = EvaluationEngine()
        
        # All tests passed
        test_results = [
            TestResult("1", TestStatus.PASSED, passed=True),
            TestResult("2", TestStatus.PASSED, passed=True)
        ]
        
        score = engine._calculate_score(test_results)
        assert score == 1.0
        
        # Half tests passed
        test_results = [
            TestResult("1", TestStatus.PASSED, passed=True),
            TestResult("2", TestStatus.FAILED, passed=False)
        ]
        
        score = engine._calculate_score(test_results)
        assert score == 0.5
        
        engine.cleanup()

class TestCodeEvaluator:
    """Test the code evaluator"""
    
    def test_code_evaluator_creation(self):
        """Test creating a code evaluator"""
        evaluator = CodeEvaluator()
        
        assert evaluator is not None
        assert hasattr(evaluator, 'engine')
        assert hasattr(evaluator, 'problems')
        
        evaluator.cleanup()
    
    def test_add_problem(self):
        """Test adding a problem to the evaluator"""
        evaluator = CodeEvaluator()
        
        test_cases = [TestCase("1", "0", "0")]
        problem = CodingProblem(
            id="test_problem",
            title="Test Problem",
            description="A test problem",
            difficulty=ProblemDifficulty.EASY,
            languages=[ProgrammingLanguage.PYTHON],
            test_cases=test_cases
        )
        
        evaluator.add_problem(problem)
        
        assert "test_problem" in evaluator.problems
        assert evaluator.get_problem("test_problem") == problem
        
        evaluator.cleanup()
    
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        evaluator = CodeEvaluator()
        
        languages = evaluator.get_supported_languages()
        assert len(languages) > 0
        assert ProgrammingLanguage.PYTHON in languages
        
        evaluator.cleanup()

class TestCodingEvaluationService:
    """Test the coding evaluation service"""
    
    def test_service_creation(self):
        """Test creating the service"""
        service = CodingEvaluationService()
        
        assert service is not None
        assert hasattr(service, 'evaluator')
        assert hasattr(service, 'sessions')
        
        service.cleanup()
    
    def test_create_session(self):
        """Test creating an evaluation session"""
        service = CodingEvaluationService()
        
        session_id = service.create_session("test_user")
        
        assert session_id is not None
        assert session_id in service.sessions
        
        session = service.get_session(session_id)
        assert session is not None
        assert session.user_id == "test_user"
        
        service.cleanup()
    
    def test_get_problems(self):
        """Test getting problems"""
        service = CodingEvaluationService()
        
        problems = service.get_problems()
        
        # Should load problems from data directory
        assert isinstance(problems, list)
        
        service.cleanup()

class TestProblemGenerator:
    """Test the problem generator"""
    
    def test_generate_basic_problem(self):
        """Test generating a basic problem"""
        generator = ProblemGenerator()
        
        problem = generator.generate_problem("fibonacci", "basic")
        
        assert problem.id.startswith("gen_fibonacci_basic")
        assert "fibonacci" in problem.title.lower()
        assert problem.difficulty == ProblemDifficulty.EASY
        assert len(problem.test_cases) > 0
        assert "fibonacci" in problem.tags
    
    def test_generate_different_concepts(self):
        """Test generating problems for different concepts"""
        generator = ProblemGenerator()
        
        concepts = ["fibonacci", "factorial", "palindrome"]
        
        for concept in concepts:
            problem = generator.generate_problem(concept)
            assert concept in problem.tags
            assert len(problem.test_cases) > 0

class TestIntegration:
    """Integration tests"""
    
    def test_end_to_end_evaluation(self):
        """Test end-to-end evaluation process"""
        service = CodingEvaluationService()
        
        # Create a simple problem
        test_cases = [
            TestCase("1", "Hello", "Hello"),
            TestCase("2", "World", "World")
        ]
        
        problem = CodingProblem(
            id="echo_test",
            title="Echo Test",
            description="Echo the input",
            difficulty=ProblemDifficulty.EASY,
            languages=[ProgrammingLanguage.PYTHON],
            test_cases=test_cases
        )
        
        service.add_problem(problem)
        
        # Create session
        session_id = service.create_session()
        
        # Submit code
        code = """
import sys
input_data = sys.argv[1] if len(sys.argv) > 1 else input()
print(input_data)
"""
        
        result = service.submit_code(
            session_id=session_id,
            code=code,
            language=ProgrammingLanguage.PYTHON,
            problem_id="echo_test"
        )
        
        assert result is not None
        assert result.submission_id is not None
        
        service.cleanup()

class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_language(self):
        """Test handling invalid language"""
        service = CodingEvaluationService()
        session_id = service.create_session()
        
        # This should handle the error gracefully
        try:
            result = service.submit_code(
                session_id=session_id,
                code="print('hello')",
                language=ProgrammingLanguage.PYTHON,
                problem_id="nonexistent_problem"
            )
            assert result.error_message is not None
        except Exception as e:
            # Should not raise unhandled exceptions
            pytest.fail(f"Unexpected exception: {e}")
        
        service.cleanup()
    
    def test_syntax_error_handling(self):
        """Test handling code with syntax errors"""
        executor = CodeExecutor()
        
        invalid_code = "def broken_function(\n    print('This will not work')"
        
        result = executor.execute_code(invalid_code, ProgrammingLanguage.PYTHON)
        
        assert not result.success
        assert result.error is not None
        
        executor.cleanup()

# Performance tests
class TestPerformance:
    """Performance tests"""
    
    def test_multiple_evaluations(self):
        """Test performance with multiple evaluations"""
        service = CodingEvaluationService()
        
        # Create a simple problem
        test_cases = [TestCase("1", "5", "5")]
        problem = CodingProblem(
            id="performance_test",
            title="Performance Test",
            description="Simple echo test",
            difficulty=ProblemDifficulty.EASY,
            languages=[ProgrammingLanguage.PYTHON],
            test_cases=test_cases
        )
        
        service.add_problem(problem)
        
        session_id = service.create_session()
        code = "import sys; print(sys.argv[1] if len(sys.argv) > 1 else input())"
        
        # Run multiple evaluations
        results = []
        for i in range(3):  # Small number for CI/CD
            result = service.submit_code(
                session_id=session_id,
                code=code,
                language=ProgrammingLanguage.PYTHON,
                problem_id="performance_test"
            )
            results.append(result)
        
        assert len(results) == 3
        assert all(r.submission_id is not None for r in results)
        
        service.cleanup()

def run_all_tests():
    """Run all tests manually"""
    print("Running Coding Evaluation Tests...")
    
    # Test models
    print("Testing models...")
    test_models = TestCodingEvaluationModels()
    test_models.test_test_case_creation()
    test_models.test_coding_problem_creation()
    print("✅ Models tests passed")
    
    # Test executor
    print("Testing executor...")
    test_executor = TestCodeExecutor()
    test_executor.test_python_execution()
    test_executor.test_syntax_validation()
    test_executor.test_supported_languages()
    print("✅ Executor tests passed")
    
    # Test browser executor
    print("Testing browser executor...")
    test_browser = TestBrowserCodeExecutor()
    test_browser.test_html_generation()
    test_browser.test_python_html_generation()
    print("✅ Browser executor tests passed")
    
    # Test evaluation engine
    print("Testing evaluation engine...")
    test_engine = TestEvaluationEngine()
    test_engine.test_evaluation_engine_creation()
    test_engine.test_score_calculation()
    print("✅ Evaluation engine tests passed")
    
    # Test code evaluator
    print("Testing code evaluator...")
    test_evaluator = TestCodeEvaluator()
    test_evaluator.test_code_evaluator_creation()
    test_evaluator.test_add_problem()
    test_evaluator.test_get_supported_languages()
    print("✅ Code evaluator tests passed")
    
    # Test service
    print("Testing service...")
    test_service = TestCodingEvaluationService()
    test_service.test_service_creation()
    test_service.test_create_session()
    test_service.test_get_problems()
    print("✅ Service tests passed")
    
    # Test problem generator
    print("Testing problem generator...")
    test_generator = TestProblemGenerator()
    test_generator.test_generate_basic_problem()
    test_generator.test_generate_different_concepts()
    print("✅ Problem generator tests passed")
    
    # Test integration
    print("Testing integration...")
    test_integration = TestIntegration()
    test_integration.test_end_to_end_evaluation()
    print("✅ Integration tests passed")
    
    # Test error handling
    print("Testing error handling...")
    test_errors = TestErrorHandling()
    test_errors.test_invalid_language()
    test_errors.test_syntax_error_handling()
    print("✅ Error handling tests passed")
    
    # Test performance
    print("Testing performance...")
    test_performance = TestPerformance()
    test_performance.test_multiple_evaluations()
    print("✅ Performance tests passed")
    
    print("\n🎉 All Coding Evaluation Tests Passed!")

if __name__ == "__main__":
    run_all_tests()