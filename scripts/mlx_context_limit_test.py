#!/usr/bin/env python3
"""
MLX-LM Context Limit Test for gpt-oss-20b
Tests maximum context length capabilities: 75k, 100k, 131k tokens
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
    def generate_content(base_file: str, target_tokens: int) -> str:
        """Generate content with approximately target tokens."""
        with open(base_file, 'r', encoding='utf-8') as f:
            base_content = f.read()
        
        base_tokens = TokenCounter.count_tokens(base_content)
        repetitions = max(1, target_tokens // base_tokens + 1)
        
        content_parts = []
        for i in range(repetitions):
            content_parts.append(f"\n\n--- SECTION {i+1} ---\n\n")
            content_parts.append(base_content)
            
            # Check if we've reached target
            current_content = ''.join(content_parts)
            current_tokens = TokenCounter.count_tokens(current_content)
            if current_tokens >= target_tokens:
                # Trim if we exceeded target significantly
                if current_tokens > target_tokens * 1.05:  # 5% tolerance
                    # Remove the last iteration and trim
                    content_parts = content_parts[:-2]
                    current_content = ''.join(content_parts)
                break
        
        final_content = ''.join(content_parts)
        actual_tokens = TokenCounter.count_tokens(final_content)
        print(f"Generated content with ~{actual_tokens:,} tokens (target: {target_tokens:,})")
        
        return final_content


class MLXClient:
    """MLX-LM client optimized for large context testing."""
    
    def __init__(self, model_path: str = "halley-ai/gpt-oss-20b-MLX-5bit-gs32", server_port: int = 8081):
        self.model_path = model_path
        self.server_url = f"http://localhost:{server_port}"
    
    async def test_health(self) -> bool:
        """Test if MLX server is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.server_url}/health")
                return response.status_code == 200
        except:
            return False
    
    async def generate_response(self, prompt: str, timeout: int = 1800) -> Dict[str, Any]:
        """Generate response using MLX-LM server with extended timeout."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.server_url}/v1/chat/completions",
                    json={
                        "model": self.model_path,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2000,  # Allow longer summaries
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
                    "tokens_per_second": response_tokens / response_time if response_time > 0 else 0,
                    "time_to_first_token": None,  # Could be measured separately
                    "memory_usage": None  # Could be measured with psutil
                }
        except Exception as e:
            return {
                "error": str(e),
                "response_time": time.time() - start_time,
                "model": self.model_path,
                "provider": "mlx"
            }


class ContextLimitTester:
    """Test MLX-LM context limits systematically."""
    
    def __init__(self):
        self.mlx_client = MLXClient()
        self.test_sizes = [75000, 100000, 131000]  # 75k, 100k, 131k (near max)
        
    async def run_context_limit_tests(self, base_file: str, iterations: int = 1) -> Dict[str, Any]:
        """Run systematic context limit tests."""
        print("🎯 MLX-LM Context Limit Testing")
        print("=" * 50)
        print(f"Model: {self.mlx_client.model_path}")
        print(f"Target sizes: {[f'{size//1000}k' for size in self.test_sizes]}")
        print(f"Iterations per size: {iterations}")
        
        # Check MLX server health
        if not await self.mlx_client.test_health():
            print("❌ MLX server is not responding!")
            return {"error": "MLX server not available"}
        
        print("✅ MLX server is healthy")
        
        all_results = {
            "test_config": {
                "model": self.mlx_client.model_path,
                "test_sizes": self.test_sizes,
                "iterations": iterations,
                "timestamp": time.time()
            },
            "results": {},
            "summary": {}
        }
        
        for size in self.test_sizes:
            size_name = f"{size//1000}k"
            print(f"\n🚀 Testing {size_name} tokens")
            print("-" * 30)
            
            # Generate content for this size
            content = TokenCounter.generate_content(base_file, size)
            actual_tokens = TokenCounter.count_tokens(content)
            
            # Create test prompt
            test_prompt = f"""Please analyze the following extensive content and provide a comprehensive summary of approximately 1500 words.

