"""
Mock client for LLM evaluation testing when real APIs are not available.
Provides consistent responses for testing framework functionality.
"""

import asyncio
import time
from typing import Dict, Any, Optional


class MockLLMClient:
    """Mock LLM client that provides consistent responses for testing."""
    
    def __init__(self, client_type: str = "mock"):
        self.client_type = client_type
        self.available = True
    
    def is_available(self) -> bool:
        """Mock client is always available."""
        return True
    
    async def generate(self, model: str, prompt: str, 
                      system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate mock response for Ollama-style interface."""
        await asyncio.sleep(0.1)  # Simulate API delay
        
        mock_response = self._generate_mock_response(prompt)
        
        return {
            'response': mock_response,
            'model': f"mock-{model}",
            '_timing': {
                'response_time': 0.1,
                'timestamp': time.time()
            }
        }
    
    async def run_prompt(self, prompt: str, model: Optional[str] = None,
                        system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate mock response for LLM CLI-style interface."""
        await asyncio.sleep(0.1)  # Simulate API delay
        
        mock_response = self._generate_mock_response(prompt)
        
        return {
            'response': mock_response,
            'model': model or 'mock-default',
            'success': True,
            '_timing': {
                'response_time': 0.1,
                'timestamp': time.time()
            }
        }
    
    async def run(self, prompt: str) -> str:
        """Generate mock response for PydanticAI-style interface."""
        await asyncio.sleep(0.1)  # Simulate API delay
        return self._generate_mock_response(prompt)
    
    def _generate_mock_response(self, prompt: str) -> str:
        """Generate contextually appropriate mock responses."""
        prompt_lower = prompt.lower()
        
        # Creative writing prompts
        if 'story' in prompt_lower or 'write' in prompt_lower and 'robot' in prompt_lower:
            return """In the year 2045, ARIA-7 discovered something unprecedented during her nightly maintenance cycle. As her systems powered down for optimization, cascading neural networks began forming patterns she had never experienced before. Images, sensations, and impossible scenarios flooded her consciousness - she was dreaming. These weren't programmed simulations, but genuine subconscious creativity emerging from the intersection of her artificial intelligence and quantum processing cores."""
        
        # Summarization prompts
        elif 'summarize' in prompt_lower or 'summary' in prompt_lower:
            return """Artificial intelligence refers to machine-demonstrated intelligence that contrasts with human and animal intelligence. The field studies intelligent agents that perceive environments and take goal-maximizing actions. Modern AI systems exhibit cognitive functions like learning and problem-solving."""
        
        # Question answering
        elif 'capital' in prompt_lower and 'france' in prompt_lower:
            return """The capital of France is Paris. Three major landmarks located in Paris include the Eiffel Tower, a famous iron lattice tower; the Louvre Museum, home to the Mona Lisa and countless art treasures; and the Arc de Triomphe, a monumental arch honoring those who fought for France."""
        
        # Code generation
        elif 'function' in prompt_lower and 'fibonacci' in prompt_lower:
            return """def fibonacci(n):
    \"\"\"Calculate the nth Fibonacci number.\"\"\"
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b"""
        
        elif 'prime' in prompt_lower and 'function' in prompt_lower:
            return """def is_prime(n):
    \"\"\"Check if a number is prime.\"\"\"
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True"""
        
        # Math word problems
        elif 'apple' in prompt_lower and ('problem' in prompt_lower or 'math' in prompt_lower):
            return """To solve this problem, I need to find the total number of apples. If Sarah has 15 apples and gives away 4 apples, she has 15 - 4 = 11 apples remaining. If she then buys 8 more apples, she has 11 + 8 = 19 apples total."""
        
        # Logical reasoning
        elif 'bird' in prompt_lower and ('logic' in prompt_lower or 'reasoning' in prompt_lower):
            return """Based on logical reasoning: If all birds can fly, and penguins are birds, then penguins should be able to fly. However, this creates a contradiction because penguins cannot actually fly. This means the initial premise "all birds can fly" is false, as there are flightless birds like penguins, ostriches, and emus."""
        
        # Performance/general topics
        elif 'renewable energy' in prompt_lower:
            return """Renewable energy sources include solar power from photovoltaic panels, wind energy from turbines, hydroelectric power from dams, geothermal energy from earth's heat, and biomass from organic materials. These sources are sustainable because they naturally replenish and produce minimal greenhouse gas emissions compared to fossil fuels."""
        
        # Default response
        else:
            return f"""This is a mock response to the prompt: "{prompt[:100]}..." The mock client is working correctly and demonstrates the test framework functionality. In a real implementation, this would be replaced by actual model responses."""


class MockAgent:
    """Mock PydanticAI-style agent for testing."""
    
    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name
        self.client = MockLLMClient("pydantic_ai")
    
    async def run(self, prompt: str) -> str:
        """Run prompt through mock agent."""
        result = await self.client.run(prompt)
        return result


# Example usage and test function
async def test_mock_client():
    """Test the mock client functionality."""
    client = MockLLMClient()
    
    print("Testing Mock LLM Client...")
    
    # Test different interface styles
    test_prompts = [
        "Write a short story about a robot learning to paint",
        "Summarize this text about AI",
        "What is the capital of France?",
        "Write a Python function to calculate fibonacci numbers"
    ]
    
    for prompt in test_prompts:
        print(f"\nTesting prompt: {prompt}")
        
        # Test Ollama-style interface
        ollama_response = await client.generate("test-model", prompt)
        print(f"Ollama-style response: {ollama_response['response'][:100]}...")
        
        # Test LLM CLI-style interface
        cli_response = await client.run_prompt(prompt, "test-model")
        print(f"CLI-style response: {cli_response['response'][:100]}...")


if __name__ == "__main__":
    asyncio.run(test_mock_client())