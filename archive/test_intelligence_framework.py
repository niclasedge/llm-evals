#!/usr/bin/env python3
"""
Test script to verify intelligence testing framework integration.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_intelligence_imports():
    """Test that all intelligence modules can be imported."""
    print("🧠 Testing Intelligence Framework Imports...")
    
    # Test base framework imports
    from src.features.llm_evaluation.intelligence_tests import (
        IntelligenceTestBase, IntelligenceTestResult, 
        IntelligenceTestRunner, IntelligenceResultAnalyzer
    )
    print("✅ Base intelligence framework imports successful")
    
    # Test specific test imports
    from src.features.llm_evaluation.intelligence_tests.tests.graphviz_tests import GraphvizTests
    from src.features.llm_evaluation.intelligence_tests.tests.logic_tests import LogicTests
    from src.features.llm_evaluation.intelligence_tests.tests.pattern_tests import PatternTests
    from src.features.llm_evaluation.intelligence_tests.tests.creative_tests import CreativeTests
    print("✅ Test modules imports successful")
    
    # Test intelligence evaluator
    from src.features.llm_evaluation.intelligence_evaluator import IntelligenceEvaluator
    print("✅ Intelligence evaluator import successful")
    
    assert True

def test_test_registry():
    """Test that tests can be registered and retrieved."""
    print("\n🔧 Testing Test Registry...")
    
    from src.features.llm_evaluation.intelligence_tests import IntelligenceTestRunner
    
    runner = IntelligenceTestRunner()
    available_tests = runner.get_available_tests()
    
    print(f"✅ Found {len(available_tests)} available tests:")
    for test_name in available_tests[:5]:  # Show first 5
        print(f"   - {test_name}")
    if len(available_tests) > 5:
        print(f"   ... and {len(available_tests) - 5} more")
    
    # Test getting tests by category
    from src.features.llm_evaluation.intelligence_tests.base_test import IntelligenceCategory
    
    for category in IntelligenceCategory:
        category_tests = runner.get_tests_by_category(category)
        print(f"   {category.value}: {len(category_tests)} tests")
    
    assert len(available_tests) > 0, "No tests available in registry"

async def test_mock_test_execution():
    """Test that tests can be executed with mock client."""
    print("\n🚀 Testing Mock Test Execution...")
    
    from src.features.llm_evaluation.intelligence_tests import IntelligenceTestRunner
    from src.features.llm_evaluation.intelligence_tests.base_test import IntelligenceTestResult, TestStatus
    
    # Create a mock client for testing
    class MockClient:
        async def generate(self, model, prompt, system_prompt=None):
            return {"response": "This is a mock response for testing purposes."}
    
    runner = IntelligenceTestRunner()
    mock_client = MockClient()
    
    # Get a simple test to run
    available_tests = runner.get_available_tests()
    assert len(available_tests) > 0, "No tests available to run"
    
    test_name = available_tests[0]
    print(f"   Running test: {test_name}")
    
    result = await runner.run_test(test_name, mock_client, "mock_model")
    
    assert isinstance(result, IntelligenceTestResult), f"Unexpected result type: {type(result)}"
    print(f"✅ Test completed: {result.test_name}")
    print(f"   Status: {result.status.value}")
    print(f"   Score: {result.score}")
    assert True

def test_intelligence_evaluator():
    """Test that intelligence evaluator can be created and configured."""
    print("\n📊 Testing Intelligence Evaluator...")
    
    from src.features.llm_evaluation.intelligence_evaluator import IntelligenceEvaluator
    
    evaluator = IntelligenceEvaluator()
    
    # Test getting available tests
    available_tests = evaluator.get_available_tests()
    print(f"✅ Evaluator has access to {sum(len(tests) for tests in available_tests.values())} tests")
    
    for category, tests in available_tests.items():
        if tests:  # Only show categories with tests
            print(f"   {category}: {len(tests)} tests")
    
    # Test getting test info
    all_test_names = [test for tests in available_tests.values() for test in tests]
    if all_test_names:
        test_info = evaluator.get_test_info(all_test_names[0])
        assert test_info is not None, "Could not retrieve test info"
        print(f"✅ Test info retrieval works: {test_info['name']}")
    
    assert True

def main():
    """Run all framework tests."""
    print("🧪 Intelligence Testing Framework Verification")
    print("=" * 50)
    
    tests = [
        test_intelligence_imports,
        test_test_registry,
        test_mock_test_execution,
        test_intelligence_evaluator
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All framework tests PASSED! Intelligence testing is ready.")
        print("\nTo run intelligence tests on actual models:")
        print("1. Set OPENROUTER_API_KEY environment variable")
        print("2. Run: python -c \"from src.features.llm_evaluation.intelligence_evaluator import run_intelligence_evaluation; import asyncio; asyncio.run(run_intelligence_evaluation())\"")
        return True
    else:
        print(f"❌ {total - passed} tests FAILED. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)