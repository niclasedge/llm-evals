#!/usr/bin/env python3
"""
Speed Test Script for 120k Token Processing
Compares Ollama vs MLX-LM performance with gpt-oss model
Tests both simple prompts and large context prompts
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
    def generate_content(base_file: str, target_tokens: int = 120_000) -> str:
        """Generate content with approximately target tokens."""
        with open(base_file, 'r', encoding='utf-8') as f:
            base_content = f.read()

        base_tokens = TokenCounter.count_tokens(base_content)
        repetitions = max(1, target_tokens // base_tokens + 1)

        content_parts = []
        for i in range(repetitions):
            content_parts.append(f"\n\n--- ITERATION {i+1} ---\n\n")
            content_parts.append(base_content)

            # Check if we've reached target
            current_content = ''.join(content_parts)
            current_tokens = TokenCounter.count_tokens(current_content)
            if current_tokens >= target_tokens:
                # Trim if we exceeded target
                if current_tokens > target_tokens:
                    # Remove the last iteration and trim
                    content_parts = content_parts[:-2]  # Remove last iteration marker and content
                    current_content = ''.join(content_parts)
                break

        final_content = ''.join(content_parts)
        actual_tokens = TokenCounter.count_tokens(final_content)
        print(f"Generated content with ~{actual_tokens:,} tokens (target: {target_tokens:,})")

        return final_content

    @staticmethod
    def generate_120k_content(base_file: str) -> str:
        """Generate content with approximately 120k tokens (max limit)."""
        return TokenCounter.generate_content(base_file, 120_000)

    @staticmethod
    def generate_50k_content(base_file: str) -> str:
        """Generate content with approximately 50k tokens."""
        return TokenCounter.generate_content(base_file, 50_000)


class OllamaClient:
    """Ollama API client for speed testing."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    async def generate_response(self, model: str, prompt: str, timeout: int = 600) -> Dict[str, Any]:
        """Generate response using Ollama API."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:  # Configurable timeout
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
    
    async def generate_response(self, prompt: str, timeout: int = 600) -> Dict[str, Any]:
        """Generate response using MLX-LM server."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:  # Configurable timeout
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
            result = await self.ollama_client.generate_response("gpt-oss", simple_prompt, timeout=120)  # 2 min for simple
            results["ollama_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
                print(f"    Response: {result['response'][:100]}...")
            else:
                print(f"    Error: {result['error']}")
        
        # Test MLX
        print("\n🔥 Testing MLX-LM (simple prompt)...")
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            result = await self.mlx_client.generate_response(simple_prompt, timeout=120)  # 2 min for simple
            
            results["mlx_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
                print(f"    Response: {result['response'][:100]}...")
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
        content_tokens = TokenCounter.count_tokens(content)
        timeout = 1200 if content_tokens > 100_000 else 600  # 20 min for large context, 10 min for medium
        print(f"    Using timeout: {timeout}s for {content_tokens:,} tokens")

        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            result = await self.ollama_client.generate_response("gpt-oss", context_prompt, timeout=timeout)
            results["ollama_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
                print(f"    Response length: {len(result['response'])} chars")
            else:
                print(f"    Error: {result['error']}")

        # Test MLX
        print("\n🔥 Testing MLX-LM (context prompt)...")
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            result = await self.mlx_client.generate_response(context_prompt, timeout=timeout)

            results["mlx_results"].append(result)
            if "error" not in result:
                print(f"    Response time: {result['response_time']:.2f}s")
                print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
                print(f"    Response length: {len(result['response'])} chars")
            else:
                print(f"    Error: {result['error']}")

        # Calculate comparison
        results["comparison"] = self._calculate_comparison(
            results["ollama_results"],
            results["mlx_results"]
        )

        return results

    async def run_comprehensive_test(self, content: str = None, iterations: int = 1) -> Dict[str, Any]:
        """Run both simple and context tests."""
        print("🎯 Starting comprehensive speed test")
        print("=" * 50)

        all_results = {
            "simple_test": None,
            "context_test": None,
            "summary": {}
        }

        # Run simple test first
        print("\n1️⃣ PHASE 1: Simple Test")
        print("-" * 30)
        simple_results = await self.run_simple_test(iterations)
        all_results["simple_test"] = simple_results

        # Wait between tests
        print("\n⏸️  Waiting 5 seconds between tests...")
        import asyncio
        await asyncio.sleep(5)

        # Run context test if content provided
        if content:
            print("\n2️⃣ PHASE 2: Context Test (120k tokens)")
            print("-" * 30)
            context_results = await self.run_context_test(content, iterations)
            all_results["context_test"] = context_results
        else:
            print("\n⚠️  Skipping context test (no content provided)")

        # Create summary
        all_results["summary"] = self._create_comprehensive_summary(
            all_results["simple_test"],
            all_results["context_test"]
        )

        return all_results

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

    def _create_comprehensive_summary(self, simple_results: Dict, context_results: Dict = None) -> Dict[str, Any]:
        """Create summary of both test phases."""
        summary = {
            "simple_test_summary": {},
            "context_test_summary": {},
            "performance_comparison": {}
        }

        # Simple test summary
        if simple_results and "comparison" in simple_results:
            comp = simple_results["comparison"]
            if "ollama" in comp and "mlx" in comp:
                summary["simple_test_summary"] = {
                    "ollama_time": comp["ollama"]["mean_time"],
                    "mlx_time": comp["mlx"]["mean_time"],
                    "faster_system": "MLX" if comp["mlx"]["mean_time"] < comp["ollama"]["mean_time"] else "Ollama"
                }

        # Context test summary
        if context_results and "comparison" in context_results:
            comp = context_results["comparison"]
            if "ollama" in comp and "mlx" in comp:
                summary["context_test_summary"] = {
                    "ollama_time": comp["ollama"]["mean_time"],
                    "mlx_time": comp["mlx"]["mean_time"],
                    "faster_system": "MLX" if comp["mlx"]["mean_time"] < comp["ollama"]["mean_time"] else "Ollama"
                }

        return summary

    def print_results(self, results: Dict[str, Any]):
        """Print formatted results."""
        print("\n" + "="*60)
        print("🏁 SPEED TEST RESULTS")
        print("="*60)

        if "simple_test" in results and results["simple_test"]:
            self._print_test_results("Simple Test", results["simple_test"])

        if "context_test" in results and results["context_test"]:
            self._print_test_results("Context Test (120k tokens)", results["context_test"])

        if "summary" in results:
            self._print_summary(results["summary"])

    def _print_test_results(self, test_name: str, test_results: Dict[str, Any]):
        """Print results for a specific test."""
        print(f"\n📊 {test_name}")
        print("-" * 40)

        config = test_results["test_config"]
        print(f"Test type: {config['test_type']}")
        print(f"Iterations: {config['iterations']}")
        if "content_tokens" in config:
            print(f"Content tokens: {config['content_tokens']:,}")
        print(f"Prompt tokens: {config['prompt_tokens']:,}")

        comparison = test_results["comparison"]

        if "ollama" in comparison:
            ollama = comparison["ollama"]
            print(f"\n🦙 Ollama Performance:")
            print(f"  Mean response time: {ollama['mean_time']:.2f}s")
            print(f"  Success rate: {ollama['success_rate']:.1%}")

        if "mlx" in comparison:
            mlx = comparison["mlx"]
            print(f"\n🔥 MLX-LM Performance:")
            print(f"  Mean response time: {mlx['mean_time']:.2f}s")
            print(f"  Success rate: {mlx['success_rate']:.1%}")

        if "relative_performance" in comparison:
            rel = comparison["relative_performance"]
            print(f"\n⚡ Relative Performance:")
            if rel["mlx_faster"]:
                print(f"  MLX is {rel['mlx_speedup']:.2f}x faster than Ollama")
            else:
                print(f"  Ollama is {1/rel['mlx_speedup']:.2f}x faster than MLX")

    def _print_summary(self, summary: Dict[str, Any]):
        """Print overall summary."""
        print(f"\n🎯 OVERALL SUMMARY")
        print("-" * 40)

        if summary.get("simple_test_summary"):
            simple = summary["simple_test_summary"]
            print(f"Simple test winner: {simple['faster_system']}")

        if summary.get("context_test_summary"):
            context = summary["context_test_summary"]
            print(f"Context test winner: {context['faster_system']}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="120k Token Speed Test")
    parser.add_argument("--iterations", type=int, default=1, help="Number of test iterations")
    parser.add_argument("--source-file", default="archive/simonwillison-llm-latest-30.md",
                       help="Source file for content generation")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--simple-only", action="store_true", help="Run only simple test")
    parser.add_argument("--context-only", action="store_true", help="Run only context test")
    parser.add_argument("--tokens", type=int, choices=[50000, 120000], default=120000,
                       help="Number of tokens for context test (50k or 120k)")

    args = parser.parse_args()

    # Check if source file exists
    source_file = Path(args.source_file)
    if not source_file.exists() and not args.simple_only:
        print(f"❌ Source file not found: {source_file}")
        return 1

    # Generate content if needed
    content = None
    if not args.simple_only:
        if args.tokens == 50000:
            print("📝 Generating 50k token content...")
            content = TokenCounter.generate_50k_content(str(source_file))
        else:
            print("📝 Generating 120k token content...")
            content = TokenCounter.generate_120k_content(str(source_file))

    # Run speed test
    runner = SpeedTestRunner()

    if args.simple_only:
        results = await runner.run_simple_test(args.iterations)
    elif args.context_only:
        results = await runner.run_context_test(content, args.iterations)
    else:
        results = await runner.run_comprehensive_test(content, args.iterations)

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
