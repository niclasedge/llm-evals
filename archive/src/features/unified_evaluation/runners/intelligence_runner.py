"""
Intelligence evaluation runner

This module provides the runner for intelligence/reasoning evaluation that integrates
with the existing intelligence evaluation system.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.core.llm_unified_config import ModelConfig
# from src.features.llm_evaluation.intelligence_evaluator import IntelligenceEvaluator
# from src.features.llm_evaluation.intelligence_tests.test_runner import IntelligenceTestRunner

from ..models import (
    EvaluationRequest,
    ModelResult,
    EvaluationMetrics
)

logger = logging.getLogger(__name__)


class IntelligenceRunner:
    """
    Runner for intelligence/reasoning evaluations
    
    This class integrates with the existing intelligence evaluation system
    and provides a unified interface for running intelligence evaluations.
    """
    
    def __init__(self):
        """Initialize the intelligence runner"""
        # self.evaluator = IntelligenceEvaluator()
        # self.test_runner = IntelligenceTestRunner()
    
    async def run_evaluation(self, model_config: ModelConfig, request: EvaluationRequest) -> ModelResult:
        """
        Run intelligence evaluation for a specific model
        
        Args:
            model_config: Model configuration
            request: Evaluation request
            
        Returns:
            Model evaluation result
        """
        start_time = datetime.now()
        
        try:
            # Get test categories
            categories = self._get_test_categories(request)
            
            if not categories:
                raise ValueError("No intelligence test categories found")
            
            # Run evaluations
            results = await self._run_intelligence_evaluations(model_config, categories, request)
            
            # Calculate metrics
            metrics = self._calculate_metrics(results)
            
            # Generate details
            details = self._generate_details(results, categories)
            
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
            logger.error(f"Intelligence evaluation failed for {model_config.name}: {str(e)}")
            return ModelResult(
                model_name=model_config.name,
                provider=model_config.provider,
                model_id=model_config.model_id,
                metrics=EvaluationMetrics(),
                errors=[str(e)]
            )
    
    def _get_test_categories(self, request: EvaluationRequest) -> List[str]:
        """Get intelligence test categories"""
        # Default categories from the intelligence tests
        default_categories = ['logic', 'creative', 'pattern', 'reasoning', 'math']
        
        # Filter by requested categories if specified
        if request.categories:
            categories = [cat for cat in request.categories if cat in default_categories]
        else:
            categories = default_categories
        
        return categories
    
    async def _run_intelligence_evaluations(self, model_config: ModelConfig, categories: List[str], request: EvaluationRequest) -> List[Dict]:
        """Run intelligence evaluations for all categories"""
        results = []
        
        for category in categories:
            try:
                # Get tests for this category
                tests = self._get_tests_for_category(category)
                
                for test in tests:
                    # Simulate intelligence evaluation
                    result = await self._simulate_intelligence_evaluation(
                        model_config, test, category, request
                    )
                    results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to evaluate intelligence category {category}: {str(e)}")
                results.append({
                    'category': category,
                    'test_id': f"{category}_error",
                    'status': 'error',
                    'error': str(e),
                    'score': 0.0
                })
        
        return results
    
    def _get_tests_for_category(self, category: str) -> List[Dict]:
        """Get tests for a specific category"""
        test_definitions = {
            'logic': [
                {'id': 'logical_reasoning', 'name': 'Logical Reasoning', 'difficulty': 'medium'},
                {'id': 'syllogism', 'name': 'Syllogistic Reasoning', 'difficulty': 'medium'},
                {'id': 'conditional_logic', 'name': 'Conditional Logic', 'difficulty': 'hard'}
            ],
            'creative': [
                {'id': 'creative_writing', 'name': 'Creative Writing', 'difficulty': 'easy'},
                {'id': 'alternative_uses', 'name': 'Alternative Uses Task', 'difficulty': 'medium'},
                {'id': 'creative_problem_solving', 'name': 'Creative Problem Solving', 'difficulty': 'hard'}
            ],
            'pattern': [
                {'id': 'sequence_completion', 'name': 'Sequence Completion', 'difficulty': 'medium'},
                {'id': 'pattern_recognition', 'name': 'Pattern Recognition', 'difficulty': 'medium'},
                {'id': 'analogical_reasoning', 'name': 'Analogical Reasoning', 'difficulty': 'hard'}
            ],
            'reasoning': [
                {'id': 'deductive_reasoning', 'name': 'Deductive Reasoning', 'difficulty': 'medium'},
                {'id': 'inductive_reasoning', 'name': 'Inductive Reasoning', 'difficulty': 'hard'},
                {'id': 'causal_reasoning', 'name': 'Causal Reasoning', 'difficulty': 'hard'}
            ],
            'math': [
                {'id': 'arithmetic', 'name': 'Arithmetic Operations', 'difficulty': 'easy'},
                {'id': 'algebra', 'name': 'Algebraic Reasoning', 'difficulty': 'medium'},
                {'id': 'geometry', 'name': 'Geometric Reasoning', 'difficulty': 'hard'}
            ]
        }
        
        return test_definitions.get(category, [])
    
    async def _simulate_intelligence_evaluation(self, model_config: ModelConfig, test: Dict, category: str, request: EvaluationRequest) -> Dict:
        """
        Simulate intelligence evaluation
        
        This is a placeholder until full intelligence evaluation is implemented.
        In a real implementation, this would:
        1. Present the test to the model
        2. Evaluate the model's response
        3. Score based on correctness and reasoning quality
        """
        
        # Simulate evaluation delay
        await asyncio.sleep(0.4)
        
        # Simulate different success rates based on model and test
        import random
        random.seed(hash(f"{model_config.name}_{test.get('id', 'unknown')}_{category}"))
        
        # Base success rate depends on model capabilities
        base_success_rate = 0.6  # Assume reasonable intelligence capabilities
        
        # Adjust for test difficulty
        difficulty = test.get('difficulty', 'medium')
        if difficulty == 'easy':
            success_rate = base_success_rate * 0.9
        elif difficulty == 'medium':
            success_rate = base_success_rate * 0.7
        else:  # hard
            success_rate = base_success_rate * 0.5
        
        # Adjust for category
        category_multipliers = {
            'logic': 0.8,
            'creative': 0.9,
            'pattern': 0.7,
            'reasoning': 0.6,
            'math': 0.8
        }
        success_rate *= category_multipliers.get(category, 0.7)
        
        # Simulate test execution
        is_success = random.random() < success_rate
        
        # Generate scores
        if is_success:
            accuracy_score = random.uniform(0.7, 1.0)
            reasoning_score = random.uniform(0.6, 0.9)
            creativity_score = random.uniform(0.5, 0.8) if category == 'creative' else random.uniform(0.3, 0.6)
        else:
            accuracy_score = random.uniform(0.0, 0.4)
            reasoning_score = random.uniform(0.0, 0.3)
            creativity_score = random.uniform(0.0, 0.2)
        
        overall_score = (accuracy_score + reasoning_score + creativity_score) / 3
        
        return {
            'test_id': test.get('id', 'unknown'),
            'test_name': test.get('name', 'Unknown Test'),
            'category': category,
            'difficulty': difficulty,
            'status': 'completed',
            'overall_score': overall_score,
            'accuracy_score': accuracy_score,
            'reasoning_score': reasoning_score,
            'creativity_score': creativity_score,
            'passed': is_success,
            'execution_time': random.uniform(1.0, 4.0),
            'model_response': f"Simulated intelligence response for {test.get('id', 'unknown')}"
        }
    
    def _calculate_metrics(self, results: List[Dict]) -> EvaluationMetrics:
        """Calculate evaluation metrics from results"""
        if not results:
            return EvaluationMetrics()
        
        total_tests = len(results)
        passed_tests = len([r for r in results if r.get('passed', False)])
        failed_tests = total_tests - passed_tests
        error_tests = len([r for r in results if r.get('status') == 'error'])
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        average_score = sum(r.get('overall_score', 0) for r in results) / total_tests
        average_time = sum(r.get('execution_time', 0) for r in results) / total_tests
        
        return EvaluationMetrics(
            accuracy=average_score,
            success_rate=success_rate,
            average_time=average_time,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests
        )
    
    def _generate_details(self, results: List[Dict], categories: List[str]) -> Dict:
        """Generate detailed results"""
        details = {
            'evaluation_type': 'intelligence',
            'categories_evaluated': len(categories),
            'categories_tested': categories,
            'results_by_category': {},
            'results_by_difficulty': {},
            'results_by_test': {}
        }
        
        # Group results by category
        for result in results:
            category = result.get('category', 'unknown')
            if category not in details['results_by_category']:
                details['results_by_category'][category] = []
            details['results_by_category'][category].append(result)
        
        # Group results by difficulty
        for result in results:
            difficulty = result.get('difficulty', 'medium')
            if difficulty not in details['results_by_difficulty']:
                details['results_by_difficulty'][difficulty] = []
            details['results_by_difficulty'][difficulty].append(result)
        
        # Group results by test
        for result in results:
            test_id = result.get('test_id', 'unknown')
            details['results_by_test'][test_id] = result
        
        # Calculate category summaries
        category_summaries = {}
        for category in categories:
            category_results = details['results_by_category'].get(category, [])
            if category_results:
                category_summaries[category] = {
                    'total_tests': len(category_results),
                    'passed_tests': len([r for r in category_results if r.get('passed', False)]),
                    'average_score': sum(r.get('overall_score', 0) for r in category_results) / len(category_results),
                    'success_rate': len([r for r in category_results if r.get('passed', False)]) / len(category_results)
                }
        
        details['category_summaries'] = category_summaries
        
        return details