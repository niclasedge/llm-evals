#!/usr/bin/env python3
"""
Model Comparison Example

This script demonstrates how to compare multiple models across different
evaluation types and generate comparison reports.

Usage:
    python examples/python/model_comparison.py
    python examples/python/model_comparison.py --models llama3,phi4,gemma3
    python examples/python/model_comparison.py --free-only --output comparison_report.md
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import csv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.features.unified_evaluation.service import EvaluationService
from src.features.unified_evaluation.models import (
    EvaluationType,
    OutputFormat,
    ModelSelection,
    OutputConfig,
    EvaluationRequest
)
from src.core.llm_unified_config import get_unified_config


class ModelComparison:
    """Class for comparing multiple models across evaluation types"""
    
    def __init__(self):
        self.service = EvaluationService()
        self.config = get_unified_config()
        self.results = {}
    
    async def compare_models_coding(
        self,
        models: List[str],
        problems: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        free_only: bool = False
    ) -> Dict[str, Any]:
        """Compare models on coding tasks"""
        
        print("🔄 Running coding comparison...")
        
        # Run evaluation for all models
        model_selection = ModelSelection(
            models=models,
            providers=[],
            capabilities=[],
            free_only=free_only
        )
        
        output_config = OutputConfig(
            format=OutputFormat.JSON,
            file_path=None,
            verbose=False,
            progress=True
        )
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=model_selection,
            output_config=output_config,
            problems=problems,
            languages=languages,
            timeout=300,
            parallel=True
        )
        
        result = await self.service.run_evaluation(request)
        
        # Process results for comparison
        comparison_data = {
            'evaluation_type': 'coding',
            'models': {},
            'problems': problems or [],
            'languages': languages or [],
            'timestamp': datetime.now().isoformat()
        }
        
        for model_result in result.model_results:
            model_name = model_result.model_name
            metrics = model_result.metrics
            
            comparison_data['models'][model_name] = {
                'provider': model_result.provider,
                'average_score': metrics.get('average_score', 0),
                'success_rate': metrics.get('success_rate', 0),
                'total_problems': metrics.get('total_problems', 0),
                'total_tests': metrics.get('total_tests', 0),
                'passed_tests': metrics.get('passed_tests', 0),
                'errors': len(model_result.errors)
            }
        
        self.results['coding'] = comparison_data
        return comparison_data
    
    async def compare_models_vision(
        self,
        models: List[str],
        categories: Optional[List[str]] = None,
        free_only: bool = False
    ) -> Dict[str, Any]:
        """Compare models on vision tasks"""
        
        print("🔄 Running vision comparison...")
        
        # Filter to vision-capable models
        vision_models = []
        for model_name in models:
            model = self.config.resolve_model_name(model_name)
            if model and 'vision' in model.capabilities:
                vision_models.append(model_name)
        
        if not vision_models:
            print("⚠️  No vision-capable models found")
            return {'evaluation_type': 'vision', 'models': {}, 'error': 'No vision models'}
        
        print(f"   Vision models: {vision_models}")
        
        # Run evaluation
        model_selection = ModelSelection(
            models=vision_models,
            providers=[],
            capabilities=['vision'],
            free_only=free_only
        )
        
        output_config = OutputConfig(
            format=OutputFormat.JSON,
            file_path=None,
            verbose=False,
            progress=True
        )
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.VISION,
            model_selection=model_selection,
            output_config=output_config,
            categories=categories,
            timeout=300,
            parallel=True
        )
        
        result = await self.service.run_evaluation(request)
        
        # Process results
        comparison_data = {
            'evaluation_type': 'vision',
            'models': {},
            'categories': categories or [],
            'timestamp': datetime.now().isoformat()
        }
        
        for model_result in result.model_results:
            model_name = model_result.model_name
            metrics = model_result.metrics
            
            comparison_data['models'][model_name] = {
                'provider': model_result.provider,
                'average_score': metrics.get('average_score', 0),
                'success_rate': metrics.get('success_rate', 0),
                'total_images': metrics.get('total_images', 0),
                'categories_tested': metrics.get('categories_tested', 0),
                'errors': len(model_result.errors)
            }
        
        self.results['vision'] = comparison_data
        return comparison_data
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate overall comparison summary"""
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'evaluation_types': list(self.results.keys()),
            'model_rankings': {},
            'best_models': {},
            'overall_statistics': {}
        }
        
        # Calculate rankings for each evaluation type
        for eval_type, data in self.results.items():
            if 'models' not in data or not data['models']:
                continue
                
            # Sort models by average score
            model_scores = [
                (model, metrics.get('average_score', 0))
                for model, metrics in data['models'].items()
            ]
            model_scores.sort(key=lambda x: x[1], reverse=True)
            
            summary['model_rankings'][eval_type] = model_scores
            summary['best_models'][eval_type] = model_scores[0][0] if model_scores else None
            
            # Calculate statistics
            scores = [score for _, score in model_scores]
            if scores:
                summary['overall_statistics'][eval_type] = {
                    'models_tested': len(scores),
                    'average_score': sum(scores) / len(scores),
                    'best_score': max(scores),
                    'worst_score': min(scores),
                    'score_range': max(scores) - min(scores)
                }
        
        return summary
    
    def export_to_csv(self, output_file: str):
        """Export comparison results to CSV"""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Evaluation Type', 'Model', 'Provider', 'Average Score', 
                           'Success Rate', 'Errors', 'Additional Metrics'])
            
            # Write data for each evaluation type
            for eval_type, data in self.results.items():
                if 'models' not in data:
                    continue
                    
                for model_name, metrics in data['models'].items():
                    additional_metrics = []
                    
                    # Add type-specific metrics
                    if eval_type == 'coding':
                        additional_metrics.append(f"Problems: {metrics.get('total_problems', 0)}")
                        additional_metrics.append(f"Tests: {metrics.get('passed_tests', 0)}/{metrics.get('total_tests', 0)}")
                    elif eval_type == 'vision':
                        additional_metrics.append(f"Images: {metrics.get('total_images', 0)}")
                        additional_metrics.append(f"Categories: {metrics.get('categories_tested', 0)}")
                    
                    writer.writerow([
                        eval_type,
                        model_name,
                        metrics.get('provider', 'unknown'),
                        f"{metrics.get('average_score', 0):.1f}",
                        f"{metrics.get('success_rate', 0):.1%}",
                        metrics.get('errors', 0),
                        '; '.join(additional_metrics)
                    ])
        
        print(f"📊 CSV report exported to: {output_file}")
    
    def export_to_markdown(self, output_file: str):
        """Export comparison results to Markdown"""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write("# Model Comparison Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Overall summary
            summary = self.generate_summary_report()
            f.write("## Summary\n\n")
            
            if summary['best_models']:
                f.write("### Best Models by Category\n\n")
                for eval_type, best_model in summary['best_models'].items():
                    f.write(f"- **{eval_type.title()}**: {best_model}\n")
                f.write("\n")
            
            # Detailed results for each evaluation type
            for eval_type, data in self.results.items():
                f.write(f"## {eval_type.title()} Evaluation\n\n")
                
                if 'models' not in data or not data['models']:
                    f.write("No results available.\n\n")
                    continue
                
                # Create table
                f.write("| Model | Provider | Average Score | Success Rate | Additional Info |\n")
                f.write("|-------|----------|---------------|--------------|----------------|\n")
                
                # Sort models by score
                sorted_models = sorted(
                    data['models'].items(),
                    key=lambda x: x[1].get('average_score', 0),
                    reverse=True
                )
                
                for model_name, metrics in sorted_models:
                    additional_info = []
                    
                    if eval_type == 'coding':
                        additional_info.append(f"Problems: {metrics.get('total_problems', 0)}")
                        additional_info.append(f"Tests: {metrics.get('passed_tests', 0)}/{metrics.get('total_tests', 0)}")
                    elif eval_type == 'vision':
                        additional_info.append(f"Images: {metrics.get('total_images', 0)}")
                        additional_info.append(f"Categories: {metrics.get('categories_tested', 0)}")
                    
                    if metrics.get('errors', 0) > 0:
                        additional_info.append(f"⚠️ {metrics['errors']} errors")
                    
                    f.write(f"| {model_name} | {metrics.get('provider', 'unknown')} | "
                           f"{metrics.get('average_score', 0):.1f} | "
                           f"{metrics.get('success_rate', 0):.1%} | "
                           f"{'; '.join(additional_info)} |\n")
                
                f.write("\n")
                
                # Add statistics if available
                if eval_type in summary['overall_statistics']:
                    stats = summary['overall_statistics'][eval_type]
                    f.write("### Statistics\n\n")
                    f.write(f"- Models tested: {stats['models_tested']}\n")
                    f.write(f"- Average score: {stats['average_score']:.1f}\n")
                    f.write(f"- Best score: {stats['best_score']:.1f}\n")
                    f.write(f"- Worst score: {stats['worst_score']:.1f}\n")
                    f.write(f"- Score range: {stats['score_range']:.1f}\n\n")
        
        print(f"📝 Markdown report exported to: {output_file}")
    
    def print_console_summary(self):
        """Print a summary to console"""
        
        summary = self.generate_summary_report()
        
        print("\n📊 Model Comparison Summary")
        print("=" * 50)
        
        # Best models
        if summary['best_models']:
            print("\n🏆 Best Models by Category:")
            for eval_type, best_model in summary['best_models'].items():
                print(f"   • {eval_type.title()}: {best_model}")
        
        # Detailed rankings
        for eval_type, rankings in summary['model_rankings'].items():
            print(f"\n📈 {eval_type.title()} Rankings:")
            for i, (model, score) in enumerate(rankings, 1):
                print(f"   {i}. {model}: {score:.1f}")
        
        # Overall statistics
        if summary['overall_statistics']:
            print(f"\n📊 Statistics:")
            for eval_type, stats in summary['overall_statistics'].items():
                print(f"   {eval_type.title()}:")
                print(f"      Models tested: {stats['models_tested']}")
                print(f"      Average score: {stats['average_score']:.1f}")
                print(f"      Score range: {stats['worst_score']:.1f} - {stats['best_score']:.1f}")


async def main():
    """Main function for model comparison"""
    
    parser = argparse.ArgumentParser(description="Model Comparison Example")
    parser.add_argument('--models', nargs='+', 
                       default=['llama3', 'phi4'], 
                       help='Models to compare')
    parser.add_argument('--types', nargs='+',
                       choices=['coding', 'vision', 'tools', 'intelligence'],
                       default=['coding'],
                       help='Evaluation types to compare')
    parser.add_argument('--free-only', action='store_true',
                       help='Use only free models')
    parser.add_argument('--output', help='Output file (format determined by extension)')
    parser.add_argument('--format', choices=['json', 'csv', 'markdown', 'console'],
                       default='console', help='Output format')
    parser.add_argument('--problems', nargs='+',
                       help='Specific coding problems to test')
    parser.add_argument('--languages', nargs='+',
                       help='Programming languages for coding evaluation')
    parser.add_argument('--categories', nargs='+',
                       help='Vision categories to test')
    
    args = parser.parse_args()
    
    print("🔍 Model Comparison Tool")
    print("=" * 40)
    
    # Initialize comparison
    comparison = ModelComparison()
    
    # Validate models
    print(f"\nValidating models: {args.models}")
    validation_results = {}
    for model_name in args.models:
        try:
            model = comparison.config.resolve_model_name(model_name)
            validation_results[model_name] = model is not None
        except Exception:
            validation_results[model_name] = False
    
    for model, is_valid in validation_results.items():
        status = "✅" if is_valid else "❌"
        print(f"  {status} {model}")
    
    # Filter to valid models
    valid_models = [m for m, valid in validation_results.items() if valid]
    if not valid_models:
        print("❌ No valid models found")
        return
    
    print(f"\nRunning comparison for: {valid_models}")
    print(f"Evaluation types: {args.types}")
    
    # Run comparisons
    try:
        for eval_type in args.types:
            if eval_type == 'coding':
                await comparison.compare_models_coding(
                    models=valid_models,
                    problems=args.problems,
                    languages=args.languages,
                    free_only=args.free_only
                )
            elif eval_type == 'vision':
                await comparison.compare_models_vision(
                    models=valid_models,
                    categories=args.categories,
                    free_only=args.free_only
                )
            else:
                print(f"⚠️  Evaluation type '{eval_type}' not implemented in this example")
        
        # Output results
        if args.output:
            # Determine format from file extension if not specified
            output_format = args.format
            if output_format == 'console' and args.output:
                ext = Path(args.output).suffix.lower()
                if ext == '.json':
                    output_format = 'json'
                elif ext == '.csv':
                    output_format = 'csv'
                elif ext in ['.md', '.markdown']:
                    output_format = 'markdown'
            
            # Export in specified format
            if output_format == 'json':
                with open(args.output, 'w') as f:
                    json.dump(comparison.results, f, indent=2)
                print(f"📄 JSON results saved to: {args.output}")
            elif output_format == 'csv':
                comparison.export_to_csv(args.output)
            elif output_format == 'markdown':
                comparison.export_to_markdown(args.output)
        
        # Always show console summary
        comparison.print_console_summary()
        
    except Exception as e:
        print(f"❌ Comparison failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())