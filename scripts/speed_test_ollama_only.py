#!/usr/bin/env python3
"""
Simplified Speed Test Script for 128k Token Processing (Ollama Only)
Tests available Ollama models with 128k token input
"""

import asyncio
import time
import json
import os
import sys
import argparse
import httpx
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / 'src'))


class TokenCounter:
    """Simple token counter (approximation)."""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """Approximate token count (1 token ≈ 4 characters)."""
        return len(text) // 4
    
    @staticmethod
    def generate_128k_content(base_file: str) -> str:
        """Generate content with approximately 128k tokens."""
        with open(base_file, 'r', encoding='utf-8') as f:
            base_content = f.read()
        
        base_tokens = TokenCounter.count_tokens(base_content)
        target_tokens = 128_000
        repetitions = max(1, target_tokens // base_tokens + 1)
        
        content_parts = []
        for i in range(repetitions):
            content_parts.append(f"\n\n--- ITERATION {i+1} ---\n\n")
            content_parts.append(base_content)
            
            # Check if we've reached target
            current_content = ''.join(content_parts)
            if TokenCounter.count_tokens(current_content) >= target_tokens:
                break
        
        final_content = ''.join(content_parts)
        actual_tokens = TokenCounter.count_tokens(final_content)
        print(f"Generated content with ~{actual_tokens:,} tokens (target: 128k)")
        
        return final_content


class OllamaClient:
    """Ollama API client for speed testing."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    async def list_models(self) -> List[str]:
        """List available models in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
        except Exception as e:
            print(f"❌ Failed to list Ollama models: {e}")
            return []
    
    async def generate_response(self, model: str, prompt: str) -> Dict[str, Any]:
        """Generate response using Ollama API."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:  # Longer timeout for large prompts
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 100  # Limit response length for speed test
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                end_time = time.time()
                
                return {
                    "response": data.get("response", ""),
                    "response_time": end_time - start_time,
                    "model": model,
                    "provider": "ollama",
                    "prompt_tokens": TokenCounter.count_tokens(prompt),
                    "response_tokens": TokenCounter.count_tokens(data.get("response", "")),
                    "total_tokens": TokenCounter.count_tokens(prompt) + TokenCounter.count_tokens(data.get("response", "")),
                    "tokens_per_second": TokenCounter.count_tokens(data.get("response", "")) / (end_time - start_time) if (end_time - start_time) > 0 else 0
                }
        except Exception as e:
            return {
                "error": str(e),
                "response_time": time.time() - start_time,
                "model": model,
                "provider": "ollama"
            }


class SpeedTestRunner:
    """Main speed test runner for Ollama models."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.results = []
    
    async def run_speed_test(self, content: str, models: List[str], iterations: int = 3) -> Dict[str, Any]:
        """Run speed test with multiple Ollama models."""
        print(f"🚀 Starting speed test with {len(models)} models, {iterations} iterations each")
        print(f"Content length: ~{TokenCounter.count_tokens(content):,} tokens")
        
        # Test prompt
        test_prompt = f"""Please analyze the following content and provide a brief summary:

{content}

Summary:"""
        
        results = {
            "test_config": {
                "iterations": iterations,
                "content_tokens": TokenCounter.count_tokens(content),
                "prompt_tokens": TokenCounter.count_tokens(test_prompt),
                "models_tested": models
            },
            "model_results": {},
            "comparison": {}
        }
        
        # Test each model
        for model in models:
            print(f"\n📊 Testing {model}...")
            model_results = []
            
            for i in range(iterations):
                print(f"  Iteration {i+1}/{iterations}")
                result = await self.ollama_client.generate_response(model, test_prompt)
                model_results.append(result)
                
                if "error" not in result:
                    print(f"    Response time: {result['response_time']:.2f}s")
                    print(f"    Tokens/sec: {result['tokens_per_second']:.1f}")
                else:
                    print(f"    Error: {result['error']}")
            
            results["model_results"][model] = model_results
        
        # Calculate comparison
        results["comparison"] = self._calculate_comparison(results["model_results"])
        
        return results
    
    def _calculate_comparison(self, model_results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate performance comparison between models."""
        comparison = {}
        
        for model, results in model_results.items():
            # Filter successful results
            successful_results = [r for r in results if "error" not in r]
            
            if successful_results:
                times = [r["response_time"] for r in successful_results]
                tokens_per_sec = [r["tokens_per_second"] for r in successful_results]
                
                comparison[model] = {
                    "mean_time": statistics.mean(times),
                    "median_time": statistics.median(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
                    "mean_tokens_per_sec": statistics.mean(tokens_per_sec),
                    "success_rate": len(successful_results) / len(results)
                }
        
        # Find fastest model
        if comparison:
            fastest_model = min(comparison.keys(), key=lambda m: comparison[m]["mean_time"])
            comparison["fastest_model"] = fastest_model
            comparison["performance_ranking"] = sorted(
                comparison.keys(), 
                key=lambda m: comparison[m]["mean_time"]
            )
        
        return comparison
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted results."""
        print("\n" + "="*60)
        print("🏁 OLLAMA SPEED TEST RESULTS")
        print("="*60)
        
        config = results["test_config"]
        print(f"Content tokens: {config['content_tokens']:,}")
        print(f"Prompt tokens: {config['prompt_tokens']:,}")
        print(f"Models tested: {', '.join(config['models_tested'])}")
        print(f"Iterations per model: {config['iterations']}")
        
        comparison = results["comparison"]
        
        # Print results for each model
        for model in config["models_tested"]:
            if model in comparison:
                stats = comparison[model]
                print(f"\n📊 {model}:")
                print(f"  Mean response time: {stats['mean_time']:.2f}s")
                print(f"  Median response time: {stats['median_time']:.2f}s")
                print(f"  Min/Max: {stats['min_time']:.2f}s / {stats['max_time']:.2f}s")
                print(f"  Mean tokens/sec: {stats['mean_tokens_per_sec']:.1f}")
                print(f"  Success rate: {stats['success_rate']:.1%}")
        
        # Performance ranking
        if "performance_ranking" in comparison:
            print(f"\n🏆 Performance Ranking (fastest to slowest):")
            for i, model in enumerate(comparison["performance_ranking"], 1):
                time_val = comparison[model]["mean_time"]
                tokens_sec = comparison[model]["mean_tokens_per_sec"]
                print(f"  {i}. {model}: {time_val:.2f}s ({tokens_sec:.1f} tokens/sec)")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="128k Token Speed Test (Ollama Only)")
    parser.add_argument("--iterations", type=int, default=3, help="Number of test iterations")
    parser.add_argument("--source-file", default="archive/simonwilison-llm-latest-30.md", 
                       help="Source file for content generation")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--models", nargs="+", help="Specific models to test")
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    
    args = parser.parse_args()
    
    # Initialize client
    runner = SpeedTestRunner()
    
    # List models if requested
    if args.list_models:
        print("📋 Available Ollama models:")
        models = await runner.ollama_client.list_models()
        for model in models:
            print(f"  - {model}")
        return 0
    
    # Check if source file exists
    source_file = Path(args.source_file)
    if not source_file.exists():
        print(f"❌ Source file not found: {source_file}")
        return 1
    
    # Determine models to test
    if args.models:
        models_to_test = args.models
    else:
        # Auto-detect available models
        available_models = await runner.ollama_client.list_models()
        if not available_models:
            print("❌ No Ollama models found. Please install some models first.")
            print("Example: ollama pull llama3.3:8b")
            return 1
        
        # Prefer gpt-oss if available, otherwise use first few models
        models_to_test = []
        if any("gpt-oss" in model for model in available_models):
            models_to_test.extend([m for m in available_models if "gpt-oss" in m])
        else:
            # Use first 2-3 available models
            models_to_test = available_models[:3]
    
    print(f"🎯 Testing models: {', '.join(models_to_test)}")
    
    # Generate 128k token content
    print("📝 Generating 128k token content...")
    content = TokenCounter.generate_128k_content(str(source_file))
    
    # Run speed test
    results = await runner.run_speed_test(content, models_to_test, args.iterations)
    
    # Print results
    runner.print_results(results)
    
    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
