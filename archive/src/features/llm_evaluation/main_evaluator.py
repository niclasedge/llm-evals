# Main LLM Evaluator Script

import sys
import asyncio
import argparse
from pathlib import Path
from pydantic_ai.agent import AgentRunResult # Added import

from . import config
from . import llm_service
from .test_framework import TestRunner
from .tests.standard_tests import TextGenerationTests, CodeGenerationTests, ReasoningTests, PerformanceTests
from .vision_evaluator import VisionEvaluator
from .image_evaluator import ImageGenerationEvaluator

# The VERY IMPORTANT NOTE regarding file location has been removed as the file is now in the correct place.

async def run_evaluations():
    """Runs evaluations based on the settings in config.py."""
    print("Starting LLM Evaluations...")

    test_queries = [
        "What is the capital of France?",
        "Explain the concept of photosynthesis in simple terms.",
        "Write a short poem about a rainy day.",
        "What are the main benefits of using Python for programming?"
    ]

    # Evaluate Ollama Models
    if config.ENABLE_OLLAMA and config.OLLAMA_MODELS_TO_TEST:
        print("\n--- Evaluating Ollama Models ---")
        for model_name in config.OLLAMA_MODELS_TO_TEST:
            print(f"\n-- Model: {model_name} (Ollama) --")
            agent = llm_service.get_llm_agent("ollama", model_name)
            if agent:
                for i, query in enumerate(test_queries):
                    print(f"  Query {i+1}: {query}")
                    response = await llm_service.run_query(agent, query)
                    if isinstance(response, AgentRunResult):
                        print(f"  Response: {response.output}")
                    elif response is None:
                        print(f"  Response: None")
                    else:
                        print(f"  Response: {response}") # Should be a string if not AgentRunResult or None
            else:
                print(f"  Skipping {model_name} as agent could not be initialized.")
    elif config.ENABLE_OLLAMA:
        print("\nOllama is enabled, but no models are listed in OLLAMA_MODELS_TO_TEST.")
    else:
        print("\nOllama evaluations are disabled in the configuration.")

    # Evaluate OpenRouter Models
    if config.ENABLE_OPENROUTER and config.OPENROUTER_MODELS_TO_TEST:
        print("\n--- Evaluating OpenRouter Models ---")
        if not config.OPENROUTER_API_KEY:
            print("OpenRouter API Key is not set. Cannot proceed with OpenRouter evaluations.")
        else:
            for model_identifier in config.OPENROUTER_MODELS_TO_TEST:
                print(f"\n-- Model: {model_identifier} (OpenRouter) --")
                agent = llm_service.get_llm_agent("openrouter", model_identifier)
                if agent:
                    for i, query in enumerate(test_queries):
                        print(f"  Query {i+1}: {query}")
                        response = await llm_service.run_query(agent, query)
                        if isinstance(response, AgentRunResult):
                            print(f"  Response: {response.output}")
                        elif response is None:
                            print(f"  Response: None")
                        else:
                            print(f"  Response: {response}") # Should be a string if not AgentRunResult or None
                else:
                    print(f"  Skipping {model_identifier} as agent could not be initialized.")
    elif config.ENABLE_OPENROUTER:
        print("\nOpenRouter is enabled, but no models are listed in OPENROUTER_MODELS_TO_TEST.")
    else:
        print("\nOpenRouter evaluations are disabled in the configuration.")

    print("\nLLM Evaluations Finished.")

