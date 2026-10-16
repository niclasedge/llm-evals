"""
Code evaluation engine and logic
"""

import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .models import (
    CodeSubmission,
    EvaluationResult,
    TestCase,
    TestResult,
    TestStatus,
    ProgrammingLanguage,
    CodingProblem
)
from .executor import CodeExecutor, BrowserCodeExecutor

class EvaluationEngine:
    """Main evaluation engine for coding submissions"""
    
    def __init__(self):
        self.server_executor = CodeExecutor()
        self.browser_executor = BrowserCodeExecutor()
        self.evaluation_history: List[EvaluationResult] = []
    
    def evaluate_submission(self, submission: CodeSubmission, 
                          problem: CodingProblem) -> EvaluationResult:
        """Evaluate a code submission against a problem"""
        start_time = time.time()
        
        try:
            # Validate language support
            if submission.language not in problem.languages:
                return EvaluationResult(
                    submission_id=submission.id,
                    score=0.0,
                    passed_tests=0,
                    total_tests=len(problem.test_cases),
                    error_message=f"Language {submission.language.value} not supported for this problem"
                )
            
            # Run test cases
            test_results = self._run_test_cases(submission, problem.test_cases)
            
            # Calculate score
            score = self._calculate_score(test_results)
            
            # Generate feedback
            feedback = self._generate_feedback(test_results, problem)
            
            execution_time = time.time() - start_time
            
            result = EvaluationResult(
                submission_id=submission.id,
                score=score,
                passed_tests=sum(1 for r in test_results if r.passed),
                total_tests=len(test_results),
                test_results=test_results,
                execution_time=execution_time,
                feedback=feedback
            )
            
            self.evaluation_history.append(result)
            return result
            
        except Exception as e:
            return EvaluationResult(
                submission_id=submission.id,
                score=0.0,
                passed_tests=0,
                total_tests=len(problem.test_cases),
                error_message=f"Evaluation error: {str(e)}"
            )
    
    def _run_test_cases(self, submission: CodeSubmission, 
                       test_cases: List[TestCase]) -> List[TestResult]:
        """Run all test cases for a submission"""
        results = []
        
        for test_case in test_cases:
            try:
                # Execute code with test case input
                execution_result = self.server_executor.execute_code(
                    submission.code, 
                    submission.language,
                    [test_case]
                )
                
                if execution_result.success:
                    # For successful execution, check the output
                    # This is a simplified approach - in practice, we'd need
                    # more sophisticated output comparison
                    actual_output = execution_result.output.strip() if execution_result.output else ""
                    expected_output = test_case.expected_output.strip()
                    
                    passed = actual_output == expected_output
                    
                    results.append(TestResult(
                        test_case_id=test_case.id,
                        status=TestStatus.PASSED if passed else TestStatus.FAILED,
                        actual_output=actual_output,
                        execution_time=execution_result.execution_time,
                        passed=passed
                    ))
                else:
                    results.append(TestResult(
                        test_case_id=test_case.id,
                        status=TestStatus.ERROR,
                        error_message=execution_result.error,
                        passed=False
                    ))
                    
            except Exception as e:
                results.append(TestResult(
                    test_case_id=test_case.id,
                    status=TestStatus.ERROR,
                    error_message=str(e),
                    passed=False
                ))
        
        return results
    
    def _calculate_score(self, test_results: List[TestResult]) -> float:
        """Calculate score based on test results"""
        if not test_results:
            return 0.0
        
        passed_tests = sum(1 for result in test_results if result.passed)
        total_tests = len(test_results)
        
        # Basic scoring: percentage of passed tests
        base_score = passed_tests / total_tests
        
        # Bonus for performance (if execution time is available)
        performance_bonus = 0.0
        execution_times = [r.execution_time for r in test_results if r.execution_time]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            # Bonus for fast execution (under 1 second)
            if avg_time < 1.0:
                performance_bonus = 0.1 * (1.0 - avg_time)
        
        return min(1.0, base_score + performance_bonus)
    
    def _generate_feedback(self, test_results: List[TestResult], 
                          problem: CodingProblem) -> str:
        """Generate feedback for the submission"""
        passed_tests = sum(1 for result in test_results if result.passed)
        total_tests = len(test_results)
        
        feedback = []
        
        if passed_tests == total_tests:
            feedback.append("🎉 Congratulations! All tests passed!")
        else:
            feedback.append(f"📊 {passed_tests}/{total_tests} tests passed")
        
        # Add specific feedback for failed tests
        failed_tests = [r for r in test_results if not r.passed]
        if failed_tests:
            feedback.append("\n❌ Failed tests:")
            for result in failed_tests[:3]:  # Show first 3 failures
                if result.status == TestStatus.FAILED:
                    feedback.append(f"  • Test {result.test_case_id}: Expected '{result.actual_output}', got different output")
                elif result.status == TestStatus.ERROR:
                    feedback.append(f"  • Test {result.test_case_id}: {result.error_message}")
                elif result.status == TestStatus.TIMEOUT:
                    feedback.append(f"  • Test {result.test_case_id}: Execution timeout")
        
        # Performance feedback
        execution_times = [r.execution_time for r in test_results if r.execution_time]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            if avg_time > 2.0:
                feedback.append(f"\n⚡ Performance: Consider optimizing - average execution time: {avg_time:.2f}s")
            elif avg_time < 0.5:
                feedback.append(f"\n⚡ Great performance! Average execution time: {avg_time:.2f}s")
        
        return "\n".join(feedback)
    
    def get_evaluation_history(self) -> List[EvaluationResult]:
        """Get evaluation history"""
        return self.evaluation_history.copy()
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self.server_executor, 'cleanup'):
            self.server_executor.cleanup()

