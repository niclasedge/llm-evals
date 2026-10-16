"""
Integration with the existing LLM evaluation framework
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import time
import json
from datetime import datetime

from ..llm_evaluation.test_framework.base_test import BaseTest, TestResult, TestStatus
from ..llm_evaluation.test_framework.test_runner import TestRunner
from ..llm_evaluation.llm_service import LLMService

from .models import (
    CodeSubmission,
    EvaluationResult,
    CodingProblem,
    ProgrammingLanguage,
    ProblemDifficulty
)
from .service import CodingEvaluationService
from .evaluator import CodeEvaluator

@dataclass
class CodingTestCase:
    """Test case for LLM coding evaluation"""
    problem_id: str
    problem_title: str
    difficulty: str
    language: str
    description: str
    expected_approach: str
    test_cases_count: int

class CodingEvaluationTest(BaseTest):
    """LLM test for coding problem solving"""
    
    def __init__(self, problem: CodingProblem, language: ProgrammingLanguage):
        self.problem = problem
        self.language = language
        self.coding_service = CodingEvaluationService()
        
        super().__init__(
            name=f"coding_{problem.id}_{language.value}",
            description=f"Solve {problem.title} in {language.value}",
            tags=["coding", problem.difficulty.value, language.value] + problem.tags
        )
    
    async def execute(self, llm_service: LLMService) -> TestResult:
        """Execute the coding test"""
        start_time = time.time()
        
        try:
            # Create prompt for the LLM
            prompt = self._create_coding_prompt()
            
            # Get response from LLM
            response = await llm_service.generate_response(prompt)
            
            # Extract code from response
            code = self._extract_code_from_response(response)
            
            if not code:
                return TestResult(
                    test_name=self.name,
                    status=TestStatus.FAILED,
                    score=0.0,
                    execution_time=time.time() - start_time,
                    error_message="No code found in LLM response",
                    details={"response": response}
                )
            
            # Create session and submit code
            session_id = self.coding_service.create_session()
            evaluation_result = self.coding_service.submit_code(
                session_id=session_id,
                code=code,
                language=self.language,
                problem_id=self.problem.id
            )
            
            # Convert to test result
            return self._convert_to_test_result(evaluation_result, response, time.time() - start_time)
            
        except Exception as e:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                score=0.0,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _create_coding_prompt(self) -> str:
        """Create prompt for the LLM to solve the coding problem"""
        visible_test_cases = [tc for tc in self.problem.test_cases if not tc.hidden]
        
        prompt = f"""
You are a skilled programmer. Please solve the following coding problem in {self.language.value}.

**Problem: {self.problem.title}**

**Description:**
{self.problem.description}

**Difficulty:** {self.problem.difficulty.value}

**Constraints:**
- Time limit: {self.problem.time_limit} seconds
- Memory limit: {self.problem.memory_limit} MB

**Example Test Cases:**
"""
        
        for i, test_case in enumerate(visible_test_cases[:3]):  # Show first 3 test cases
            prompt += f"""
Test Case {i+1}:
Input: {test_case.input_data}
Expected Output: {test_case.expected_output}
"""
        
        prompt += f"""

**Requirements:**
1. Write clean, efficient code in {self.language.value}
2. Handle all edge cases
3. Follow the input/output format exactly
4. Optimize for the given time and memory constraints

**Response Format:**
Please provide your solution in the following format:

```{self.language.value}
[Your code here]
```

Explain your approach briefly and then provide the complete, working solution.
"""
        
        return prompt
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract code from LLM response"""
        # Look for code blocks
        import re
        
        # Try to find code blocks with language specification
        pattern = f"```{self.language.value}\\s*\\n(.*?)\\n```"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # Try generic code blocks
        pattern = r"```\s*\n(.*?)\n```"
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Try to find code between specific markers
        markers = [
            (f"# {self.language.value} solution", "\n\n"),
            ("def ", "\n\n"),
            ("function ", "\n\n"),
            ("class ", "\n\n"),
            ("#include", "\n\n")
        ]
        
        for start_marker, end_marker in markers:
            start_idx = response.lower().find(start_marker.lower())
            if start_idx != -1:
                end_idx = response.find(end_marker, start_idx)
                if end_idx == -1:
                    end_idx = len(response)
                return response[start_idx:end_idx].strip()
        
        return None
    
    def _convert_to_test_result(self, evaluation_result: EvaluationResult, 
                               llm_response: str, total_time: float) -> TestResult:
        """Convert coding evaluation result to test result"""
        status = TestStatus.PASSED if evaluation_result.score >= 0.8 else TestStatus.FAILED
        
        if evaluation_result.error_message:
            status = TestStatus.ERROR
        
        details = {
            "llm_response": llm_response,
            "code_score": evaluation_result.score,
            "passed_tests": evaluation_result.passed_tests,
            "total_tests": evaluation_result.total_tests,
            "execution_time": evaluation_result.execution_time,
            "feedback": evaluation_result.feedback,
            "test_results": [asdict(tr) for tr in evaluation_result.test_results]
        }
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=evaluation_result.score,
            execution_time=total_time,
            error_message=evaluation_result.error_message,
            details=details
        )

