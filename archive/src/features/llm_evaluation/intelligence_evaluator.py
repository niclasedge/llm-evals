"""
Intelligence evaluator for LLM intelligence testing.
Main entry point for running intelligence tests and generating reports.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from .intelligence_tests import IntelligenceTestRunner, IntelligenceResultAnalyzer
from .intelligence_tests.base_test import IntelligenceCategory
from .llm_service import get_llm_agent, run_query
from .config import (
    ENABLE_OLLAMA, ENABLE_OPENROUTER,
    OLLAMA_MODELS_TO_TEST, OPENROUTER_MODELS_TO_TEST
)


class IntelligenceEvaluator:
    """Main intelligence evaluator class."""
    
    def __init__(self, output_dir: str = "intelligence_test_results"):
        self.test_runner = IntelligenceTestRunner()
        self.result_analyzer = IntelligenceResultAnalyzer()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Store evaluation sessions
        self.evaluation_sessions = {}
    
    async def run_intelligence_evaluation(
        self,
        models: Optional[List[str]] = None,
        categories: Optional[List[IntelligenceCategory]] = None,
        complexity_levels: Optional[List[int]] = None,
        output_format: str = 'json',
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        Run comprehensive intelligence evaluation.
        
        Args:
            models: List of models to test (if None, uses config defaults)
            categories: List of intelligence categories to test
            complexity_levels: List of complexity levels to include
            output_format: Output format ('json', 'markdown', 'dict')
            save_results: Whether to save results to files
        
        Returns:
            Dict containing evaluation results
        """
        
        start_time = time.time()
        
        # Get models from config if not specified
        if models is None:
            models = []
            if ENABLE_OLLAMA:
                models.extend([f"ollama:{model}" for model in OLLAMA_MODELS_TO_TEST])
            if ENABLE_OPENROUTER:
                models.extend([f"openrouter:{model}" for model in OPENROUTER_MODELS_TO_TEST])
        
        if not models:
            raise ValueError("No models specified and none found in configuration")
        
        print(f"🧠 Starting Intelligence Evaluation for {len(models)} models...")
        print(f"📊 Available test categories: {[cat.value for cat in IntelligenceCategory]}")
        
        evaluation_results = {
            'evaluation_id': f"intelligence_eval_{int(time.time())}",
            'start_time': start_time,
            'models_tested': models,
            'categories_tested': [cat.value for cat in categories] if categories else 'all',
            'complexity_levels': complexity_levels or 'all',
            'model_results': {},
            'comparative_analysis': {},
            'summary': {}
        }
        
        # Run tests for each model
        for model_spec in models:
            print(f"\n🔍 Testing model: {model_spec}")
            
            try:
                # Create agent for the model
                agent = await self._create_model_agent(model_spec)
                
                # Run intelligence battery
                model_results = await self._run_model_intelligence_tests(
                    agent, model_spec, categories, complexity_levels
                )
                
                evaluation_results['model_results'][model_spec] = model_results
                
                # Add results to analyzer
                if model_results.get('detailed_results'):
                    from .intelligence_tests.base_test import IntelligenceTestResult, TestStatus
                    
                    # Convert dict results back to IntelligenceTestResult objects
                    test_results = []
                    for result_dict in model_results['detailed_results']:
                        # Create a minimal IntelligenceTestResult object
                        result = IntelligenceTestResult(
                            test_name=result_dict.get('test_name', ''),
                            status=TestStatus(result_dict.get('status', 'error')),
                            score=result_dict.get('score'),
                            details=result_dict.get('details', {}),
                            intelligence_category=IntelligenceCategory(result_dict.get('intelligence_category')) if result_dict.get('intelligence_category') else None,
                            complexity_level=result_dict.get('complexity_level'),
                            creativity_score=result_dict.get('creativity_score'),
                            logical_coherence=result_dict.get('logical_coherence')
                        )
                        test_results.append(result)
                    
                    self.result_analyzer.add_results(test_results)
                
                print(f"✅ Completed testing {model_spec}")
                
            except Exception as e:
                print(f"❌ Error testing {model_spec}: {e}")
                evaluation_results['model_results'][model_spec] = {
                    'error': str(e),
                    'status': 'failed'
                }
        
        # Perform comparative analysis
        if len(evaluation_results['model_results']) > 1:
            successful_models = [
                model for model, results in evaluation_results['model_results'].items()
                if 'error' not in results
            ]
            
            if len(successful_models) > 1:
                print(f"\n📈 Performing comparative analysis...")
                evaluation_results['comparative_analysis'] = self.result_analyzer.compare_models(successful_models)
        
        # Generate summary
        evaluation_results['summary'] = self._generate_evaluation_summary(evaluation_results)
        evaluation_results['end_time'] = time.time()
        evaluation_results['total_duration'] = evaluation_results['end_time'] - start_time
        
        # Save results if requested
        if save_results:
            await self._save_evaluation_results(evaluation_results, output_format)
        
        print(f"\n🎉 Intelligence evaluation completed in {evaluation_results['total_duration']:.2f} seconds")
        return evaluation_results
    
    async def _create_model_agent(self, model_spec: str):
        """Create an agent for the specified model."""
        if model_spec.startswith("ollama:"):
            model_name = model_spec[7:]  # Remove "ollama:" prefix
            return get_llm_agent("ollama", model_name)
        elif model_spec.startswith("openrouter:"):
            model_name = model_spec[11:]  # Remove "openrouter:" prefix
            return get_llm_agent("openrouter", model_name)
        else:
            # Default to trying as direct model name
            return get_llm_agent("ollama", model_spec)
    
    async def _run_model_intelligence_tests(
        self,
        agent,
        model_spec: str,
        categories: Optional[List[IntelligenceCategory]] = None,
        complexity_levels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Run intelligence tests for a specific model."""
        
        if categories:
            # Run specific categories
            all_results = []
            for category in categories:
                print(f"  🧪 Running {category.value} tests...")
                category_results = await self.test_runner.run_tests_by_category(
                    category, agent, model_spec
                )
                all_results.extend(category_results)
        else:
            # Run full intelligence battery
            print(f"  🧪 Running full intelligence battery...")
            battery_results = await self.test_runner.run_intelligence_battery(
                agent, model_spec
            )
            return battery_results
        
        # Filter by complexity if specified
        if complexity_levels:
            all_results = [r for r in all_results if r.complexity_level in complexity_levels]
        
        # Generate battery-like results structure
        return self._format_model_results(all_results, model_spec)
    
    def _format_model_results(self, results, model_spec: str) -> Dict[str, Any]:
        """Format results in battery-like structure."""
        if not results:
            return {'model': model_spec, 'error': 'No results generated'}
        
        # Group by category
        category_results = {}
        for result in results:
            if result.intelligence_category:
                category = result.intelligence_category.value
                if category not in category_results:
                    category_results[category] = []
                category_results[category].append(result)
        
        # Calculate statistics
        formatted_results = {
            'model': model_spec,
            'start_time': time.time(),
            'category_results': {},
            'overall_results': {},
            'detailed_results': [r.to_dict() for r in results]
        }
        
        # Process each category
        for category, category_tests in category_results.items():
            scores = [r.score for r in category_tests if r.score is not None]
            passed = sum(1 for r in category_tests if r.status.value == 'passed')
            
            formatted_results['category_results'][category] = {
                'test_count': len(category_tests),
                'average_score': sum(scores) / len(scores) if scores else 0.0,
                'pass_rate': passed / len(category_tests) if category_tests else 0.0,
                'results': [r.to_dict() for r in category_tests]
            }
        
        # Calculate overall statistics
        all_scores = [r.score for r in results if r.score is not None]
        all_passed = sum(1 for r in results if r.status.value == 'passed')
        
        formatted_results['overall_results'] = {
            'total_tests': len(results),
            'overall_score': sum(all_scores) / len(all_scores) if all_scores else 0.0,
            'overall_pass_rate': all_passed / len(results) if results else 0.0,
            'category_scores': {cat: data['average_score'] for cat, data in formatted_results['category_results'].items()}
        }
        
        formatted_results['execution_time'] = 0.0  # Would need to track this properly
        formatted_results['end_time'] = time.time()
        
        return formatted_results
    
    def _generate_evaluation_summary(self, evaluation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate evaluation summary."""
        model_results = evaluation_results.get('model_results', {})
        successful_models = [
            model for model, results in model_results.items()
            if 'error' not in results
        ]
        
        if not successful_models:
            return {'status': 'All models failed', 'successful_models': 0}
        
        # Calculate aggregate statistics
        all_scores = []
        all_pass_rates = []
        category_performance = {}
        
        for model in successful_models:
            results = model_results[model]
            overall = results.get('overall_results', {})
            
            if overall.get('overall_score') is not None:
                all_scores.append(overall['overall_score'])
            if overall.get('overall_pass_rate') is not None:
                all_pass_rates.append(overall['overall_pass_rate'])
            
            # Aggregate category performance
            for category, score in overall.get('category_scores', {}).items():
                if category not in category_performance:
                    category_performance[category] = []
                category_performance[category].append(score)
        
        # Find best and worst performers
        model_scores = {
            model: model_results[model].get('overall_results', {}).get('overall_score', 0)
            for model in successful_models
        }
        
        best_model = max(model_scores.items(), key=lambda x: x[1]) if model_scores else None
        worst_model = min(model_scores.items(), key=lambda x: x[1]) if model_scores else None
        
        return {
            'total_models_tested': len(model_results),
            'successful_models': len(successful_models),
            'failed_models': len(model_results) - len(successful_models),
            'average_score_across_models': sum(all_scores) / len(all_scores) if all_scores else 0.0,
            'average_pass_rate_across_models': sum(all_pass_rates) / len(all_pass_rates) if all_pass_rates else 0.0,
            'best_performing_model': {'model': best_model[0], 'score': best_model[1]} if best_model else None,
            'worst_performing_model': {'model': worst_model[0], 'score': worst_model[1]} if worst_model else None,
            'category_average_performance': {
                category: sum(scores) / len(scores)
                for category, scores in category_performance.items()
            },
            'status': 'completed'
        }
    
    async def _save_evaluation_results(self, results: Dict[str, Any], output_format: str = 'json'):
        """Save evaluation results to files."""
        evaluation_id = results.get('evaluation_id', 'unknown')
        
        # Save main results
        if output_format == 'json':
            results_file = self.output_dir / f"{evaluation_id}_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"💾 Results saved to: {results_file}")
        
        # Generate and save reports for each model
        for model_spec in results.get('model_results', {}):
            if 'error' not in results['model_results'][model_spec]:
                try:
                    # Generate individual model report
                    model_analysis = self.result_analyzer.analyze_model_intelligence(model_spec)
                    
                    # Save as JSON
                    model_file = self.output_dir / f"{evaluation_id}_{model_spec.replace(':', '_')}_analysis.json"
                    with open(model_file, 'w') as f:
                        json.dump(model_analysis, f, indent=2, default=str)
                    
                    # Save as Markdown if requested
                    if output_format == 'markdown':
                        markdown_report = self.result_analyzer.generate_report(model_spec, 'markdown')
                        md_file = self.output_dir / f"{evaluation_id}_{model_spec.replace(':', '_')}_report.md"
                        with open(md_file, 'w') as f:
                            f.write(markdown_report)
                        print(f"📄 Report saved to: {md_file}")
                
                except Exception as e:
                    print(f"⚠️ Error generating report for {model_spec}: {e}")
        
        # Save comparative analysis if available
        if results.get('comparative_analysis'):
            comp_file = self.output_dir / f"{evaluation_id}_comparative_analysis.json"
            with open(comp_file, 'w') as f:
                json.dump(results['comparative_analysis'], f, indent=2, default=str)
            print(f"📊 Comparative analysis saved to: {comp_file}")
    
    async def run_category_evaluation(
        self,
        category: IntelligenceCategory,
        models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run evaluation for a specific intelligence category."""
        return await self.run_intelligence_evaluation(
            models=models,
            categories=[category],
            save_results=True
        )
    
    async def run_quick_intelligence_test(
        self,
        model_spec: str,
        test_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run a quick intelligence test with specific tests."""
        print(f"🚀 Running quick intelligence test for {model_spec}")
        
        try:
            agent = await self._create_model_agent(model_spec)
            
            if test_names:
                # Run specific tests
                results = []
                for test_name in test_names:
                    if test_name in self.test_runner.get_available_tests():
                        result = await self.test_runner.run_test(test_name, agent, model_spec)
                        results.append(result)
                    else:
                        print(f"⚠️ Test '{test_name}' not found")
            else:
                # Run a sample from each category
                results = []
                for category in IntelligenceCategory:
                    category_tests = self.test_runner.get_tests_by_category(category)
                    if category_tests:
                        # Run first test from each category
                        test = category_tests[0]
                        result = await test.run_with_timing(agent, model_spec)
                        results.append(result)
            
            return {
                'model': model_spec,
                'test_count': len(results),
                'results': [r.to_dict() for r in results],
                'summary': {
                    'average_score': sum(r.score for r in results if r.score) / len([r for r in results if r.score]) if results else 0.0,
                    'pass_rate': sum(1 for r in results if r.status.value == 'passed') / len(results) if results else 0.0
                }
            }
        
        except Exception as e:
            return {'model': model_spec, 'error': str(e)}
    
    def get_available_tests(self) -> Dict[str, List[str]]:
        """Get available tests organized by category."""
        tests_by_category = {}
        
        for category in IntelligenceCategory:
            category_tests = self.test_runner.get_tests_by_category(category)
            tests_by_category[category.value] = [test.name for test in category_tests]
        
        return tests_by_category
    
    def get_test_info(self, test_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific test."""
        if test_name not in self.test_runner.test_registry:
            return None
        
        test = self.test_runner.test_registry[test_name]
        return {
            'name': test.name,
            'description': test.description,
            'category': test.intelligence_category.value,
            'complexity_level': test.complexity_level,
            'config': test.config
        }


# Convenience functions for common use cases
async def run_intelligence_evaluation(models: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convenience function to run intelligence evaluation."""
    evaluator = IntelligenceEvaluator()
    return await evaluator.run_intelligence_evaluation(models=models)


async def run_graphviz_evaluation(models: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convenience function to run GraphViz diagram tests."""
    evaluator = IntelligenceEvaluator()
    return await evaluator.run_category_evaluation(
        IntelligenceCategory.GRAPHICAL_REPRESENTATION, models
    )


async def run_creative_evaluation(models: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convenience function to run creative thinking tests."""
    evaluator = IntelligenceEvaluator()
    return await evaluator.run_category_evaluation(
        IntelligenceCategory.CREATIVE_THINKING, models
    )