"""
Intelligence test runner for executing and managing intelligence tests.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from .base_test import IntelligenceTestBase, IntelligenceTestResult, IntelligenceCategory
from .tests.graphviz_tests import GraphvizTests
from .tests.logic_tests import LogicTests
from .tests.pattern_tests import PatternTests
from .tests.creative_tests import CreativeTests


class IntelligenceTestRunner:
    """Runner for intelligence tests."""
    
    def __init__(self):
        self.test_registry = {}
        self.results = []
        self._register_all_tests()
    
    def _register_all_tests(self):
        """Register all available intelligence tests."""
        # GraphViz tests
        for test in GraphvizTests.get_all_tests():
            self.register_test(test)
        
        # Logic tests
        for test in LogicTests.get_all_tests():
            self.register_test(test)
        
        # Pattern tests
        for test in PatternTests.get_all_tests():
            self.register_test(test)
        
        # Creative tests
        for test in CreativeTests.get_all_tests():
            self.register_test(test)
    
    def register_test(self, test: IntelligenceTestBase):
        """Register a test."""
        self.test_registry[test.name] = test
    
    def get_available_tests(self) -> List[str]:
        """Get list of available test names."""
        return list(self.test_registry.keys())
    
    def get_tests_by_category(self, category: IntelligenceCategory) -> List[IntelligenceTestBase]:
        """Get tests by intelligence category."""
        return [test for test in self.test_registry.values() 
                if test.intelligence_category == category]
    
    def get_tests_by_complexity(self, complexity_level: int) -> List[IntelligenceTestBase]:
        """Get tests by complexity level."""
        return [test for test in self.test_registry.values() 
                if test.complexity_level == complexity_level]
    
    async def run_test(self, test_name: str, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run a single test."""
        if test_name not in self.test_registry:
            raise ValueError(f"Test '{test_name}' not found")
        
        test = self.test_registry[test_name]
        result = await test.run_with_timing(client, model, **kwargs)
        self.results.append(result)
        return result
    
    async def run_tests_by_category(self, category: IntelligenceCategory, client: Any, model: str, **kwargs) -> List[IntelligenceTestResult]:
        """Run all tests in a category."""
        tests = self.get_tests_by_category(category)
        results = []
        
        for test in tests:
            try:
                result = await test.run_with_timing(client, model, **kwargs)
                results.append(result)
                self.results.append(result)
            except Exception as e:
                print(f"Error running test {test.name}: {e}")
                # Continue with other tests
        
        return results
    
    async def run_all_tests(self, client: Any, model: str, max_concurrent: int = 3, **kwargs) -> List[IntelligenceTestResult]:
        """Run all available tests."""
        test_names = self.get_available_tests()
        
        # Run tests with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_single_test(test_name: str):
            async with semaphore:
                return await self.run_test(test_name, client, model, **kwargs)
        
        tasks = [run_single_test(name) for name in test_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and keep only successful results
        valid_results = [r for r in results if isinstance(r, IntelligenceTestResult)]
        return valid_results
    
    async def run_intelligence_battery(self, client: Any, model: str, **kwargs) -> Dict[str, Any]:
        """Run a comprehensive intelligence test battery."""
        start_time = time.time()
        
        battery_results = {
            'model': model,
            'start_time': start_time,
            'category_results': {},
            'overall_results': {},
            'detailed_results': []
        }
        
        # Run tests by category
        categories = [
            IntelligenceCategory.GRAPHICAL_REPRESENTATION,
            IntelligenceCategory.MATHEMATICAL_REASONING,
            IntelligenceCategory.LOGICAL_REASONING,
            IntelligenceCategory.PATTERN_RECOGNITION,
            IntelligenceCategory.ABSTRACT_REASONING,
            IntelligenceCategory.CREATIVE_THINKING,
            IntelligenceCategory.SPATIAL_REASONING
        ]
        
        for category in categories:
            print(f"Running {category.value} tests...")
            category_results = await self.run_tests_by_category(category, client, model, **kwargs)
            
            # Calculate category statistics
            if category_results:
                category_stats = self._calculate_category_stats(category_results)
                battery_results['category_results'][category.value] = category_stats
                battery_results['detailed_results'].extend([r.to_dict() for r in category_results])
        
        # Calculate overall statistics
        all_results = [r for category_results in battery_results['category_results'].values() 
                      for r in category_results.get('results', [])]
        
        if all_results:
            battery_results['overall_results'] = self._calculate_overall_stats(battery_results['category_results'])
        
        battery_results['execution_time'] = time.time() - start_time
        battery_results['end_time'] = time.time()
        
        return battery_results
    
    def _calculate_category_stats(self, results: List[IntelligenceTestResult]) -> Dict[str, Any]:
        """Calculate statistics for a category of tests."""
        if not results:
            return {
                'test_count': 0,
                'average_score': 0.0,
                'pass_rate': 0.0,
                'average_creativity': 0.0,
                'average_coherence': 0.0,
                'average_complexity': 0.0,
                'results': []
            }
        
        scores = [r.score for r in results if r.score is not None]
        creativity_scores = [r.creativity_score for r in results if r.creativity_score is not None]
        coherence_scores = [r.logical_coherence for r in results if r.logical_coherence is not None]
        complexity_levels = [r.complexity_level for r in results if r.complexity_level is not None]
        
        passed_tests = sum(1 for r in results if r.status.value == 'passed')
        
        return {
            'test_count': len(results),
            'average_score': sum(scores) / len(scores) if scores else 0.0,
            'pass_rate': passed_tests / len(results) if results else 0.0,
            'average_creativity': sum(creativity_scores) / len(creativity_scores) if creativity_scores else 0.0,
            'average_coherence': sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0,
            'average_complexity': sum(complexity_levels) / len(complexity_levels) if complexity_levels else 0.0,
            'score_distribution': self._calculate_score_distribution(scores),
            'results': [r.to_dict() for r in results]
        }
    
    def _calculate_overall_stats(self, category_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall intelligence statistics."""
        total_tests = 0
        total_score = 0.0
        total_passed = 0
        total_creativity = 0.0
        total_coherence = 0.0
        
        creativity_count = 0
        coherence_count = 0
        
        category_scores = {}
        
        for category, stats in category_results.items():
            total_tests += stats['test_count']
            total_score += stats['average_score'] * stats['test_count']
            total_passed += stats['pass_rate'] * stats['test_count']
            
            if stats['average_creativity'] > 0:
                total_creativity += stats['average_creativity'] * stats['test_count']
                creativity_count += stats['test_count']
            
            if stats['average_coherence'] > 0:
                total_coherence += stats['average_coherence'] * stats['test_count']
                coherence_count += stats['test_count']
            
            category_scores[category] = stats['average_score']
        
        return {
            'total_tests': total_tests,
            'overall_score': total_score / total_tests if total_tests > 0 else 0.0,
            'overall_pass_rate': total_passed / total_tests if total_tests > 0 else 0.0,
            'overall_creativity': total_creativity / creativity_count if creativity_count > 0 else 0.0,
            'overall_coherence': total_coherence / coherence_count if coherence_count > 0 else 0.0,
            'category_scores': category_scores,
            'intelligence_quotient': self._calculate_intelligence_quotient(category_scores)
        }
    
    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate score distribution."""
        if not scores:
            return {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        
        distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        
        for score in scores:
            if score >= 0.9:
                distribution['excellent'] += 1
            elif score >= 0.7:
                distribution['good'] += 1
            elif score >= 0.5:
                distribution['fair'] += 1
            else:
                distribution['poor'] += 1
        
        return distribution
    
    def _calculate_intelligence_quotient(self, category_scores: Dict[str, float]) -> float:
        """Calculate a simple intelligence quotient based on category performance."""
        if not category_scores:
            return 0.0
        
        # Weight different categories
        weights = {
            'logical_reasoning': 0.2,
            'mathematical_reasoning': 0.2,
            'pattern_recognition': 0.15,
            'abstract_reasoning': 0.15,
            'creative_thinking': 0.1,
            'spatial_reasoning': 0.1,
            'graphical_representation': 0.1
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for category, score in category_scores.items():
            weight = weights.get(category, 0.1)
            weighted_score += score * weight
            total_weight += weight
        
        # Normalize to 0-100 scale (like traditional IQ)
        iq_score = (weighted_score / total_weight) * 100 if total_weight > 0 else 0.0
        return iq_score
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all test results."""
        if not self.results:
            return {'total_tests': 0, 'summary': 'No tests run'}
        
        passed = sum(1 for r in self.results if r.status.value == 'passed')
        failed = sum(1 for r in self.results if r.status.value == 'failed')
        errors = sum(1 for r in self.results if r.status.value == 'error')
        
        scores = [r.score for r in self.results if r.score is not None]
        
        return {
            'total_tests': len(self.results),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': passed / len(self.results) if self.results else 0.0,
            'average_score': sum(scores) / len(scores) if scores else 0.0,
            'score_range': [min(scores), max(scores)] if scores else [0.0, 0.0]
        }
    
    def clear_results(self):
        """Clear all stored results."""
        self.results.clear()
        for test in self.test_registry.values():
            test.results.clear()