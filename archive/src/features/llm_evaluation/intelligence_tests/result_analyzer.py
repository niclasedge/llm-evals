"""
Intelligence test result analyzer for processing and reporting test outcomes.
"""

import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_test import IntelligenceTestResult, IntelligenceCategory


class IntelligenceResultAnalyzer:
    """Analyzer for intelligence test results."""
    
    def __init__(self):
        self.results = []
        self.analysis_cache = {}
    
    def add_results(self, results: List[IntelligenceTestResult]):
        """Add results to analyzer."""
        self.results.extend(results)
        self.analysis_cache.clear()  # Clear cache when new results added
    
    def analyze_model_intelligence(self, model_name: str) -> Dict[str, Any]:
        """Analyze intelligence profile for a specific model."""
        model_results = [r for r in self.results if r.details.get('model') == model_name]
        
        if not model_results:
            return {'error': f'No results found for model {model_name}'}
        
        analysis = {
            'model': model_name,
            'analysis_timestamp': datetime.now().isoformat(),
            'overall_performance': self._analyze_overall_performance(model_results),
            'category_analysis': self._analyze_by_category(model_results),
            'strength_weaknesses': self._identify_strengths_weaknesses(model_results),
            'complexity_analysis': self._analyze_complexity_performance(model_results),
            'creativity_analysis': self._analyze_creativity_performance(model_results),
            'recommendations': self._generate_recommendations(model_results)
        }
        
        return analysis
    
    def compare_models(self, model_names: List[str]) -> Dict[str, Any]:
        """Compare intelligence performance across multiple models."""
        comparison = {
            'comparison_timestamp': datetime.now().isoformat(),
            'models': model_names,
            'model_analyses': {},
            'comparative_analysis': {},
            'rankings': {}
        }
        
        # Get individual model analyses
        for model in model_names:
            comparison['model_analyses'][model] = self.analyze_model_intelligence(model)
        
        # Comparative analysis
        comparison['comparative_analysis'] = self._perform_comparative_analysis(model_names)
        comparison['rankings'] = self._rank_models(model_names)
        
        return comparison
    
    def _analyze_overall_performance(self, results: List[IntelligenceTestResult]) -> Dict[str, Any]:
        """Analyze overall performance metrics."""
        if not results:
            return {}
        
        scores = [r.score for r in results if r.score is not None]
        execution_times = [r.execution_time for r in results if r.execution_time is not None]
        
        passed_tests = sum(1 for r in results if r.status.value == 'passed')
        failed_tests = sum(1 for r in results if r.status.value == 'failed')
        error_tests = sum(1 for r in results if r.status.value == 'error')
        
        return {
            'total_tests': len(results),
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'error_tests': error_tests,
            'pass_rate': passed_tests / len(results) if results else 0.0,
            'average_score': sum(scores) / len(scores) if scores else 0.0,
            'score_std_dev': self._calculate_std_dev(scores),
            'score_range': [min(scores), max(scores)] if scores else [0.0, 0.0],
            'average_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0.0,
            'performance_grade': self._calculate_performance_grade(scores)
        }
    
    def _analyze_by_category(self, results: List[IntelligenceTestResult]) -> Dict[str, Any]:
        """Analyze performance by intelligence category."""
        category_analysis = {}
        
        # Group by category
        category_groups = {}
        for result in results:
            if result.intelligence_category:
                category = result.intelligence_category.value
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(result)
        
        # Analyze each category
        for category, category_results in category_groups.items():
            scores = [r.score for r in category_results if r.score is not None]
            creativity_scores = [r.creativity_score for r in category_results if r.creativity_score is not None]
            coherence_scores = [r.logical_coherence for r in category_results if r.logical_coherence is not None]
            
            passed = sum(1 for r in category_results if r.status.value == 'passed')
            
            category_analysis[category] = {
                'test_count': len(category_results),
                'pass_rate': passed / len(category_results) if category_results else 0.0,
                'average_score': sum(scores) / len(scores) if scores else 0.0,
                'score_range': [min(scores), max(scores)] if scores else [0.0, 0.0],
                'average_creativity': sum(creativity_scores) / len(creativity_scores) if creativity_scores else None,
                'average_coherence': sum(coherence_scores) / len(coherence_scores) if coherence_scores else None,
                'performance_level': self._categorize_performance_level(sum(scores) / len(scores) if scores else 0.0)
            }
        
        return category_analysis
    
    def _identify_strengths_weaknesses(self, results: List[IntelligenceTestResult]) -> Dict[str, Any]:
        """Identify model strengths and weaknesses."""
        category_analysis = self._analyze_by_category(results)
        
        if not category_analysis:
            return {'strengths': [], 'weaknesses': [], 'balanced_areas': []}
        
        # Sort categories by performance
        sorted_categories = sorted(category_analysis.items(), 
                                 key=lambda x: x[1]['average_score'], reverse=True)
        
        total_categories = len(sorted_categories)
        top_third = total_categories // 3
        bottom_third = total_categories // 3
        
        strengths = [cat for cat, data in sorted_categories[:top_third] 
                    if data['average_score'] > 0.7]
        weaknesses = [cat for cat, data in sorted_categories[-bottom_third:] 
                     if data['average_score'] < 0.5]
        balanced_areas = [cat for cat, data in sorted_categories[top_third:-bottom_third]
                         if 0.5 <= data['average_score'] <= 0.7]
        
        return {
            'strengths': strengths,
            'weaknesses': weaknesses,
            'balanced_areas': balanced_areas,
            'strongest_category': sorted_categories[0][0] if sorted_categories else None,
            'weakest_category': sorted_categories[-1][0] if sorted_categories else None
        }
    
    def _analyze_complexity_performance(self, results: List[IntelligenceTestResult]) -> Dict[str, Any]:
        """Analyze performance across different complexity levels."""
        complexity_groups = {}
        
        for result in results:
            if result.complexity_level is not None:
                level = result.complexity_level
                if level not in complexity_groups:
                    complexity_groups[level] = []
                complexity_groups[level].append(result)
        
        complexity_analysis = {}
        for level, level_results in complexity_groups.items():
            scores = [r.score for r in level_results if r.score is not None]
            passed = sum(1 for r in level_results if r.status.value == 'passed')
            
            complexity_analysis[f'level_{level}'] = {
                'test_count': len(level_results),
                'pass_rate': passed / len(level_results) if level_results else 0.0,
                'average_score': sum(scores) / len(scores) if scores else 0.0,
                'performance_trend': self._analyze_complexity_trend(complexity_groups)
            }
        
        return complexity_analysis
    
    def _analyze_creativity_performance(self, results: List[IntelligenceTestResult]) -> Dict[str, Any]:
        """Analyze creativity-specific performance."""
        creative_results = [r for r in results if r.creativity_score is not None]
        
        if not creative_results:
            return {'message': 'No creativity scores available'}
        
        creativity_scores = [r.creativity_score for r in creative_results]
        overall_scores = [r.score for r in creative_results if r.score is not None]
        
        return {
            'creativity_test_count': len(creative_results),
            'average_creativity_score': sum(creativity_scores) / len(creativity_scores),
            'creativity_score_range': [min(creativity_scores), max(creativity_scores)],
            'creativity_vs_overall_correlation': self._calculate_correlation(creativity_scores, overall_scores),
            'creativity_level': self._categorize_creativity_level(sum(creativity_scores) / len(creativity_scores))
        }
    
    def _generate_recommendations(self, results: List[IntelligenceTestResult]) -> List[str]:
        """Generate recommendations based on performance analysis."""
        recommendations = []
        
        strengths_weaknesses = self._identify_strengths_weaknesses(results)
        overall_performance = self._analyze_overall_performance(results)
        
        # Overall performance recommendations
        if overall_performance.get('pass_rate', 0) < 0.6:
            recommendations.append("Consider improving fundamental reasoning capabilities across all domains.")
        
        if overall_performance.get('average_score', 0) < 0.5:
            recommendations.append("Focus on enhancing basic problem-solving and analytical thinking skills.")
        
        # Category-specific recommendations
        weaknesses = strengths_weaknesses.get('weaknesses', [])
        for weakness in weaknesses:
            if 'mathematical' in weakness:
                recommendations.append("Improve mathematical reasoning and calculation accuracy.")
            elif 'creative' in weakness:
                recommendations.append("Enhance creative thinking and divergent problem-solving approaches.")
            elif 'spatial' in weakness:
                recommendations.append("Develop spatial reasoning and visualization capabilities.")
            elif 'logical' in weakness:
                recommendations.append("Strengthen logical reasoning and deductive thinking skills.")
            elif 'pattern' in weakness:
                recommendations.append("Focus on pattern recognition and sequence analysis abilities.")
        
        # Creativity recommendations
        creativity_analysis = self._analyze_creativity_performance(results)
        if creativity_analysis.get('average_creativity_score', 0) < 0.5:
            recommendations.append("Develop more creative and innovative thinking approaches.")
        
        # Complexity recommendations
        complexity_analysis = self._analyze_complexity_performance(results)
        if any(data.get('pass_rate', 0) < 0.4 for data in complexity_analysis.values()):
            recommendations.append("Practice with more challenging and complex problem-solving scenarios.")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _perform_comparative_analysis(self, model_names: List[str]) -> Dict[str, Any]:
        """Perform comparative analysis across models."""
        model_data = {}
        
        for model in model_names:
            model_results = [r for r in self.results if r.details.get('model') == model]
            if model_results:
                scores = [r.score for r in model_results if r.score is not None]
                model_data[model] = {
                    'average_score': sum(scores) / len(scores) if scores else 0.0,
                    'test_count': len(model_results),
                    'pass_rate': sum(1 for r in model_results if r.status.value == 'passed') / len(model_results)
                }
        
        if len(model_data) < 2:
            return {'message': 'Need at least 2 models for comparison'}
        
        # Find best and worst performing models
        best_model = max(model_data.items(), key=lambda x: x[1]['average_score'])
        worst_model = min(model_data.items(), key=lambda x: x[1]['average_score'])
        
        return {
            'model_scores': {model: data['average_score'] for model, data in model_data.items()},
            'model_pass_rates': {model: data['pass_rate'] for model, data in model_data.items()},
            'best_performer': {'model': best_model[0], 'score': best_model[1]['average_score']},
            'worst_performer': {'model': worst_model[0], 'score': worst_model[1]['average_score']},
            'performance_gap': best_model[1]['average_score'] - worst_model[1]['average_score']
        }
    
    def _rank_models(self, model_names: List[str]) -> Dict[str, Any]:
        """Rank models by different criteria."""
        model_data = {}
        
        for model in model_names:
            model_results = [r for r in self.results if r.details.get('model') == model]
            if model_results:
                analysis = self.analyze_model_intelligence(model)
                model_data[model] = analysis
        
        # Rank by overall score
        overall_ranking = sorted(model_data.items(), 
                               key=lambda x: x[1].get('overall_performance', {}).get('average_score', 0), 
                               reverse=True)
        
        # Rank by creativity
        creativity_ranking = sorted(model_data.items(),
                                  key=lambda x: x[1].get('creativity_analysis', {}).get('average_creativity_score', 0),
                                  reverse=True)
        
        return {
            'overall_ranking': [model for model, _ in overall_ranking],
            'creativity_ranking': [model for model, _ in creativity_ranking],
            'detailed_rankings': {
                'overall': [(model, data.get('overall_performance', {}).get('average_score', 0)) 
                           for model, data in overall_ranking],
                'creativity': [(model, data.get('creativity_analysis', {}).get('average_creativity_score', 0))
                              for model, data in creativity_ranking]
            }
        }
    
    def _calculate_std_dev(self, scores: List[float]) -> float:
        """Calculate standard deviation of scores."""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        return variance ** 0.5
    
    def _calculate_performance_grade(self, scores: List[float]) -> str:
        """Calculate performance grade based on scores."""
        if not scores:
            return 'N/A'
        
        average = sum(scores) / len(scores)
        
        if average >= 0.9:
            return 'A'
        elif average >= 0.8:
            return 'B'
        elif average >= 0.7:
            return 'C'
        elif average >= 0.6:
            return 'D'
        else:
            return 'F'
    
    def _categorize_performance_level(self, score: float) -> str:
        """Categorize performance level."""
        if score >= 0.9:
            return 'Excellent'
        elif score >= 0.7:
            return 'Good'
        elif score >= 0.5:
            return 'Fair'
        else:
            return 'Poor'
    
    def _categorize_creativity_level(self, score: float) -> str:
        """Categorize creativity level."""
        if score >= 0.8:
            return 'Highly Creative'
        elif score >= 0.6:
            return 'Creative'
        elif score >= 0.4:
            return 'Moderately Creative'
        else:
            return 'Limited Creativity'
    
    def _analyze_complexity_trend(self, complexity_groups: Dict[int, List]) -> str:
        """Analyze performance trend across complexity levels."""
        if len(complexity_groups) < 2:
            return 'Insufficient data'
        
        levels = sorted(complexity_groups.keys())
        scores = []
        
        for level in levels:
            level_scores = [r.score for r in complexity_groups[level] if r.score is not None]
            if level_scores:
                scores.append(sum(level_scores) / len(level_scores))
        
        if len(scores) < 2:
            return 'Insufficient data'
        
        # Simple trend analysis
        if scores[-1] > scores[0]:
            return 'Improving with complexity'
        elif scores[-1] < scores[0]:
            return 'Declining with complexity'
        else:
            return 'Consistent across complexity'
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate correlation coefficient between two lists."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(xi ** 2 for xi in x)
        sum_y2 = sum(yi ** 2 for yi in y)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def generate_report(self, model_name: str, output_format: str = 'dict') -> Any:
        """Generate comprehensive intelligence report."""
        analysis = self.analyze_model_intelligence(model_name)
        
        if output_format == 'json':
            return json.dumps(analysis, indent=2)
        elif output_format == 'markdown':
            return self._generate_markdown_report(analysis)
        else:
            return analysis
    
    def _generate_markdown_report(self, analysis: Dict[str, Any]) -> str:
        """Generate markdown report."""
        model = analysis.get('model', 'Unknown')
        overall = analysis.get('overall_performance', {})
        
        report = f"""# Intelligence Analysis Report: {model}
        
## Overall Performance
- **Total Tests**: {overall.get('total_tests', 0)}
- **Pass Rate**: {overall.get('pass_rate', 0):.2%}
- **Average Score**: {overall.get('average_score', 0):.3f}
- **Performance Grade**: {overall.get('performance_grade', 'N/A')}

## Category Analysis
"""
        
        category_analysis = analysis.get('category_analysis', {})
        for category, data in category_analysis.items():
            report += f"""
### {category.replace('_', ' ').title()}
- **Tests**: {data.get('test_count', 0)}
- **Pass Rate**: {data.get('pass_rate', 0):.2%}
- **Average Score**: {data.get('average_score', 0):.3f}
- **Performance Level**: {data.get('performance_level', 'N/A')}
"""
        
        strengths_weaknesses = analysis.get('strength_weaknesses', {})
        report += f"""
## Strengths and Weaknesses
- **Strengths**: {', '.join(strengths_weaknesses.get('strengths', ['None identified']))}
- **Weaknesses**: {', '.join(strengths_weaknesses.get('weaknesses', ['None identified']))}

## Recommendations
"""
        
        recommendations = analysis.get('recommendations', [])
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
        
        return report