class CodeEvaluator:
    """High-level code evaluator interface"""
    
    def __init__(self):
        self.engine = EvaluationEngine()
        self.problems: Dict[str, CodingProblem] = {}
    
    def add_problem(self, problem: CodingProblem):
        """Add a coding problem to the evaluator"""
        self.problems[problem.id] = problem
    
    def evaluate_code(self, code: str, language: ProgrammingLanguage, 
                     problem_id: str, user_id: Optional[str] = None) -> EvaluationResult:
        """Evaluate code against a problem"""
        if problem_id not in self.problems:
            return EvaluationResult(
                submission_id="unknown",
                score=0.0,
                passed_tests=0,
                total_tests=0,
                error_message=f"Problem {problem_id} not found"
            )
        
        problem = self.problems[problem_id]
        
        # Create submission
        submission = CodeSubmission(
            id=f"sub_{int(time.time())}",
            code=code,
            language=language,
            problem_id=problem_id,
            user_id=user_id
        )
        
        return self.engine.evaluate_submission(submission, problem)
    
    def get_problem(self, problem_id: str) -> Optional[CodingProblem]:
        """Get a problem by ID"""
        return self.problems.get(problem_id)
    
    def get_all_problems(self) -> List[CodingProblem]:
        """Get all problems"""
        return list(self.problems.values())
    
    def get_supported_languages(self) -> List[ProgrammingLanguage]:
        """Get supported programming languages"""
        return self.engine.server_executor.get_supported_languages()
    
    def validate_code_syntax(self, code: str, language: ProgrammingLanguage) -> bool:
        """Validate code syntax"""
        return self.engine.server_executor.validate_syntax(code, language)
    
    def generate_browser_runner(self, code: str, language: ProgrammingLanguage, 
                              problem_id: str) -> str:
        """Generate HTML for browser-based code execution"""
        if problem_id not in self.problems:
            return "<html><body>Problem not found</body></html>"
        
        problem = self.problems[problem_id]
        return self.engine.browser_executor.generate_html_runner(
            code, language, problem.test_cases
        )
    
    def cleanup(self):
        """Clean up resources"""
        self.engine.cleanup()