Focus on:
1. Main themes and topics
2. Key insights and findings
3. Technical details and concepts
4. Examples and use cases
5. Conclusions and implications
6. Future directions

Content to analyze:

{content}

Please provide a detailed, well-structured summary:

Summary:"""
            
            prompt_tokens = TokenCounter.count_tokens(test_prompt)
            
            print(f"Content tokens: {actual_tokens:,}")
            print(f"Total prompt tokens: {prompt_tokens:,}")
            
            # Determine timeout based on size
            if size >= 131000:
                timeout = 2400  # 40 minutes for max size
            elif size >= 100000:
                timeout = 1800  # 30 minutes for 100k
            else:
                timeout = 1200  # 20 minutes for 75k
            
            print(f"Timeout: {timeout}s ({timeout//60} minutes)")
            
            size_results = []
            
            for i in range(iterations):
                print(f"\n  Iteration {i+1}/{iterations}")
                
                result = await self.mlx_client.generate_response(test_prompt, timeout=timeout)
                size_results.append(result)
                
                if "error" not in result:
                    print(f"    ✅ Success!")
                    print(f"    Response time: {result['response_time']:.1f}s ({result['response_time']/60:.1f} min)")
                    print(f"    Tokens/sec: {result.get('tokens_per_second', 0):.1f}")
                    print(f"    Response tokens: {result.get('response_tokens', 0):,}")
                    print(f"    Response length: {len(result.get('response', ''))}")
                else:
                    print(f"    ❌ Error: {result['error']}")
                
                # Wait between iterations to let system recover
                if i < iterations - 1:
                    print("    Waiting 30s before next iteration...")
                    await asyncio.sleep(30)
            
            all_results["results"][size_name] = {
                "target_tokens": size,
                "actual_tokens": actual_tokens,
                "prompt_tokens": prompt_tokens,
                "timeout": timeout,
                "iterations": size_results
            }
            
            # Calculate statistics for this size
            successful_results = [r for r in size_results if "error" not in r]
            if successful_results:
                times = [r["response_time"] for r in successful_results]
                throughputs = [r.get("tokens_per_second", 0) for r in successful_results]
                
                all_results["results"][size_name]["statistics"] = {
                    "success_rate": len(successful_results) / len(size_results),
                    "mean_time": statistics.mean(times),
                    "mean_throughput": statistics.mean(throughputs),
                    "min_time": min(times),
                    "max_time": max(times)
                }
                
                print(f"\n  📊 {size_name} Statistics:")
                print(f"    Success rate: {len(successful_results)}/{len(size_results)}")
                print(f"    Mean time: {statistics.mean(times):.1f}s")
                print(f"    Mean throughput: {statistics.mean(throughputs):.1f} tok/s")
            else:
                all_results["results"][size_name]["statistics"] = {
                    "success_rate": 0,
                    "error": "All iterations failed"
                }
                print(f"\n  ❌ {size_name}: All iterations failed")
        
        # Create overall summary
        all_results["summary"] = self._create_summary(all_results["results"])
        
        return all_results

    def _create_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of all test results."""
        summary = {
            "max_successful_size": None,
            "performance_by_size": {},
            "recommendations": []
        }

        successful_sizes = []

        for size_name, size_data in results.items():
            stats = size_data.get("statistics", {})
            if stats.get("success_rate", 0) > 0:
                successful_sizes.append({
                    "size": size_name,
                    "tokens": size_data["actual_tokens"],
                    "success_rate": stats["success_rate"],
                    "mean_time": stats.get("mean_time", 0),
                    "mean_throughput": stats.get("mean_throughput", 0)
                })

                summary["performance_by_size"][size_name] = {
                    "success_rate": f"{stats['success_rate']:.1%}",
                    "avg_time": f"{stats.get('mean_time', 0):.1f}s",
                    "avg_throughput": f"{stats.get('mean_throughput', 0):.1f} tok/s"
                }

        if successful_sizes:
            # Find max successful size
            max_successful = max(successful_sizes, key=lambda x: x["tokens"])
            summary["max_successful_size"] = max_successful["size"]

            # Generate recommendations
            if max_successful["tokens"] >= 131000:
                summary["recommendations"].append("✅ Model can handle maximum context (131k tokens)")
            elif max_successful["tokens"] >= 100000:
                summary["recommendations"].append("⚠️ Model handles 100k+ tokens but may struggle with maximum")
            elif max_successful["tokens"] >= 75000:
                summary["recommendations"].append("⚠️ Model handles 75k+ tokens but has limitations at higher sizes")

            # Performance recommendations
            best_throughput = max(successful_sizes, key=lambda x: x["mean_throughput"])
            if best_throughput["mean_throughput"] > 5:
                summary["recommendations"].append(f"🚀 Best performance at {best_throughput['size']} tokens")
            else:
                summary["recommendations"].append("⚠️ Low throughput - consider smaller context sizes")
        else:
            summary["recommendations"].append("❌ No successful tests - check model configuration")

        return summary

    def print_results(self, results: Dict[str, Any]):
        """Print formatted test results."""
        print("\n" + "="*60)
        print("🏁 MLX-LM CONTEXT LIMIT TEST RESULTS")
        print("="*60)

        config = results["test_config"]
        print(f"Model: {config['model']}")
        print(f"Test sizes: {[f'{size//1000}k' for size in config['test_sizes']]}")
        print(f"Iterations: {config['iterations']}")

        # Print results for each size
        for size_name, size_data in results["results"].items():
            print(f"\n📊 {size_name.upper()} TOKEN TEST")
            print("-" * 40)
            print(f"Target tokens: {size_data['target_tokens']:,}")
            print(f"Actual tokens: {size_data['actual_tokens']:,}")
            print(f"Prompt tokens: {size_data['prompt_tokens']:,}")
            print(f"Timeout: {size_data['timeout']}s")

            stats = size_data.get("statistics", {})
            if "error" not in stats:
                print(f"Success rate: {stats['success_rate']:.1%}")
                if stats['success_rate'] > 0:
                    print(f"Mean time: {stats['mean_time']:.1f}s ({stats['mean_time']/60:.1f} min)")
                    print(f"Mean throughput: {stats['mean_throughput']:.1f} tok/s")
                    print(f"Time range: {stats['min_time']:.1f}s - {stats['max_time']:.1f}s")
            else:
                print(f"❌ {stats['error']}")

        # Print summary
        summary = results["summary"]
        print(f"\n🎯 SUMMARY")
        print("-" * 40)

        if summary.get("max_successful_size"):
            print(f"Maximum successful size: {summary['max_successful_size']}")

        print("\nPerformance by size:")
        for size, perf in summary.get("performance_by_size", {}).items():
            print(f"  {size}: {perf['success_rate']} success, {perf['avg_time']}, {perf['avg_throughput']}")

        print("\nRecommendations:")
        for rec in summary.get("recommendations", []):
            print(f"  {rec}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="MLX-LM Context Limit Test")
    parser.add_argument("--source-file", default="archive/simonwillison-llm-latest-30.md",
                       help="Source file for content generation")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--iterations", type=int, default=1, help="Number of iterations per size")
    parser.add_argument("--sizes", nargs="+", type=int, choices=[75000, 100000, 131000],
                       default=[75000, 100000, 131000], help="Token sizes to test")
    parser.add_argument("--quick", action="store_true", help="Quick test (75k only)")

    args = parser.parse_args()

    # Check if source file exists
    source_file = Path(args.source_file)
    if not source_file.exists():
        print(f"❌ Source file not found: {source_file}")
        return 1

    # Setup test sizes
    tester = ContextLimitTester()
    if args.quick:
        tester.test_sizes = [75000]
    else:
        tester.test_sizes = args.sizes

    print(f"🎯 Testing MLX-LM context limits")
    print(f"Source file: {source_file}")
    print(f"Test sizes: {[f'{size//1000}k' for size in tester.test_sizes]}")

    # Run tests
    results = await tester.run_context_limit_tests(str(source_file), args.iterations)

    # Print results
    if "error" not in results:
        tester.print_results(results)
    else:
        print(f"❌ Test failed: {results['error']}")
        return 1

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
