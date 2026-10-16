"""
Core service layer for coding evaluation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os
from dataclasses import asdict

from .models import (
    CodingProblem,
    CodeSubmission,
    EvaluationResult,
    EvaluationSession,
    ProgrammingLanguage,
    ProblemDifficulty,
    TestCase
)
from .evaluator import CodeEvaluator, AdvancedCodeEvaluator
from .executor import CodeExecutor, BrowserCodeExecutor

class CodingEvaluationService:
    """Main service for coding evaluation operations"""
    
    def __init__(self, use_advanced_evaluator: bool = True):
        self.evaluator = AdvancedCodeEvaluator() if use_advanced_evaluator else CodeEvaluator()
        self.sessions: Dict[str, EvaluationSession] = {}
        self.data_dir = "data/coding_evaluation"
        self._ensure_data_directory()
        self._load_problems()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(f"{self.data_dir}/problems", exist_ok=True)
        os.makedirs(f"{self.data_dir}/sessions", exist_ok=True)
        os.makedirs(f"{self.data_dir}/results", exist_ok=True)
    
    def _load_problems(self):
        """Load problems from data directory"""
        problems_dir = f"{self.data_dir}/problems"
        if os.path.exists(problems_dir):
            for filename in os.listdir(problems_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(problems_dir, filename), 'r') as f:
                            problem_data = json.load(f)
                            problem = self._dict_to_problem(problem_data)
                            self.evaluator.add_problem(problem)
                    except Exception as e:
                        print(f"Error loading problem {filename}: {e}")
    
    def _dict_to_problem(self, data: Dict[str, Any]) -> CodingProblem:
        """Convert dictionary to CodingProblem object"""
        test_cases = [
            TestCase(
                id=tc['id'],
                input_data=tc['input_data'],
                expected_output=tc['expected_output'],
                time_limit=tc.get('time_limit', 5.0),
                memory_limit=tc.get('memory_limit', 128),
                description=tc.get('description'),
                hidden=tc.get('hidden', False)
            )
            for tc in data['test_cases']
        ]
        
        return CodingProblem(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            difficulty=ProblemDifficulty(data['difficulty']),
            languages=[ProgrammingLanguage(lang) for lang in data['languages']],
            test_cases=test_cases,
            starter_code=data.get('starter_code', {}),
            solution=data.get('solution', {}),
            tags=data.get('tags', []),
            time_limit=data.get('time_limit', 5.0),
            memory_limit=data.get('memory_limit', 128)
        )
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new evaluation session"""
        session_id = f"session_{int(datetime.now().timestamp())}"
        session = EvaluationSession(
            id=session_id,
            user_id=user_id
        )
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[EvaluationSession]:
        """Get an evaluation session"""
        return self.sessions.get(session_id)
    
    def get_problems(self, difficulty: Optional[ProblemDifficulty] = None,
                    language: Optional[ProgrammingLanguage] = None,
                    tags: Optional[List[str]] = None) -> List[CodingProblem]:
        """Get problems with optional filters"""
        problems = self.evaluator.get_all_problems()
        
        if difficulty:
            problems = [p for p in problems if p.difficulty == difficulty]
        
        if language:
            problems = [p for p in problems if language in p.languages]
        
        if tags:
            problems = [p for p in problems if any(tag in p.tags for tag in tags)]
        
        return problems
    
    def get_problem(self, problem_id: str) -> Optional[CodingProblem]:
        """Get a specific problem"""
        return self.evaluator.get_problem(problem_id)
    
    def submit_code(self, session_id: str, code: str, language: ProgrammingLanguage,
                   problem_id: str, model_name: Optional[str] = None) -> EvaluationResult:
        """Submit code for evaluation"""
        session = self.get_session(session_id)
        if not session:
            return EvaluationResult(
                submission_id="unknown",
                score=0.0,
                passed_tests=0,
                total_tests=0,
                error_message="Session not found"
            )
        
        # Create submission
        submission = CodeSubmission(
            id=f"sub_{session_id}_{int(datetime.now().timestamp())}",
            code=code,
            language=language,
            problem_id=problem_id,
            user_id=session.user_id
        )
        
        # Add to session
        session.submissions.append(submission)
        session.updated_at = datetime.now()
        
        # Evaluate
        if model_name:
            result = self.evaluate_with_model_internal(
                code, language, problem_id, session.user_id, model_name
            )
        else:
            result = self.evaluator.evaluate_code(
                code, language, problem_id, session.user_id
            )
        
        # Update session with best score
        if result.score > session.best_score:
            session.best_score = result.score
        
        # Save result
        self._save_result(result)
        
        return result
    
    def get_supported_languages(self) -> List[ProgrammingLanguage]:
        """Get supported programming languages"""
        return self.evaluator.get_supported_languages()
    
    def validate_syntax(self, code: str, language: ProgrammingLanguage) -> bool:
        """Validate code syntax"""
        return self.evaluator.validate_code_syntax(code, language)
    
    def generate_browser_runner(self, code: str, language: ProgrammingLanguage,
                              problem_id: str) -> str:
        """Generate HTML for browser execution"""
        return self.evaluator.generate_browser_runner(code, language, problem_id)
    
    def get_evaluation_history(self, session_id: str) -> List[EvaluationResult]:
        """Get evaluation history for a session"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        # Load results from disk
        results = []
        results_dir = f"{self.data_dir}/results"
        
        for submission in session.submissions:
            result_file = f"{results_dir}/{submission.id}.json"
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                        # Convert back to EvaluationResult
                        results.append(self._dict_to_evaluation_result(result_data))
                except Exception as e:
                    print(f"Error loading result {submission.id}: {e}")
        
        return results
    
    def evaluate_with_model(self, session_id: str, code: str, language: ProgrammingLanguage,
                           problem_id: str, model_name: str) -> EvaluationResult:
        """Evaluate code with specific model"""
        return self.submit_code(session_id, code, language, problem_id, model_name)
    
    def evaluate_with_model_internal(self, code: str, language: ProgrammingLanguage,
                                   problem_id: str, user_id: str, model_name: str) -> EvaluationResult:
        """Internal method to evaluate code with a specific model"""
        # For now, this is a placeholder that uses the standard evaluator
        # In a full implementation, this would integrate with the unified LLM service
        # to get model-specific feedback or use the model for code review
        
        result = self.evaluator.evaluate_code(code, language, problem_id, user_id)
        
        # Add model-specific information to the result
        if hasattr(result, 'feedback'):
            result.feedback = f"[Evaluated with {model_name}] {result.feedback or 'Code evaluation completed'}"
        
        return result
    
    def _dict_to_evaluation_result(self, data: Dict[str, Any]) -> EvaluationResult:
        """Convert dictionary to EvaluationResult"""
        # This is a simplified conversion
        return EvaluationResult(
            submission_id=data['submission_id'],
            score=data['score'],
            passed_tests=data['passed_tests'],
            total_tests=data['total_tests'],
            execution_time=data.get('execution_time'),
            memory_usage=data.get('memory_usage'),
            error_message=data.get('error_message'),
            feedback=data.get('feedback')
        )
    
    def get_code_quality_metrics(self, code: str, language: ProgrammingLanguage) -> Dict[str, float]:
        """Get code quality metrics"""
        if isinstance(self.evaluator, AdvancedCodeEvaluator):
            return self.evaluator.evaluate_code_quality(code, language)
        return {}
    
    def benchmark_performance(self, code: str, language: ProgrammingLanguage,
                            problem_id: str) -> Dict[str, float]:
        """Benchmark code performance"""
        if isinstance(self.evaluator, AdvancedCodeEvaluator):
            return self.evaluator.benchmark_performance(code, language, problem_id)
        return {}
    
    def add_problem(self, problem: CodingProblem) -> bool:
        """Add a new problem"""
        try:
            self.evaluator.add_problem(problem)
            self._save_problem(problem)
            return True
        except Exception as e:
            print(f"Error adding problem: {e}")
            return False
    
    def _save_problem(self, problem: CodingProblem):
        """Save problem to disk"""
        problem_file = f"{self.data_dir}/problems/{problem.id}.json"
        with open(problem_file, 'w') as f:
            json.dump(asdict(problem), f, indent=2, default=str)
    
    def _save_result(self, result: EvaluationResult):
        """Save evaluation result to disk"""
        result_file = f"{self.data_dir}/results/{result.submission_id}.json"
        with open(result_file, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        results = self.get_evaluation_history(session_id)
        
        if not results:
            return {
                'total_submissions': 0,
                'best_score': 0.0,
                'average_score': 0.0,
                'problems_attempted': 0,
                'problems_solved': 0
            }
        
        scores = [r.score for r in results]
        problems_attempted = len(set(r.submission_id.split('_')[2] for r in results))
        problems_solved = len([r for r in results if r.score >= 1.0])
        
        return {
            'total_submissions': len(results),
            'best_score': max(scores),
            'average_score': sum(scores) / len(scores),
            'problems_attempted': problems_attempted,
            'problems_solved': problems_solved,
            'languages_used': list(set(session.language.value for session in self.sessions.values() if session.language))
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.evaluator.cleanup()

class ProblemGenerator:
    """Generates coding problems automatically"""
    
    def __init__(self):
        self.templates = {
            'basic': {
                'title': 'Basic {concept} Problem',
                'description': 'Write a function that {description}',
                'difficulty': ProblemDifficulty.EASY,
                'languages': [ProgrammingLanguage.PYTHON, ProgrammingLanguage.JAVASCRIPT]
            },
            'intermediate': {
                'title': 'Intermediate {concept} Problem',
                'description': 'Implement {description} with {constraint}',
                'difficulty': ProblemDifficulty.MEDIUM,
                'languages': [ProgrammingLanguage.PYTHON, ProgrammingLanguage.JAVASCRIPT, ProgrammingLanguage.JAVA]
            },
            'advanced': {
                'title': 'Advanced {concept} Problem',
                'description': 'Design and implement {description} that {requirement}',
                'difficulty': ProblemDifficulty.HARD,
                'languages': [ProgrammingLanguage.PYTHON, ProgrammingLanguage.JAVASCRIPT, ProgrammingLanguage.JAVA, ProgrammingLanguage.CPP]
            }
        }
    
    def generate_problem(self, concept: str, template_type: str = 'basic') -> CodingProblem:
        """Generate a coding problem"""
        if template_type not in self.templates:
            template_type = 'basic'
        
        template = self.templates[template_type]
        problem_id = f"gen_{concept}_{template_type}_{int(datetime.now().timestamp())}"
        
        # Generate test cases based on concept
        test_cases = self._generate_test_cases(concept)
        
        return CodingProblem(
            id=problem_id,
            title=template['title'].format(concept=concept),
            description=template['description'].format(description=f"solves {concept} problems"),
            difficulty=template['difficulty'],
            languages=template['languages'],
            test_cases=test_cases,
            tags=[concept, template_type]
        )
    
    def _generate_test_cases(self, concept: str) -> List[TestCase]:
        """Generate test cases for a concept"""
        # This is a simplified implementation
        # In practice, you'd have more sophisticated test case generation
        
        if concept == 'fibonacci':
            return [
                TestCase(id="1", input_data="0", expected_output="0"),
                TestCase(id="2", input_data="1", expected_output="1"),
                TestCase(id="3", input_data="5", expected_output="5"),
                TestCase(id="4", input_data="10", expected_output="55")
            ]
        elif concept == 'factorial':
            return [
                TestCase(id="1", input_data="0", expected_output="1"),
                TestCase(id="2", input_data="1", expected_output="1"),
                TestCase(id="3", input_data="5", expected_output="120"),
                TestCase(id="4", input_data="7", expected_output="5040")
            ]
        elif concept == 'palindrome':
            return [
                TestCase(id="1", input_data="racecar", expected_output="True"),
                TestCase(id="2", input_data="hello", expected_output="False"),
                TestCase(id="3", input_data="madam", expected_output="True"),
                TestCase(id="4", input_data="python", expected_output="False")
            ]
        else:
            # Generic test cases
            return [
                TestCase(id="1", input_data="test1", expected_output="result1"),
                TestCase(id="2", input_data="test2", expected_output="result2")
            ]