class AdvancedCodeEvaluator(CodeEvaluator):
    """Advanced code evaluator with additional features"""
    
    def __init__(self):
        super().__init__()
        self.code_quality_metrics = {}
        self.performance_benchmarks = {}
    
    def evaluate_code_quality(self, code: str, language: ProgrammingLanguage) -> Dict[str, float]:
        """Evaluate code quality metrics"""
        metrics = {
            'readability': self._assess_readability(code),
            'complexity': self._assess_complexity(code),
            'maintainability': self._assess_maintainability(code),
            'style': self._assess_style(code, language)
        }
        
        self.code_quality_metrics[code] = metrics
        return metrics
    
    def _assess_readability(self, code: str) -> float:
        """Assess code readability (0.0 to 1.0)"""
        # Simple heuristics
        lines = code.split('\n')
        
        # Check for comments
        comment_ratio = sum(1 for line in lines if line.strip().startswith('#') or line.strip().startswith('//')) / len(lines)
        
        # Check for meaningful variable names
        meaningful_vars = 0
        total_vars = 0
        
        # This is a simplified assessment
        readability_score = 0.7 + (comment_ratio * 0.3)
        
        return min(1.0, readability_score)
    
    def _assess_complexity(self, code: str) -> float:
        """Assess code complexity (0.0 to 1.0, lower is better)"""
        # Count nested blocks, loops, conditions
        nesting_level = 0
        max_nesting = 0
        
        for char in code:
            if char == '{':
                nesting_level += 1
                max_nesting = max(max_nesting, nesting_level)
            elif char == '}':
                nesting_level -= 1
        
        # Normalize complexity (inverted so lower complexity = higher score)
        complexity_score = 1.0 - min(1.0, max_nesting / 10.0)
        
        return complexity_score
    
    def _assess_maintainability(self, code: str) -> float:
        """Assess code maintainability (0.0 to 1.0)"""
        # Check for function decomposition
        lines = code.split('\n')
        function_count = sum(1 for line in lines if 'def ' in line or 'function ' in line)
        
        # More functions usually means better maintainability
        maintainability_score = min(1.0, function_count / 5.0 + 0.5)
        
        return maintainability_score
    
    def _assess_style(self, code: str, language: ProgrammingLanguage) -> float:
        """Assess code style (0.0 to 1.0)"""
        # Check for consistent indentation, naming conventions, etc.
        lines = code.split('\n')
        
        # Check indentation consistency
        indentations = []
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indentations.append(indent)
        
        # Check if indentation is consistent
        if indentations:
            indent_consistency = 1.0 if len(set(indentations)) <= 2 else 0.5
        else:
            indent_consistency = 1.0
        
        return indent_consistency
    
    def benchmark_performance(self, code: str, language: ProgrammingLanguage, 
                            problem_id: str) -> Dict[str, float]:
        """Benchmark code performance"""
        if problem_id not in self.problems:
            return {}
        
        problem = self.problems[problem_id]
        
        # Run multiple times to get average performance
        execution_times = []
        memory_usage = []
        
        for _ in range(3):  # Run 3 times
            result = self.engine.server_executor.execute_code(
                code, language, problem.test_cases
            )
            
            if result.execution_time:
                execution_times.append(result.execution_time)
            if result.memory_usage:
                memory_usage.append(result.memory_usage)
        
        benchmarks = {}
        
        if execution_times:
            benchmarks['avg_execution_time'] = sum(execution_times) / len(execution_times)
            benchmarks['min_execution_time'] = min(execution_times)
            benchmarks['max_execution_time'] = max(execution_times)
        
        if memory_usage:
            benchmarks['avg_memory_usage'] = sum(memory_usage) / len(memory_usage)
            benchmarks['max_memory_usage'] = max(memory_usage)
        
        self.performance_benchmarks[f"{problem_id}_{language.value}"] = benchmarks
        
        return benchmarks