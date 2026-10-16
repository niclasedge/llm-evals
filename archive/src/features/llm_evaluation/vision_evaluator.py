# Vision Evaluator Module for LLM Vision Testing

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

from . import config
from . import llm_service
from .vision_test_cases import VisionTestCase, VisionTestCaseFactory


@dataclass
class VisionTestResult:
    """Container for vision test results."""
    test_name: str
    category: str
    model_provider: str
    model_identifier: str
    image_path: str
    query: str
    response: str
    score: float
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    expected_elements: Optional[List[str]] = None
    found_elements: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class VisionEvaluator:
    """Vision model evaluator for testing multimodal capabilities."""
    
    def __init__(self, test_config: Optional[Dict] = None):
        """Initialize the vision evaluator."""
        self.config = test_config or {}
        self.test_cases = []
        self.results = []
        
    def load_test_cases(self) -> List[VisionTestCase]:
        """Load all vision test cases."""
        if not self.test_cases:
            self.test_cases = VisionTestCaseFactory.get_all_test_cases()
        return self.test_cases
    
    def score_vision_response(self, response: str, test_case: VisionTestCase) -> Dict[str, Any]:
        """
        Score vision response based on expected elements.
        
        Args:
            response (str): The model's response
            test_case (VisionTestCase): The test case with expected elements
            
        Returns:
            dict: Scoring results with score, found_elements, and metadata
        """
        if not response or not test_case.expected_elements:
            return {
                'score': 0.0,
                'found_elements': [],
                'metadata': {'reason': 'No response or no expected elements'}
            }
        
        response_lower = response.lower()
        found_elements = []
        
        # Check for expected elements in response
        for element in test_case.expected_elements:
            if element.lower() in response_lower:
                found_elements.append(element)
        
        # Calculate score based on found elements
        score = len(found_elements) / len(test_case.expected_elements)
        
        # Apply category-specific scoring adjustments
        if test_case.category == "object_recognition":
            # Boost score for specific object mentions
            if any(obj in response_lower for obj in ["object", "item", "thing"]):
                score = min(1.0, score + 0.1)
        elif test_case.category == "scene_description":
            # Boost score for scene description words
            scene_words = ["room", "place", "scene", "area", "space", "environment"]
            if any(word in response_lower for word in scene_words):
                score = min(1.0, score + 0.1)
        elif test_case.category == "text_in_image":
            # Penalize hallucinated text
            if "cannot read" in response_lower or "no text" in response_lower:
                if not found_elements:
                    score = 0.5  # Partial credit for admitting uncertainty
        elif test_case.category == "visual_reasoning":
            # Boost score for reasoning keywords
            reasoning_words = ["because", "therefore", "logic", "pattern", "sequence"]
            if any(word in response_lower for word in reasoning_words):
                score = min(1.0, score + 0.15)
        elif test_case.category == "chart_analysis":
            # Boost score for data analysis terms
            data_words = ["data", "chart", "graph", "value", "trend", "increase", "decrease"]
            if any(word in response_lower for word in data_words):
                score = min(1.0, score + 0.1)
        
        return {
            'score': score,
            'found_elements': found_elements,
            'metadata': {
                'total_expected': len(test_case.expected_elements),
                'total_found': len(found_elements),
                'category': test_case.category,
                'response_length': len(response)
            }
        }
    
    async def run_single_test(self, test_case: VisionTestCase, model_provider: str, model_identifier: str) -> VisionTestResult:
        """
        Run a single vision test case.
        
        Args:
            test_case (VisionTestCase): The test case to run
            model_provider (str): The model provider ('ollama' or 'openrouter')
            model_identifier (str): The model identifier
            
        Returns:
            VisionTestResult: The test result
        """
        start_time = time.time()
        
        try:
            # Create vision agent
            agent = llm_service.get_vision_agent(model_provider, model_identifier)
            if not agent:
                return VisionTestResult(
                    test_name=test_case.name,
                    category=test_case.category,
                    model_provider=model_provider,
                    model_identifier=model_identifier,
                    image_path=test_case.image_path,
                    query=test_case.query,
                    response="",
                    score=0.0,
                    execution_time=time.time() - start_time,
                    success=False,
                    error_message="Failed to create vision agent"
                )
            
            # Run the vision query
            response = await llm_service.run_vision_query(agent, test_case.query, test_case.image_path)
            
            if response is None:
                return VisionTestResult(
                    test_name=test_case.name,
                    category=test_case.category,
                    model_provider=model_provider,
                    model_identifier=model_identifier,
                    image_path=test_case.image_path,
                    query=test_case.query,
                    response="",
                    score=0.0,
                    execution_time=time.time() - start_time,
                    success=False,
                    error_message="No response from model"
                )
            
            # Extract response text
            response_text = ""
            if hasattr(response, 'output'):
                response_text = response.output
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)
            
            # Score the response
            scoring_result = self.score_vision_response(response_text, test_case)
            
            return VisionTestResult(
                test_name=test_case.name,
                category=test_case.category,
                model_provider=model_provider,
                model_identifier=model_identifier,
                image_path=test_case.image_path,
                query=test_case.query,
                response=response_text,
                score=scoring_result['score'],
                execution_time=time.time() - start_time,
                success=True,
                expected_elements=test_case.expected_elements,
                found_elements=scoring_result['found_elements'],
                metadata=scoring_result['metadata']
            )
            
        except Exception as e:
            return VisionTestResult(
                test_name=test_case.name,
                category=test_case.category,
                model_provider=model_provider,
                model_identifier=model_identifier,
                image_path=test_case.image_path,
                query=test_case.query,
                response="",
                score=0.0,
                execution_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
    
    async def run_vision_evaluation(self, model_provider: str, model_identifier: str) -> Dict[str, Any]:
        """
        Run all vision tests for a specific model.
        
        Args:
            model_provider (str): The model provider ('ollama' or 'openrouter')
            model_identifier (str): The model identifier
            
        Returns:
            dict: Evaluation results with summary statistics
        """
        print(f"Running vision evaluation for {model_provider}/{model_identifier}")
        
        # Load test cases
        test_cases = self.load_test_cases()
        
        # Filter test cases based on availability of images
        available_test_cases = []
        for test_case in test_cases:
            image_path = Path(test_case.image_path)
            if image_path.exists():
                available_test_cases.append(test_case)
            else:
                print(f"Warning: Image not found for test '{test_case.name}': {test_case.image_path}")
        
        if not available_test_cases:
            print("No test cases with available images found")
            return {
                'model_provider': model_provider,
                'model_identifier': model_identifier,
                'results': [],
                'summary': {
                    'total_tests': 0,
                    'successful_tests': 0,
                    'failed_tests': 0,
                    'average_score': 0.0,
                    'average_execution_time': 0.0,
                    'category_scores': {}
                }
            }
        
        print(f"Running {len(available_test_cases)} vision tests...")
        
        # Run all tests
        results = []
        for test_case in available_test_cases:
            result = await self.run_single_test(test_case, model_provider, model_identifier)
            results.append(result)
            
            # Print progress
            status = "✅" if result.success else "❌"
            print(f"  {status} {test_case.name} ({test_case.category}): {result.score:.2f} ({result.execution_time:.2f}s)")
        
        # Calculate summary statistics
        summary = self.calculate_summary(results)
        
        return {
            'model_provider': model_provider,
            'model_identifier': model_identifier,
            'results': results,
            'summary': summary
        }
    
    def calculate_summary(self, results: List[VisionTestResult]) -> Dict[str, Any]:
        """Calculate summary statistics for vision test results."""
        if not results:
            return {
                'total_tests': 0,
                'successful_tests': 0,
                'failed_tests': 0,
                'average_score': 0.0,
                'average_execution_time': 0.0,
                'category_scores': {}
            }
        
        successful_results = [r for r in results if r.success]
        total_tests = len(results)
        successful_tests = len(successful_results)
        failed_tests = total_tests - successful_tests
        
        # Calculate averages
        average_score = sum(r.score for r in successful_results) / len(successful_results) if successful_results else 0.0
        average_execution_time = sum(r.execution_time for r in results) / len(results)
        
        # Calculate category-specific scores
        category_scores = {}
        categories = set(r.category for r in results)
        for category in categories:
            category_results = [r for r in results if r.category == category and r.success]
            if category_results:
                category_scores[category] = {
                    'average_score': sum(r.score for r in category_results) / len(category_results),
                    'test_count': len(category_results),
                    'success_rate': len(category_results) / len([r for r in results if r.category == category])
                }
        
        success_rate = successful_tests / total_tests if total_tests > 0 else 0.0
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'average_score': average_score,
            'average_execution_time': average_execution_time,
            'category_scores': category_scores
        }
    
    def save_results(self, results: Dict[str, Any], output_file: Path):
        """Save vision test results to JSON file."""
        # Convert VisionTestResult objects to dictionaries
        serializable_results = []
        for result in results.get('results', []):
            if isinstance(result, VisionTestResult):
                serializable_results.append({
                    'test_name': result.test_name,
                    'category': result.category,
                    'model_provider': result.model_provider,
                    'model_identifier': result.model_identifier,
                    'image_path': result.image_path,
                    'query': result.query,
                    'response': result.response,
                    'score': result.score,
                    'execution_time': result.execution_time,
                    'success': result.success,
                    'error_message': result.error_message,
                    'expected_elements': result.expected_elements,
                    'found_elements': result.found_elements,
                    'metadata': result.metadata
                })
        
        output_data = {
            'model_provider': results.get('model_provider'),
            'model_identifier': results.get('model_identifier'),
            'results': serializable_results,
            'summary': results.get('summary', {})
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Vision test results saved to: {output_file}")
    
    def generate_report(self, results: Dict[str, Any], output_file: Path) -> str:
        """Generate markdown report for vision test results."""
        report_lines = []
        
        # Header
        report_lines.append(f"# Vision Test Report")
        report_lines.append(f"")
        report_lines.append(f"**Model**: {results['model_provider']}/{results['model_identifier']}")
        report_lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"")
        
        # Summary
        summary = results['summary']
        report_lines.append(f"## Summary")
        report_lines.append(f"")
        report_lines.append(f"- **Total Tests**: {summary['total_tests']}")
        report_lines.append(f"- **Successful**: {summary['successful_tests']} ({summary['success_rate']:.1%})")
        report_lines.append(f"- **Failed**: {summary['failed_tests']}")
        report_lines.append(f"- **Average Score**: {summary['average_score']:.2f}")
        report_lines.append(f"- **Average Execution Time**: {summary['average_execution_time']:.2f}s")
        report_lines.append(f"")
        
        # Category Scores
        if summary['category_scores']:
            report_lines.append(f"## Category Performance")
            report_lines.append(f"")
            for category, scores in summary['category_scores'].items():
                report_lines.append(f"### {category.replace('_', ' ').title()}")
                report_lines.append(f"- **Average Score**: {scores['average_score']:.2f}")
                report_lines.append(f"- **Tests**: {scores['test_count']}")
                report_lines.append(f"- **Success Rate**: {scores['success_rate']:.1%}")
                report_lines.append(f"")
        
        # Detailed Results
        report_lines.append(f"## Detailed Results")
        report_lines.append(f"")
        
        for result in results['results']:
            if isinstance(result, dict):
                test_result = result
            else:
                test_result = {
                    'test_name': result.test_name,
                    'category': result.category,
                    'score': result.score,
                    'success': result.success,
                    'execution_time': result.execution_time,
                    'query': result.query,
                    'response': result.response,
                    'error_message': result.error_message
                }
            
            status = "✅ PASS" if test_result['success'] else "❌ FAIL"
            report_lines.append(f"### {test_result['test_name']} ({test_result['category']})")
            report_lines.append(f"")
            report_lines.append(f"**Status**: {status}")
            report_lines.append(f"**Score**: {test_result['score']:.2f}")
            report_lines.append(f"**Execution Time**: {test_result['execution_time']:.2f}s")
            report_lines.append(f"")
            report_lines.append(f"**Query**: {test_result['query']}")
            report_lines.append(f"")
            if test_result['success']:
                report_lines.append(f"**Response**: {test_result['response']}")
            else:
                report_lines.append(f"**Error**: {test_result['error_message']}")
            report_lines.append(f"")
            report_lines.append(f"---")
            report_lines.append(f"")
        
        report_content = "\n".join(report_lines)
        
        # Save report
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        print(f"Vision test report saved to: {output_file}")
        return report_content


async def main():
    """Main function for testing vision evaluator."""
    if not config.ENABLE_VISION_TESTING:
        print("Vision testing is disabled in configuration")
        return
    
    evaluator = VisionEvaluator()
    
    # Test with OpenRouter if available
    if config.ENABLE_OPENROUTER and config.OPENROUTER_VISION_MODELS_TO_TEST:
        model_identifier = config.OPENROUTER_VISION_MODELS_TO_TEST[0]
        print(f"Testing vision evaluation with OpenRouter model: {model_identifier}")
        
        results = await evaluator.run_vision_evaluation("openrouter", model_identifier)
        
        # Save results
        output_dir = Path("test_results")
        output_dir.mkdir(exist_ok=True)
        
        results_file = output_dir / "vision_evaluation_results.json"
        evaluator.save_results(results, results_file)
        
        report_file = output_dir / "vision_evaluation_report.md"
        evaluator.generate_report(results, report_file)


if __name__ == "__main__":
    asyncio.run(main())