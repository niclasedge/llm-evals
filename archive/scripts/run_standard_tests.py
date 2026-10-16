#!/usr/bin/env python3
"""
Run standardized LLM evaluation tests.
Based on Simon Willison's LLM CLI patterns and comprehensive test framework.
"""

import asyncio
import argparse
import sys
import json
import yaml
from pathlib import Path
from typing import List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.features.llm_evaluation.test_framework import TestRunner
from src.features.llm_evaluation.tests.standard_tests import (
    TextGenerationTests, CodeGenerationTests, ReasoningTests, PerformanceTests
)


def load_test_config(config_file: str) -> dict:
    """Load test configuration from YAML file."""
    config_path = project_root / "src/features/llm_evaluation/tests/test_configs" / config_file
    
    if not config_path.exists():
        raise FileNotFoundError(f"Test config not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def create_test_config_from_args(args) -> dict:
    """Create test configuration from command line arguments."""
    if args.config:
        return load_test_config(args.config)
    
    # Create default configuration
    config = {
        'name': 'Command Line Test Suite',
        'version': '1.0',
        'tests': []
    }
    
    # Add tests based on categories
    if not args.category or 'text' in args.category:
        text_tests = TextGenerationTests.get_all_tests()
        for test in text_tests:
            config['tests'].append({
                'name': test.name,
                'type': 'TextGenerationTest',
                'description': test.description,
                'prompt': test.get_test_prompt(),
                'system_prompt': test.get_system_prompt(),
                'min_length': test.config.get('min_length', 30)
            })
    
    if not args.category or 'code' in args.category:
        code_tests = CodeGenerationTests.get_all_tests()
        for test in code_tests:
            config['tests'].append({
                'name': test.name,
                'type': 'CodeGenerationTest', 
                'description': test.description,
                'prompt': test.get_test_prompt(),
                'system_prompt': test.get_system_prompt(),
                'min_length': test.config.get('min_length', 30)
            })
    
    if not args.category or 'reasoning' in args.category:
        reasoning_tests = ReasoningTests.get_all_tests()
        for test in reasoning_tests:
            config['tests'].append({
                'name': test.name,
                'type': 'ReasoningTest',
                'description': test.description,
                'prompt': test.get_test_prompt(),
                'system_prompt': test.get_system_prompt(),
                'min_length': test.config.get('min_length', 30)
            })
    
    if not args.category or 'performance' in args.category:
        perf_tests = PerformanceTests.get_all_tests()
        for test in perf_tests:
            config['tests'].append({
                'name': test.name,
                'type': 'PerformanceTest',
                'description': test.description,
                'prompt': test.get_test_prompt(),
                'system_prompt': test.get_system_prompt(),
                'min_length': test.config.get('min_length', 30)
            })
    
    return config


async def run_tests(args):
    """Run the test suite."""
    print(f"🚀 Running LLM Evaluation Tests")
    print("=" * 50)
    
    # Load configuration
    try:
        config = create_test_config_from_args(args)
        print(f"📋 Loaded test suite: {config['name']}")
        print(f"   Tests to run: {len(config['tests'])}")
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False
    
    # Filter tests if specified
    test_names = args.tests.split(',') if args.tests else None
    if test_names:
        print(f"   Filtering to tests: {test_names}")
    
    # Filter models if specified
    models = args.models.split(',') if args.models else None
    if models:
        print(f"   Testing models: {models}")
    
    # Filter clients if specified
    clients = args.clients.split(',') if args.clients else None
    if clients:
        print(f"   Using clients: {clients}")
    
    print()
    
    # Run tests
    try:
        async with TestRunner(config) as runner:
            results = await runner.run_test_suite(
                test_names=test_names,
                models=models,
                clients=clients
            )
            
            # Print results summary
            summary = results['summary']
            print("\n" + "="*50)
            print("TEST RESULTS SUMMARY")
            print("="*50)
            print(f"Total Tests: {summary['total_tests']}")
            print(f"Passed: {summary['passed']} ✅")
            print(f"Failed: {summary['failed']} ❌")
            print(f"Errors: {summary['errors']} ⚠️")
            print(f"Success Rate: {summary['success_rate']:.1%}")
            print(f"Average Score: {summary['average_score']:.2f}")
            print(f"Execution Time: {summary['execution_time']:.2f}s")
            
            # Generate detailed report if requested
            if args.report:
                output_file = Path(args.output) / "test_report.md"
                report = runner.generate_report(results, output_file)
                print(f"\n📄 Detailed report saved to: {output_file}")
            
            # Save raw results
            if args.save_results:
                output_file = Path(args.output) / "test_results.json"
                runner.save_results(results, output_file)
                print(f"💾 Raw results saved to: {output_file}")
            
            # Print individual test results if verbose
            if args.verbose:
                print("\n" + "="*50)
                print("INDIVIDUAL TEST RESULTS")
                print("="*50)
                for result in results['results']:
                    status_icon = {
                        'passed': '✅',
                        'failed': '❌', 
                        'error': '⚠️'
                    }.get(result['status'], '❓')
                    
                    score_str = f" ({result['score']:.2f})" if result['score'] else ""
                    time_str = f" [{result['execution_time']:.2f}s]" if result['execution_time'] else ""
                    
                    print(f"{status_icon} {result['test_name']}{score_str}{time_str}")
                    print(f"   Model: {result['details'].get('model', 'Unknown')}")
                    print(f"   Client: {result['details'].get('client_type', 'Unknown')}")
                    
                    if result['error']:
                        print(f"   Error: {result['error']}")
                    
                    print()
            
            return summary['success_rate'] > 0.5
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run standardized LLM evaluation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python scripts/run_standard_tests.py
  
  # Run only text generation tests
  python scripts/run_standard_tests.py --category text
  
  # Run specific tests
  python scripts/run_standard_tests.py --tests "creative_writing_robot,fibonacci_function"
  
  # Test specific models
  python scripts/run_standard_tests.py --models "llama3,gpt-3.5-turbo"
  
  # Use specific clients
  python scripts/run_standard_tests.py --clients "ollama,llm_cli"
  
  # Run with custom config
  python scripts/run_standard_tests.py --config basic_tests.yaml
  
  # Generate detailed report
  python scripts/run_standard_tests.py --report --verbose
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Test configuration file (YAML)',
        default=None
    )
    
    parser.add_argument(
        '--category',
        choices=['text', 'code', 'reasoning', 'performance'],
        help='Test category to run',
        default=None
    )
    
    parser.add_argument(
        '--tests', '-t',
        help='Comma-separated list of specific tests to run',
        default=None
    )
    
    parser.add_argument(
        '--models', '-m',
        help='Comma-separated list of models to test',
        default=None
    )
    
    parser.add_argument(
        '--clients',
        choices=['ollama', 'llm_cli', 'pydantic_ai'],
        help='Comma-separated list of clients to use',
        default=None
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output directory for results',
        default='test_results'
    )
    
    parser.add_argument(
        '--report', '-r',
        action='store_true',
        help='Generate detailed markdown report'
    )
    
    parser.add_argument(
        '--save-results',
        action='store_true',
        help='Save raw results to JSON file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed test results'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimize output'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output).mkdir(exist_ok=True)
    
    # Run tests
    try:
        success = asyncio.run(run_tests(args))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()