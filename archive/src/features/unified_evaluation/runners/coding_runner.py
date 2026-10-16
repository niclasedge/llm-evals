"""
Coding evaluation runner

This module provides the runner for coding evaluation that integrates
with the existing coding evaluation system.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.core.llm_unified_config import ModelConfig
from src.features.coding_evaluation.service import CodingEvaluationService
from src.features.coding_evaluation.models import ProgrammingLanguage, ProblemDifficulty

from ..models import (
    EvaluationRequest,
    ModelResult,
    EvaluationMetrics
)

logger = logging.getLogger(__name__)


class CodingRunner:
    """
    Runner for coding evaluations
    
    This class integrates with the existing coding evaluation system
    and provides a unified interface for running coding evaluations.
    """
    
    def __init__(self):
        """Initialize the coding runner"""
        self.service = CodingEvaluationService()
    
    async def run_evaluation(self, model_config: ModelConfig, request: EvaluationRequest) -> ModelResult:
        """
        Run coding evaluation for a specific model
        
        Args:
            model_config: Model configuration
            request: Evaluation request
            
        Returns:
            Model evaluation result
        """
        start_time = datetime.now()
        
        try:
            # Get problems to evaluate
            problems = self._get_problems(request)
            
            # Filter by language if specified
            if request.languages:
                problems = self._filter_by_language(problems, request.languages)
            
            # Filter by difficulty if specified
            if request.difficulty:
                problems = self._filter_by_difficulty(problems, request.difficulty)
            
            if not problems:
                raise ValueError("No problems found matching the criteria")
            
            # Run evaluations
            results = await self._run_problem_evaluations(model_config, problems, request)
            
            # Calculate metrics
            metrics = self._calculate_metrics(results)
            
            # Generate details
            details = self._generate_details(results, problems)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return ModelResult(
                model_name=model_config.name,
                provider=model_config.provider,
                model_id=model_config.model_id,
                metrics=metrics,
                details=details,
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"Coding evaluation failed for {model_config.name}: {str(e)}")
            return ModelResult(
                model_name=model_config.name,
                provider=model_config.provider,
                model_id=model_config.model_id,
                metrics=EvaluationMetrics(),
                errors=[str(e)]
            )
    
    def _get_problems(self, request: EvaluationRequest) -> List:
        """Get problems to evaluate"""
        try:
            all_problems = self.service.get_problems()
            
            # Filter by specific problems if requested
            if request.problems:
                problems = [p for p in all_problems if p.id in request.problems]
            else:
                problems = all_problems
                
            return problems
            
        except Exception as e:
            logger.error(f"Failed to get problems: {str(e)}")
            return []
    
    def _filter_by_language(self, problems: List, languages: List[str]) -> List:
        """Filter problems by supported languages"""
        filtered_problems = []
        
        for problem in problems:
            # Check if problem supports any of the requested languages
            problem_languages = [lang.value for lang in problem.languages]
            if any(lang in problem_languages for lang in languages):
                filtered_problems.append(problem)
        
        return filtered_problems
    
    def _filter_by_difficulty(self, problems: List, difficulty: str) -> List:
        """Filter problems by difficulty"""
        try:
            target_difficulty = ProblemDifficulty(difficulty.upper())
            return [p for p in problems if p.difficulty == target_difficulty]
        except ValueError:
            logger.warning(f"Invalid difficulty: {difficulty}")
            return problems
    
    async def _run_problem_evaluations(self, model_config: ModelConfig, problems: List, request: EvaluationRequest) -> List[Dict]:
        """Run evaluations for all problems"""
        results = []
        
        for problem in problems:
            # Determine which languages to test
            test_languages = self._get_test_languages(problem, request.languages)
            
            for language in test_languages:
                try:
                    # For now, simulate evaluation since full LLM integration isn't implemented
                    result = await self._simulate_problem_evaluation(
                        model_config, problem, language, request
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Failed to evaluate problem {problem.id} in {language}: {str(e)}")
                    results.append({
                        'problem_id': problem.id,
                        'language': language,
                        'status': 'error',
                        'error': str(e),
                        'score': 0.0
                    })
        
        return results
    
    def _get_test_languages(self, problem, requested_languages: Optional[List[str]]) -> List[str]:
        """Get languages to test for a problem"""
        problem_languages = [lang.value for lang in problem.languages]
        
        if requested_languages:
            # Test only requested languages that the problem supports
            return [lang for lang in requested_languages if lang in problem_languages]
        else:
            # Test all languages the problem supports
            return problem_languages
    
    async def _simulate_problem_evaluation(self, model_config: ModelConfig, problem, language: str, request: EvaluationRequest) -> Dict:
        """
        Simulate problem evaluation
        
        This is a placeholder until full LLM integration is implemented.
        In a real implementation, this would:
        1. Generate code using the LLM
        2. Execute the code with test cases
        3. Calculate scores based on test results
        """
        
        # Simulate evaluation delay
        await asyncio.sleep(0.1)
        
        # Simulate different success rates based on model and problem
        import random
        random.seed(hash(f"{model_config.name}_{problem.id}_{language}"))
        
        # Simulate success rate based on model capabilities
        base_success_rate = 0.7 if 'code' in model_config.capabilities else 0.4
        
        # Adjust for difficulty
        if problem.difficulty == ProblemDifficulty.EASY:
            success_rate = base_success_rate * 0.9
        elif problem.difficulty == ProblemDifficulty.MEDIUM:
            success_rate = base_success_rate * 0.7
        else:  # HARD
            success_rate = base_success_rate * 0.5
        
        # Simulate test case results
        test_cases = len(problem.test_cases)
        passed_tests = int(random.random() * test_cases * success_rate)
        
        return {
            'problem_id': problem.id,
            'problem_title': problem.title,
            'language': language,
            'difficulty': problem.difficulty.value,
            'total_tests': test_cases,
            'passed_tests': passed_tests,
            'failed_tests': test_cases - passed_tests,
            'status': 'completed',
            'score': passed_tests / test_cases if test_cases > 0 else 0.0,
            'execution_time': random.uniform(0.5, 3.0)
        }
    
    def _calculate_metrics(self, results: List[Dict]) -> EvaluationMetrics:
        """Calculate evaluation metrics from results"""
        if not results:
            return EvaluationMetrics()
        
        total_tests = sum(r.get('total_tests', 0) for r in results)
        passed_tests = sum(r.get('passed_tests', 0) for r in results)
        failed_tests = sum(r.get('failed_tests', 0) for r in results)
        error_tests = len([r for r in results if r.get('status') == 'error'])
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        average_time = sum(r.get('execution_time', 0) for r in results) / len(results)
        
        return EvaluationMetrics(
            accuracy=success_rate,
            success_rate=success_rate,
            average_time=average_time,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests
        )
    
    def _generate_details(self, results: List[Dict], problems: List) -> Dict:
        """Generate detailed results"""
        details = {
            'evaluation_type': 'coding',
            'problems_evaluated': len(problems),
            'languages_tested': list(set(r.get('language', 'unknown') for r in results)),
            'results_by_problem': {},
            'results_by_language': {}
        }
        
        # Group results by problem
        for result in results:
            problem_id = result.get('problem_id', 'unknown')
            if problem_id not in details['results_by_problem']:
                details['results_by_problem'][problem_id] = []
            details['results_by_problem'][problem_id].append(result)
        
        # Group results by language
        for result in results:
            language = result.get('language', 'unknown')
            if language not in details['results_by_language']:
                details['results_by_language'][language] = []
            details['results_by_language'][language].append(result)
        
        return details
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self.service, 'cleanup'):
            self.service.cleanup()