class CodingTestSuite:
    """Test suite for coding evaluations"""
    
    def __init__(self):
        self.coding_service = CodingEvaluationService()
        self.tests: List[CodingEvaluationTest] = []
    
    def add_problem_tests(self, problem: CodingProblem, 
                         languages: Optional[List[ProgrammingLanguage]] = None):
        """Add tests for a problem in specified languages"""
        if languages is None:
            languages = problem.languages
        
        for language in languages:
            if language in problem.languages:
                test = CodingEvaluationTest(problem, language)
                self.tests.append(test)
    
    def add_all_problems(self, difficulty_filter: Optional[ProblemDifficulty] = None,
                        language_filter: Optional[ProgrammingLanguage] = None):
        """Add tests for all available problems"""
        problems = self.coding_service.get_problems(
            difficulty=difficulty_filter,
            language=language_filter
        )
        
        for problem in problems:
            languages = [language_filter] if language_filter else problem.languages
            self.add_problem_tests(problem, languages)
    
    def get_tests(self) -> List[CodingEvaluationTest]:
        """Get all coding tests"""
        return self.tests
    
    def get_test_configs(self) -> List[Dict[str, Any]]:
        """Get test configurations for the test runner"""
        configs = []
        
        for test in self.tests:
            config = {
                "name": test.name,
                "description": test.description,
                "tags": test.tags,
                "problem_id": test.problem.id,
                "problem_title": test.problem.title,
                "language": test.language.value,
                "difficulty": test.problem.difficulty.value,
                "timeout": test.problem.time_limit + 30,  # Extra time for LLM processing
                "expected_score_threshold": 0.8
            }
            configs.append(config)
        
        return configs

class CodingEvaluationRunner:
    """Runner for coding evaluation tests"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.test_suite = CodingTestSuite()
        self.results: List[TestResult] = []
    
    async def run_coding_evaluation(self, problems: Optional[List[str]] = None,
                                   languages: Optional[List[str]] = None,
                                   difficulty: Optional[str] = None) -> Dict[str, Any]:
        """Run coding evaluation tests"""
        # Setup test suite
        if problems:
            coding_service = CodingEvaluationService()
            for problem_id in problems:
                problem = coding_service.get_problem(problem_id)
                if problem:
                    lang_filters = [ProgrammingLanguage(lang) for lang in languages] if languages else None
                    self.test_suite.add_problem_tests(problem, lang_filters)
        else:
            difficulty_filter = ProblemDifficulty(difficulty) if difficulty else None
            language_filter = ProgrammingLanguage(languages[0]) if languages and len(languages) == 1 else None
            self.test_suite.add_all_problems(difficulty_filter, language_filter)
        
        # Run tests
        tests = self.test_suite.get_tests()
        results = []
        
        for test in tests:
            print(f"Running test: {test.name}")
            result = await test.execute(self.llm_service)
            results.append(result)
            self.results.append(result)
        
        # Generate summary
        return self._generate_summary(results)
    
    def _generate_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate evaluation summary"""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status == TestStatus.FAILED)
        error_tests = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        avg_score = sum(r.score for r in results) / total_tests if total_tests > 0 else 0
        avg_time = sum(r.execution_time for r in results) / total_tests if total_tests > 0 else 0
        
        # Group by difficulty and language
        by_difficulty = {}
        by_language = {}
        
        for result in results:
            # Extract difficulty and language from test name
            parts = result.test_name.split('_')
            if len(parts) >= 3:
                difficulty = parts[1] if len(parts) > 1 else "unknown"
                language = parts[2] if len(parts) > 2 else "unknown"
                
                if difficulty not in by_difficulty:
                    by_difficulty[difficulty] = {"passed": 0, "total": 0, "avg_score": 0}
                if language not in by_language:
                    by_language[language] = {"passed": 0, "total": 0, "avg_score": 0}
                
                by_difficulty[difficulty]["total"] += 1
                by_language[language]["total"] += 1
                
                if result.status == TestStatus.PASSED:
                    by_difficulty[difficulty]["passed"] += 1
                    by_language[language]["passed"] += 1
                
                by_difficulty[difficulty]["avg_score"] += result.score
                by_language[language]["avg_score"] += result.score
        
        # Calculate averages
        for stats in by_difficulty.values():
            if stats["total"] > 0:
                stats["avg_score"] /= stats["total"]
        
        for stats in by_language.values():
            if stats["total"] > 0:
                stats["avg_score"] /= stats["total"]
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "average_score": avg_score,
                "average_execution_time": avg_time
            },
            "by_difficulty": by_difficulty,
            "by_language": by_language,
            "detailed_results": [asdict(r) for r in results],
            "timestamp": datetime.now().isoformat()
        }
    
    def save_results(self, filename: str = None):
        """Save results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"coding_evaluation_results_{timestamp}.json"
        
        summary = self._generate_summary(self.results)
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"Results saved to {filename}")

# Integration function for the main evaluator
def create_coding_evaluation_tests() -> List[BaseTest]:
    """Create coding evaluation tests for the main test framework"""
    test_suite = CodingTestSuite()
    
    # Add basic problems for testing
    test_suite.add_all_problems(
        difficulty_filter=ProblemDifficulty.EASY,
        language_filter=ProgrammingLanguage.PYTHON
    )
    
    return test_suite.get_tests()

def run_coding_evaluation_standalone():
    """Standalone function to run coding evaluations"""
    from ..llm_evaluation.llm_service import LLMService
    import asyncio
    
    async def main():
        # Initialize LLM service (would use actual config)
        llm_service = LLMService()
        
        # Create runner
        runner = CodingEvaluationRunner(llm_service)
        
        # Run evaluation
        results = await runner.run_coding_evaluation(
            problems=["fibonacci", "palindrome"],
            languages=["python"],
            difficulty="easy"
        )
        
        print("Coding Evaluation Results:")
        print(json.dumps(results["summary"], indent=2))
        
        # Save results
        runner.save_results()
    
    asyncio.run(main())

if __name__ == "__main__":
    run_coding_evaluation_standalone()