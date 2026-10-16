#!/usr/bin/env python3
"""
Speed Test Script for 128k Token Processing
Compares Ollama vs MLX-LM performance with gpt-oss model
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

# Remove the import that's not needed for this script
# from core.llm_client import LLMMessage, LLMResponse


class TokenCounter:
    """Simple token counter (approximation)."""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """Approximate token count (1 token ≈ 4 characters)."""
        return len(text) // 4
    
    @staticmethod
    def generate_120k_content(base_file: str) -> str:
        """Generate content with approximately 120k tokens (max limit)."""
        with open(base_file, 'r', encoding='utf-8') as f:
            base_content = f.read()

        base_tokens = TokenCounter.count_tokens(base_content)
        target_tokens = 120_000  # Reduced from 128k to 120k
        repetitions = max(1, target_tokens // base_tokens + 1)

        content_parts = []
        for i in range(repetitions):
            content_parts.append(f"\n\n--- ITERATION {i+1} ---\n\n")
            content_parts.append(base_content)

            # Check if we've reached target (but don't exceed 120k)
            current_content = ''.join(content_parts)
            current_tokens = TokenCounter.count_tokens(current_content)
            if current_tokens >= target_tokens:
                # Trim to exactly 120k tokens if we exceeded
                if current_tokens > 120_000:
                    # Remove the last iteration and trim
                    content_parts = content_parts[:-2]  # Remove last iteration marker and content
                    current_content = ''.join(content_parts)
                break

        final_content = ''.join(content_parts)
        actual_tokens = TokenCounter.count_tokens(final_content)
        print(f"Generated content with ~{actual_tokens:,} tokens (target: 120k max)")

        return final_content


class OllamaClient:
    """Ollama API client for speed testing."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    async def generate_response(self, model: str, prompt: str) -> Dict[str, Any]:
        """Generate response using Ollama API."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 1500,  # Allow 1000 words summary (~1500 tokens)
                            "num_ctx": 131072  # Set context length to 131k (gpt-oss max)
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                end_time = time.time()
                
                response_tokens = TokenCounter.count_tokens(data.get("response", ""))
                response_time = end_time - start_time

                return {
                    "response": data.get("response", ""),
                    "response_time": response_time,
                    "model": model,
                    "provider": "ollama",
                    "prompt_tokens": TokenCounter.count_tokens(prompt),
                    "response_tokens": response_tokens,
                    "total_tokens": TokenCounter.count_tokens(prompt) + response_tokens,
                    "tokens_per_second": response_tokens / response_time if response_time > 0 else 0
                }
        except Exception as e:
            return {
                "error": str(e),
                "response_time": time.time() - start_time,
                "model": model,
                "provider": "ollama"
            }


class MLXClient:
    """MLX-LM client for speed testing."""

    def __init__(self, model_path: str = "halley-ai/gpt-oss-20b-MLX-5bit-gs32", server_port: int = 8081):
        self.model_path = model_path
        self.server_url = f"http://localhost:{server_port}"  # MLX server port

    async def generate_response(self, prompt: str) -> Dict[str, Any]:
        """Generate response using MLX-LM server."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.server_url}/v1/chat/completions",
                    json={
                        "model": self.model_path,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1500,  # Allow 1000 words summary (~1500 tokens)
                        "temperature": 0.1
                    }
                )
                response.raise_for_status()
                data = response.json()

                end_time = time.time()

                response_content = ""
                if "choices" in data and len(data["choices"]) > 0:
                    response_content = data["choices"][0]["message"]["content"]

                response_tokens = TokenCounter.count_tokens(response_content)
                response_time = end_time - start_time

                return {
                    "response": response_content,
                    "response_time": response_time,
                    "model": self.model_path,
                    "provider": "mlx",
                    "prompt_tokens": TokenCounter.count_tokens(prompt),
                    "response_tokens": response_tokens,
                    "total_tokens": TokenCounter.count_tokens(prompt) + response_tokens,
                    "tokens_per_second": response_tokens / response_time if response_time > 0 else 0
                }
        except Exception as e:
            return {
                "error": str(e),
                "response_time": time.time() - start_time,
                "model": self.model_path,
                "provider": "mlx"
            }

    async def generate_response_direct(self, prompt: str) -> Dict[str, Any]:
        """Generate response using MLX-LM directly (fallback method)."""
        start_time = time.time()

        try:
            # Try using mlx_lm directly
            import subprocess
            import json

            cmd = [
                "python", "-m", "mlx_lm.generate",
                "--model", self.model_path,
                "--prompt", prompt,
                "--max-tokens", "1500",
                "--temp", "0.1"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            end_time = time.time()

            if result.returncode == 0:
                response_content = result.stdout.strip()
                response_tokens = TokenCounter.count_tokens(response_content)
                response_time = end_time - start_time

                return {
                    "response": response_content,
                    "response_time": response_time,
                    "model": self.model_path,
                    "provider": "mlx_direct",
                    "prompt_tokens": TokenCounter.count_tokens(prompt),
                    "response_tokens": response_tokens,
                    "total_tokens": TokenCounter.count_tokens(prompt) + response_tokens,
                    "tokens_per_second": response_tokens / response_time if response_time > 0 else 0
                }
            else:
                return {
                    "error": f"MLX command failed: {result.stderr}",
                    "response_time": end_time - start_time,
                    "model": self.model_path,
                    "provider": "mlx_direct"
                }
        except Exception as e:
            return {
                "error": str(e),
                "response_time": time.time() - start_time,
                "model": self.model_path,
                "provider": "mlx_direct"
            }


class SpeedTestRunner:
    """Main speed test runner."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.mlx_client = MLXClient()
        self.results = []
    
    async def run_simple_test(self, iterations: int = 1) -> Dict[str, Any]:
        """Run simple test with basic prompt."""
        print(f"🧪 Starting simple test with {iterations} iterations")

        # Simple test prompt
        simple_prompt = "Schreibe 100 Wörter über Käse. Erkläre verschiedene Käsesorten, deren Herstellung und warum Käse so beliebt ist."

        results = {
            "test_config": {
                "test_type": "simple",
                "iterations": iterations,
                "prompt_tokens": TokenCounter.count_tokens(simple_prompt)
            },
            "ollama_results": [],
            "mlx_results": [],
            "comparison": {}
        }

        # Test Ollama
        print("\n📊 Testing Ollama (simple prompt)...")
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            result = await self.ollama_client.generate_response("gpt-oss", simple_prompt)
            results["ollama_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
            else:
                print(f"    Error: {result['error']}")

        # Test MLX
        print("\n🔥 Testing MLX-LM (simple prompt)...")
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            result = await self.mlx_client.generate_response(simple_prompt)
            if "error" in result:
                print(f"    Server failed, trying direct method...")
                result = await self.mlx_client.generate_response_direct(simple_prompt)

            results["mlx_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
            else:
                print(f"    Error: {result['error']}")

        # Calculate comparison
        results["comparison"] = self._calculate_comparison(
            results["ollama_results"],
            results["mlx_results"]
        )

        return results

    async def run_context_test(self, content: str, iterations: int = 1) -> Dict[str, Any]:
        """Run context test with large content."""
        print(f"🚀 Starting context test with {iterations} iterations")
        print(f"Content length: ~{TokenCounter.count_tokens(content):,} tokens")

        # Context test prompt - Summary task with ~120k token input
        context_prompt = f"""Please read the following content carefully and provide a comprehensive summary of approximately 1000 words. Focus on the key points, main themes, and important insights.

{content}

Please provide a detailed summary (approximately 1000 words) covering:
1. Main topics and themes discussed
2. Key insights and findings
3. Important technical details and concepts
4. Significant examples and use cases
5. Overall conclusions and implications
6. Future directions or recommendations

Write a thorough, well-structured summary that captures the essence of the content:

Summary:"""

        results = {
            "test_config": {
                "test_type": "context",
                "iterations": iterations,
                "content_tokens": TokenCounter.count_tokens(content),
                "prompt_tokens": TokenCounter.count_tokens(context_prompt)
            },
            "ollama_results": [],
            "mlx_results": [],
            "comparison": {}
        }

        # Test Ollama
        print("\n📊 Testing Ollama (context prompt)...")
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            result = await self.ollama_client.generate_response("gpt-oss", context_prompt)
            results["ollama_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
            else:
                print(f"    Error: {result['error']}")

        # Test MLX
        print("\n🔥 Testing MLX-LM (context prompt)...")
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            result = await self.mlx_client.generate_response(context_prompt)
            if "error" in result:
                print(f"    Server failed, trying direct method...")
                result = await self.mlx_client.generate_response_direct(context_prompt)

            results["mlx_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
            else:
                print(f"    Error: {result['error']}")

        # Calculate comparison
        results["comparison"] = self._calculate_comparison(
            results["ollama_results"],
            results["mlx_results"]
        )

        return results

        results = {
            "test_config": {
                "iterations": iterations,
                "content_tokens": TokenCounter.count_tokens(content),
                "prompt_tokens": TokenCounter.count_tokens(test_prompt),
                "sequential": sequential
            },
            "ollama_results": [],
            "mlx_results": [],
            "comparison": {}
        }

        if sequential:
            # Run tests sequentially to avoid memory conflicts

            # Test Ollama first
            print("\n📊 Testing Ollama (gpt-oss) - Phase 1...")
            for i in range(iterations):
                print(f"  Iteration {i+1}/{iterations}")
                result = await self.ollama_client.generate_response("gpt-oss", test_prompt)
                results["ollama_results"].append(result)
                if "error" not in result:
                    print(f"    Response time: {result['response_time']:.2f}s")
                    print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
                else:
                    print(f"    Error: {result['error']}")

            print("\n⏸️  Ollama tests complete. Preparing for MLX tests...")
            print("💡 Tip: If you're running low on memory, consider stopping Ollama:")
            print("   pkill ollama")

            # Wait a moment for memory cleanup
            import asyncio
            await asyncio.sleep(2)

            # Test MLX
            print("\n🔥 Testing MLX-LM (gpt-oss) - Phase 2...")
            for i in range(iterations):
                print(f"  Iteration {i+1}/{iterations}")
                # Try server first, then fallback to direct
                result = await self.mlx_client.generate_response(test_prompt)
                if "error" in result:
                    print(f"    Server failed, trying direct method...")
                    result = await self.mlx_client.generate_response_direct(test_prompt)

                results["mlx_results"].append(result)
                if "error" not in result:
                    print(f"    Response time: {result['response_time']:.2f}s")
                    print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
                else:
                    print(f"    Error: {result['error']}")

        else:
            # Original parallel approach (for smaller models)
            print("\n📊 Testing Ollama (gpt-oss)...")
            for i in range(iterations):
                print(f"  Iteration {i+1}/{iterations}")
                result = await self.ollama_client.generate_response("gpt-oss", test_prompt)
                results["ollama_results"].append(result)
                if "error" not in result:
                    print(f"    Response time: {result['response_time']:.2f}s")
                else:
                    print(f"    Error: {result['error']}")

            print("\n🔥 Testing MLX-LM (gpt-oss)...")
            for i in range(iterations):
                print(f"  Iteration {i+1}/{iterations}")
                result = await self.mlx_client.generate_response(test_prompt)
                if "error" in result:
                    print(f"    Server failed, trying direct method...")
                    result = await self.mlx_client.generate_response_direct(test_prompt)

                results["mlx_results"].append(result)
                if "error" not in result:
                    print(f"    Response time: {result['response_time']:.2f}s")
                else:
                    print(f"    Error: {result['error']}")

        # Calculate comparison
        results["comparison"] = self._calculate_comparison(
            results["ollama_results"],
            results["mlx_results"]
        )

        return results
    
    def _calculate_comparison(self, ollama_results: List[Dict], mlx_results: List[Dict]) -> Dict[str, Any]:
        """Calculate performance comparison."""
        comparison = {}
        
        # Filter successful results
        ollama_times = [r["response_time"] for r in ollama_results if "error" not in r]
        mlx_times = [r["response_time"] for r in mlx_results if "error" not in r]
        
        if ollama_times:
            comparison["ollama"] = {
                "mean_time": statistics.mean(ollama_times),
                "median_time": statistics.median(ollama_times),
                "min_time": min(ollama_times),
                "max_time": max(ollama_times),
                "std_dev": statistics.stdev(ollama_times) if len(ollama_times) > 1 else 0,
                "success_rate": len(ollama_times) / len(ollama_results)
            }
        
        if mlx_times:
            comparison["mlx"] = {
                "mean_time": statistics.mean(mlx_times),
                "median_time": statistics.median(mlx_times),
                "min_time": min(mlx_times),
                "max_time": max(mlx_times),
                "std_dev": statistics.stdev(mlx_times) if len(mlx_times) > 1 else 0,
                "success_rate": len(mlx_times) / len(mlx_results)
            }
        
        # Calculate relative performance
        if ollama_times and mlx_times:
            ollama_mean = statistics.mean(ollama_times)
            mlx_mean = statistics.mean(mlx_times)
            
            if ollama_mean > 0:
                speedup = ollama_mean / mlx_mean
                comparison["relative_performance"] = {
                    "mlx_speedup": speedup,
                    "mlx_faster": speedup > 1.0,
                    "performance_difference_pct": ((ollama_mean - mlx_mean) / ollama_mean) * 100
                }
        
        return comparison
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted results."""
        print("\n" + "="*60)
        print("🏁 SPEED TEST RESULTS")
        print("="*60)
        
        config = results["test_config"]
        print(f"Content tokens: {config['content_tokens']:,}")
        print(f"Prompt tokens: {config['prompt_tokens']:,}")
        print(f"Iterations: {config['iterations']}")
        
        comparison = results["comparison"]
        
        if "ollama" in comparison:
            ollama = comparison["ollama"]
            print(f"\n📊 Ollama Performance:")
            print(f"  Mean response time: {ollama['mean_time']:.2f}s")
            print(f"  Median response time: {ollama['median_time']:.2f}s")
            print(f"  Min/Max: {ollama['min_time']:.2f}s / {ollama['max_time']:.2f}s")
            print(f"  Success rate: {ollama['success_rate']:.1%}")
        
        if "mlx" in comparison:
            mlx = comparison["mlx"]
            print(f"\n🔥 MLX-LM Performance:")
            print(f"  Mean response time: {mlx['mean_time']:.2f}s")
            print(f"  Median response time: {mlx['median_time']:.2f}s")
            print(f"  Min/Max: {mlx['min_time']:.2f}s / {mlx['max_time']:.2f}s")
            print(f"  Success rate: {mlx['success_rate']:.1%}")
        
        if "relative_performance" in comparison:
            rel = comparison["relative_performance"]
            print(f"\n⚡ Relative Performance:")
            if rel["mlx_faster"]:
                print(f"  MLX is {rel['mlx_speedup']:.2f}x faster than Ollama")
            else:
                print(f"  Ollama is {1/rel['mlx_speedup']:.2f}x faster than MLX")
            print(f"  Performance difference: {rel['performance_difference_pct']:.1f}%")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="128k Token Speed Test")
    parser.add_argument("--iterations", type=int, default=3, help="Number of test iterations")
    parser.add_argument("--source-file", default="archive/simonwilison-llm-latest-30.md",
                       help="Source file for content generation")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel (default: sequential)")
    parser.add_argument("--sequential", action="store_true", help="Run tests sequentially (default, safer for large models)")
    
    args = parser.parse_args()
    
    # Check if source file exists
    source_file = Path(args.source_file)
    if not source_file.exists():
        print(f"❌ Source file not found: {source_file}")
        return 1
    
    # Generate 128k token content
    print("📝 Generating 128k token content...")
    content = TokenCounter.generate_128k_content(str(source_file))
    
    # Determine test mode
    sequential = not args.parallel  # Default to sequential unless --parallel is specified
    if args.sequential:
        sequential = True

    # Run speed test
    runner = SpeedTestRunner()
    results = await runner.run_speed_test(content, args.iterations, sequential=sequential)
    
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
