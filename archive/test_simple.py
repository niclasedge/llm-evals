#!/usr/bin/env python3
"""
Simple test to verify the framework works without external dependencies.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.features.llm_evaluation.test_framework.base_test import BaseTest, TestResult, TestStatus


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, responses=None):
        self.responses = responses or {}
    
    async def generate(self, model, prompt, system_prompt=None):
        """Mock generate method."""
        return {
            'response': self.responses.get(prompt, f"Mock response for: {prompt[:50]}...")
        }


class SimpleTest(BaseTest):
    """Simple test that always passes."""
    
    async def run(self, client, model, **kwargs):
        """Run simple test."""
        prompt = self.get_test_prompt()
        
        # Get response from mock client
        response = await client.generate(model=model, prompt=prompt)
        text_response = response.get('response', '')
        
        # Always pass if we get any response
        is_valid = len(text_response) > 0
        score = 1.0 if is_valid else 0.0
        
        status = TestStatus.PASSED if is_valid else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': text_response,
                'model': model
            }
        )


async def test_framework():
    """Test the framework with mock data."""
    print("🧪 Testing LLM Evaluation Framework")
    print("=" * 50)
    
    # Create a simple test
    test = SimpleTest(
        name="simple_test",
        description="A simple test that should pass",
        config={
            'prompt': 'Hello, how are you?',
            'system_prompt': 'You are a helpful assistant.'
        }
    )
    
    # Create mock client
    client = MockLLMClient(responses={
        'Hello, how are you?': 'Hello! I am doing well, thank you for asking.'
    })
    
    # Run the test
    result = await test.run_with_timing(client, "mock-model")
    
    # Print results
    print(f"Test: {result.test_name}")
    print(f"Status: {result.status.value}")
    print(f"Score: {result.score}")
    print(f"Execution Time: {result.execution_time:.3f}s")
    print(f"Response: {result.details['response']}")
    
    assert result.status == TestStatus.PASSED, f"Framework test failed with status: {result.status.value}"
    print("\n✅ Framework test PASSED!")


if __name__ == "__main__":
    try:
        asyncio.run(test_framework())
        sys.exit(0)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)