async def run_new_test_framework():
    """Run evaluations using the new test framework."""
    print("Starting New LLM Test Framework...")
    
    # Create test configuration
    test_config = {
        'name': 'Integrated LLM Evaluation',
        'version': '1.0',
        'tests': []
    }
    
    # Add all standard tests
    all_tests = []
    all_tests.extend(TextGenerationTests.get_all_tests())
    all_tests.extend(CodeGenerationTests.get_all_tests()[:2])  # Limit code tests
    all_tests.extend(ReasoningTests.get_all_tests()[:2])     # Limit reasoning tests
    all_tests.extend(PerformanceTests.get_all_tests()[:1])   # Limit performance tests
    
    for test in all_tests:
        test_config['tests'].append({
            'name': test.name,
            'type': test.__class__.__name__,
            'description': test.description,
            'prompt': test.get_test_prompt(),
            'system_prompt': test.get_system_prompt(),
            'min_length': test.config.get('min_length', 30),
            **test.config
        })
    
    print(f"Running {len(test_config['tests'])} tests...")
    
    # Run tests
    async with TestRunner(test_config) as runner:
        results = await runner.run_test_suite()
        
        # Print summary
        summary = results['summary']
        print("\n" + "="*50)
        print("NEW TEST FRAMEWORK RESULTS")
        print("="*50)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Errors: {summary['errors']} ⚠️")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Average Score: {summary['average_score']:.2f}")
        print(f"Execution Time: {summary['execution_time']:.2f}s")
        
        # Generate report
        output_dir = Path("test_results")
        output_dir.mkdir(exist_ok=True)
        
        report_file = output_dir / "evaluation_report.md"
        report = runner.generate_report(results, report_file)
        
        results_file = output_dir / "evaluation_results.json"
        runner.save_results(results, results_file)
        
        print(f"\n📄 Report saved to: {report_file}")
        print(f"💾 Results saved to: {results_file}")


async def run_tool_call_tests():
    """Run tool call evaluations using the new tool call testing framework."""
    from .tool_call_tests import ToolCallTestRunner, ToolCallScenarioFactory
    from .test_framework.mock_client import MockAgent
    
    print("Starting Tool Call Test Framework...")
    
    # Create mock client for testing (will be replaced with real agents when API keys are available)
    mock_agent = MockAgent()
    
    # Initialize test runner
    runner = ToolCallTestRunner()
    
    # Get all scenarios
    all_scenarios = ToolCallScenarioFactory.get_all_scenarios()
    print(f"Running {len(all_scenarios)} tool call tests...")
    
    # Run the test suite
    results = await runner.run_test_suite(all_scenarios, mock_agent)
    
    # Print summary
    runner.print_summary(results)
    
    # Generate and save reports
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    report_file = output_dir / "tool_call_evaluation_report.md"
    report = runner.generate_report(results, report_file)
    
    results_file = output_dir / "tool_call_evaluation_results.json"
    runner.save_results(results, results_file)
    
    print(f"\n📄 Tool call report saved to: {report_file}")
    print(f"💾 Tool call results saved to: {results_file}")
    
    return results


async def run_vision_tests():
    """Run vision evaluations using the vision test framework."""
    if not config.ENABLE_VISION_TESTING:
        print("Vision testing is disabled in configuration.")
        return
    
    print("Starting Vision Test Framework...")
    
    # Initialize vision evaluator
    evaluator = VisionEvaluator()
    
    all_results = []
    
    # Test OpenRouter vision models
    if config.ENABLE_OPENROUTER and config.OPENROUTER_VISION_MODELS_TO_TEST:
        print(f"\n--- Testing OpenRouter Vision Models ---")
        for model_identifier in config.OPENROUTER_VISION_MODELS_TO_TEST:
            print(f"\nTesting {model_identifier}...")
            try:
                results = await evaluator.run_vision_evaluation("openrouter", model_identifier)
                all_results.append(results)
            except Exception as e:
                print(f"Error testing {model_identifier}: {e}")
                continue
    
    # Test Ollama vision models
    if config.ENABLE_OLLAMA and config.OLLAMA_VISION_MODELS_TO_TEST:
        print(f"\n--- Testing Ollama Vision Models ---")
        for model_identifier in config.OLLAMA_VISION_MODELS_TO_TEST:
            print(f"\nTesting {model_identifier}...")
            try:
                results = await evaluator.run_vision_evaluation("ollama", model_identifier)
                all_results.append(results)
            except Exception as e:
                print(f"Error testing {model_identifier}: {e}")
                continue
    
    # Generate consolidated report
    if all_results:
        print("\n" + "="*50)
        print("VISION TEST FRAMEWORK RESULTS")
        print("="*50)
        
        total_tests = sum(r['summary']['total_tests'] for r in all_results)
        total_successful = sum(r['summary']['successful_tests'] for r in all_results)
        total_failed = sum(r['summary']['failed_tests'] for r in all_results)
        
        print(f"Total Models Tested: {len(all_results)}")
        print(f"Total Tests: {total_tests}")
        print(f"Successful Tests: {total_successful}")
        print(f"Failed Tests: {total_failed}")
        
        if total_tests > 0:
            overall_success_rate = total_successful / total_tests
            print(f"Overall Success Rate: {overall_success_rate:.1%}")
        
        # Save consolidated results
        output_dir = Path("test_results")
        output_dir.mkdir(exist_ok=True)
        
        consolidated_results_file = output_dir / "vision_evaluation_consolidated.json"
        with open(consolidated_results_file, 'w') as f:
            import json
            json.dump(all_results, f, indent=2, default=str)
        
        print(f"\n📄 Consolidated vision results saved to: {consolidated_results_file}")
        
        # Generate individual reports for each model
        for results in all_results:
            model_name = f"{results['model_provider']}_{results['model_identifier'].replace('/', '_').replace(':', '_')}"
            report_file = output_dir / f"vision_report_{model_name}.md"
            evaluator.generate_report(results, report_file)
            
            results_file = output_dir / f"vision_results_{model_name}.json"
            evaluator.save_results(results, results_file)
    
    else:
        print("No vision models were successfully tested.")
    
    return all_results


