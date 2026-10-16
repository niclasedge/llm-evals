#!/usr/bin/env python3
"""
Unified Evaluation API Example

This script demonstrates how to use the unified evaluation system programmatically
via Python API calls. It shows how to run different types of evaluations and 
handle results.

Usage:
    python examples/python/unified_evaluation_api.py
    python examples/python/unified_evaluation_api.py --model llama3 --type coding
    python examples/python/unified_evaluation_api.py --free-only --output results.json
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

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


class UnifiedEvaluationExample:
    """Example class for running unified evaluations via Python API"""
    
    def __init__(self):
        self.service = EvaluationService()
        self.config = get_unified_config()
    
    async def run_coding_evaluation(
        self,
        models: List[str],
        problems: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        free_only: bool = False,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Run coding evaluation with specified parameters"""
        
        print(f"🔄 Starting coding evaluation...")
        print(f"   Models: {models}")
        print(f"   Problems: {problems or 'All available'}")
        print(f"   Languages: {languages or 'All supported'}")
        
        # Build model selection
        model_selection = ModelSelection(
            models=models,
            providers=[],
            capabilities=[],
            free_only=free_only
        )
        
        # Build output config
        output_config = OutputConfig(
            format=OutputFormat.JSON,
            file_path=None,
            verbose=verbose,
            progress=True
        )
        
        # Build evaluation request
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=model_selection,
            output_config=output_config,
            problems=problems,
            languages=languages,
            timeout=300,
            parallel=True
        )
        
        # Run evaluation
        result = await self.service.run_evaluation(request)
        
        print(f"✅ Coding evaluation completed")
        return result.model_dump()
    
    async def run_vision_evaluation(
        self,
        models: List[str],
        categories: Optional[List[str]] = None,
        images: Optional[List[str]] = None,
        free_only: bool = False,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Run vision evaluation with specified parameters"""
        
        print(f"🔄 Starting vision evaluation...")
        print(f"   Models: {models}")
        print(f"   Categories: {categories or 'All available'}")
        print(f"   Images: {images or 'Test image collection'}")
        
        # Build model selection with vision capability
        model_selection = ModelSelection(
            models=models,
            providers=[],
            capabilities=['vision'],
            free_only=free_only
        )
        
        # Build output config
        output_config = OutputConfig(
            format=OutputFormat.JSON,
            file_path=None,
            verbose=verbose,
            progress=True
        )
        
        # Build evaluation request
        request = EvaluationRequest(
            evaluation_type=EvaluationType.VISION,
            model_selection=model_selection,
            output_config=output_config,
            categories=categories,
            images=images,
            timeout=300,
            parallel=True
        )
        
        # Run evaluation
        result = await self.service.run_evaluation(request)
        
        print(f"✅ Vision evaluation completed")
        return result.model_dump()
    
    async def run_comprehensive_evaluation(
        self,
        models: List[str],
        free_only: bool = False,
        timeout: int = 600,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Run comprehensive evaluation across all types"""
        
        print(f"🔄 Starting comprehensive evaluation...")
        print(f"   Models: {models}")
        print(f"   Free only: {free_only}")
        print(f"   Timeout: {timeout}s")
        
        # Build model selection
        model_selection = ModelSelection(
            models=models,
            providers=[],
            capabilities=[],
            free_only=free_only
        )
        
        # Build output config
        output_config = OutputConfig(
            format=OutputFormat.JSON,
            file_path=None,
            verbose=verbose,
            progress=True
        )
        
        # Build evaluation request
        request = EvaluationRequest(
            evaluation_type=EvaluationType.ALL,
            model_selection=model_selection,
            output_config=output_config,
            timeout=timeout,
            parallel=True
        )
        
        # Run evaluation
        result = await self.service.run_evaluation(request)
        
        print(f"✅ Comprehensive evaluation completed")
        return result.model_dump()
    
    def list_available_models(
        self,
        provider: Optional[str] = None,
        capability: Optional[str] = None,
        free_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List available models with filtering"""
        
        models = self.config.list_models(
            provider=provider,
            capability=capability,
            free_only=free_only,
            enabled_only=True
        )
        
        return [
            {
                'name': m.name,
                'provider': m.provider,
                'model_id': m.model_id,
                'capabilities': m.capabilities,
                'free': m.free,
                'enabled': m.enabled
            }
            for m in models
        ]
    
    def validate_models(self, model_names: List[str]) -> Dict[str, bool]:
        """Validate that model names are available"""
        
        results = {}
        for model_name in model_names:
            try:
                model = self.config.resolve_model_name(model_name)
                results[model_name] = model is not None
            except Exception:
                results[model_name] = False
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save results to file with timestamp"""
        
        # Add timestamp to results
        results['timestamp'] = datetime.now().isoformat()
        
        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Results saved to: {output_file}")
        
        # Show file size
        file_size = output_path.stat().st_size
        print(f"   File size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")


async def main():
    """Main function demonstrating various evaluation scenarios"""
    
    parser = argparse.ArgumentParser(description="Unified Evaluation API Example")
    parser.add_argument('--model', '--models', dest='models', nargs='+', 
                       default=['llama3'], help='Models to evaluate')
    parser.add_argument('--type', dest='eval_type', 
                       choices=['coding', 'vision', 'tools', 'intelligence', 'all'],
                       default='coding', help='Evaluation type')
    parser.add_argument('--free-only', action='store_true',
                       help='Use only free models')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--list-models', action='store_true',
                       help='List available models and exit')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Timeout in seconds')
    
    args = parser.parse_args()
    
    # Initialize example
    example = UnifiedEvaluationExample()
    
    print("🚀 Unified Evaluation API Example")
    print("==================================")
    
    # List models if requested
    if args.list_models:
        print("\nAvailable models:")
        models = example.list_available_models(free_only=args.free_only)
        for model in models:
            capabilities = ', '.join(model['capabilities'])
            cost = 'Free' if model['free'] else 'Paid'
            print(f"  • {model['name']} ({model['provider']}) - {capabilities} - {cost}")
        return
    
    # Validate models
    print(f"\nValidating models: {args.models}")
    validation_results = example.validate_models(args.models)
    
    for model, is_valid in validation_results.items():
        status = "✅" if is_valid else "❌"
        print(f"  {status} {model}")
    
    # Check if any models are invalid
    invalid_models = [m for m, valid in validation_results.items() if not valid]
    if invalid_models:
        print(f"\n⚠️  Invalid models: {invalid_models}")
        if args.free_only:
            print("Try listing available free models: --list-models --free-only")
        else:
            print("Try listing available models: --list-models")
        return
    
    # Run evaluation based on type
    try:
        if args.eval_type == 'coding':
            results = await example.run_coding_evaluation(
                models=args.models,
                problems=['fibonacci', 'palindrome'],
                languages=['python', 'javascript'],
                free_only=args.free_only,
                verbose=args.verbose
            )
        
        elif args.eval_type == 'vision':
            results = await example.run_vision_evaluation(
                models=args.models,
                categories=['object_recognition', 'scene_description'],
                free_only=args.free_only,
                verbose=args.verbose
            )
        
        elif args.eval_type == 'all':
            results = await example.run_comprehensive_evaluation(
                models=args.models,
                free_only=args.free_only,
                timeout=args.timeout,
                verbose=args.verbose
            )
        
        else:
            print(f"❌ Evaluation type '{args.eval_type}' not implemented in this example")
            print("Available types: coding, vision, all")
            return
        
        # Display summary
        print(f"\n📊 Evaluation Summary:")
        if 'summary' in results:
            summary = results['summary']
            print(f"   • Best Model: {summary.get('best_model', 'N/A')}")
            print(f"   • Completion Rate: {summary.get('completion_rate', 0):.1%}")
            print(f"   • Total Duration: {summary.get('total_duration', 0):.1f}s")
        
        if 'model_results' in results:
            print(f"   • Models Evaluated: {len(results['model_results'])}")
            for model_result in results['model_results']:
                model_name = model_result.get('model_name', 'Unknown')
                metrics = model_result.get('metrics', {})
                avg_score = metrics.get('average_score', 0)
                success_rate = metrics.get('success_rate', 0)
                print(f"     - {model_name}: Score {avg_score:.1f}, Success {success_rate:.1%}")
        
        # Save results if output file specified
        if args.output:
            example.save_results(results, args.output)
        
    except Exception as e:
        print(f"❌ Evaluation failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(main())