async def run_image_generation_tests():
    """Run image generation evaluations using the image generation test framework."""
    if not config.ENABLE_IMAGE_GENERATION:
        print("Image generation testing is disabled in configuration.")
        return
    
    print("Starting Image Generation Test Framework...")
    
    # Initialize image generation evaluator
    evaluator = ImageGenerationEvaluator()
    
    try:
        # Run image generation evaluation
        results = await evaluator.run_evaluation()
        
        if results.get("status") == "disabled":
            print("Image generation evaluation is disabled.")
            return results
        
        if results.get("status") == "error":
            print(f"Error in image generation evaluation: {results.get('message')}")
            return results
        
        # Print summary
        summary = results.get("summary", {})
        print("\n" + "="*50)
        print("IMAGE GENERATION TEST RESULTS")
        print("="*50)
        print(f"Total Providers: {summary.get('total_providers', 0)}")
        print(f"Total Models: {summary.get('total_models', 0)}")
        print(f"Total Generations: {summary.get('total_generations', 0)}")
        print(f"Successful Generations: {summary.get('successful_generations', 0)}")
        print(f"Failed Generations: {summary.get('failed_generations', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1%}")
        print(f"Average Generation Time: {summary.get('average_generation_time', 0):.2f}s")
        
        # Show provider performance
        print("\n--- Provider Performance ---")
        for provider, perf in summary.get("provider_performance", {}).items():
            print(f"{provider}: {perf['success_rate']:.1%} success rate, {perf['average_time']:.2f}s avg time")
        
        # Show model performance
        print("\n--- Model Performance ---")
        for model, perf in summary.get("model_performance", {}).items():
            print(f"{model}: {perf['success_rate']:.1%} success rate, {perf['average_time']:.2f}s avg time")
        
        print(f"\n📄 Detailed results saved to: image_evaluation_results/")
        
        return results
        
    except Exception as e:
        print(f"Error running image generation tests: {e}")
        return {"status": "error", "message": str(e)}


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="LLM Evaluation Tool")
    parser.add_argument(
        '--framework',
        choices=['legacy', 'new', 'tool_calls', 'vision', 'image_generation'],
        default='new',
        help='Choose evaluation framework to use'
    )
    
    args = parser.parse_args()
    
    if args.framework == 'legacy':
        print("Running legacy evaluation framework...")
        asyncio.run(run_evaluations())
    elif args.framework == 'tool_calls':
        print("Running tool call test framework...")
        asyncio.run(run_tool_call_tests())
    elif args.framework == 'vision':
        print("Running vision test framework...")
        asyncio.run(run_vision_tests())
    elif args.framework == 'image_generation':
        print("Running image generation test framework...")
        asyncio.run(run_image_generation_tests())
    else:
        print("Running new test framework...")
        asyncio.run(run_new_test_framework())


if __name__ == "__main__":
    # Ensure you have your OPENROUTER_API_KEY environment variable set if testing OpenRouter
    # e.g., export OPENROUTER_API_KEY='your_key_here'
    # Ensure Ollama is running and models in OLLAMA_MODELS_TO_TEST are pulled.
    main()

