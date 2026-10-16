import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .image_service import ImageGenerationService
from .image_prompts import IMAGE_TEST_PROMPTS, get_balanced_prompt_set, get_evaluation_criteria
from .image_results import ImageGenerationResults
from . import config

logger = logging.getLogger(__name__)


class ImageGenerationEvaluator:
    """Main evaluator for image generation models"""
    
    def __init__(self):
        self.service = ImageGenerationService()
        self.results = ImageGenerationResults()
        self.results_dir = Path("image_evaluation_results")
        self.results_dir.mkdir(exist_ok=True)
        
    async def run_evaluation(self, 
                           providers: Optional[List[str]] = None,
                           models: Optional[List[str]] = None,
                           prompts: Optional[List[Dict[str, Any]]] = None,
                           complexity_levels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run image generation evaluation"""
        
        if not config.ENABLE_IMAGE_GENERATION:
            logger.info("Image generation evaluation is disabled in config")
            return {"status": "disabled", "message": "Image generation evaluation is disabled"}
        
        # Get available providers
        if providers is None:
            providers = self.service.get_available_providers()
        
        if not providers:
            logger.warning("No image generation providers available")
            return {"status": "error", "message": "No image generation providers available"}
        
        # Get test prompts
        if prompts is None:
            prompts = get_balanced_prompt_set()
        
        # Filter prompts by complexity if specified
        if complexity_levels:
            prompts = [p for p in prompts if p["complexity"] in complexity_levels]
        
        logger.info(f"Starting image generation evaluation with {len(providers)} providers and {len(prompts)} prompts")
        
        # Create evaluation session
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        evaluation_results = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "config": {
                "providers": providers,
                "models": models,
                "prompts": len(prompts),
                "complexity_levels": complexity_levels
            },
            "results": {},
            "summary": {},
            "errors": []
        }
        
        # Run evaluation for each provider
        for provider in providers:
            logger.info(f"Evaluating provider: {provider}")
            
            provider_models = models or self.service.get_models_for_provider(provider)
            if not provider_models:
                logger.warning(f"No models available for provider: {provider}")
                continue
            
            provider_results = await self._evaluate_provider(provider, provider_models, prompts)
            evaluation_results["results"][provider] = provider_results
        
        # Generate summary
        evaluation_results["summary"] = self._generate_summary(evaluation_results["results"])
        evaluation_results["end_time"] = datetime.now().isoformat()
        
        # Save results
        await self._save_evaluation_results(evaluation_results)
        
        logger.info("Image generation evaluation completed")
        return evaluation_results
    
    async def _evaluate_provider(self, provider: str, models: List[str], prompts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a specific provider with given models and prompts"""
        
        provider_results = {
            "provider": provider,
            "models": {},
            "statistics": {
                "total_generations": 0,
                "successful_generations": 0,
                "failed_generations": 0,
                "total_time": 0.0,
                "average_time": 0.0
            }
        }
        
        for model in models:
            logger.info(f"Evaluating model: {model}")
            model_results = await self._evaluate_model(provider, model, prompts)
            provider_results["models"][model] = model_results
            
            # Update statistics
            stats = provider_results["statistics"]
            model_stats = model_results["statistics"]
            stats["total_generations"] += model_stats["total_generations"]
            stats["successful_generations"] += model_stats["successful_generations"]
            stats["failed_generations"] += model_stats["failed_generations"]
            stats["total_time"] += model_stats["total_time"]
        
        # Calculate averages
        total_gens = provider_results["statistics"]["total_generations"]
        if total_gens > 0:
            provider_results["statistics"]["average_time"] = (
                provider_results["statistics"]["total_time"] / total_gens
            )
        
        return provider_results
    
    async def _evaluate_model(self, provider: str, model: str, prompts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a specific model with given prompts"""
        
        model_results = {
            "provider": provider,
            "model": model,
            "generations": [],
            "statistics": {
                "total_generations": len(prompts),
                "successful_generations": 0,
                "failed_generations": 0,
                "total_time": 0.0,
                "average_time": 0.0
            }
        }
        
        # Process prompts with concurrency control
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests
        
        tasks = []
        for prompt in prompts:
            task = self._generate_with_semaphore(semaphore, provider, model, prompt)
            tasks.append(task)
        
        # Wait for all generations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Generation failed: {result}")
                model_results["generations"].append({
                    "success": False,
                    "error": str(result),
                    "provider": provider,
                    "model": model
                })
                model_results["statistics"]["failed_generations"] += 1
            else:
                model_results["generations"].append(result)
                if result.get("success", False):
                    model_results["statistics"]["successful_generations"] += 1
                    model_results["statistics"]["total_time"] += result.get("generation_time", 0)
                else:
                    model_results["statistics"]["failed_generations"] += 1
        
        # Calculate averages
        successful = model_results["statistics"]["successful_generations"]
        if successful > 0:
            model_results["statistics"]["average_time"] = (
                model_results["statistics"]["total_time"] / successful
            )
        
        return model_results
    
    async def _generate_with_semaphore(self, semaphore: asyncio.Semaphore, 
                                     provider: str, model: str, 
                                     prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image with semaphore control"""
        async with semaphore:
            try:
                result = await self.service.generate_image(
                    provider=provider,
                    model=model,
                    prompt=prompt["prompt"]
                )
                
                # Add prompt metadata to result
                result["prompt_metadata"] = {
                    "category": prompt["category"],
                    "description": prompt["description"],
                    "complexity": prompt["complexity"],
                    "expected_elements": prompt["expected_elements"]
                }
                
                return result
                
            except Exception as e:
                logger.error(f"Error generating image: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "provider": provider,
                    "model": model,
                    "prompt": prompt["prompt"],
                    "prompt_metadata": {
                        "category": prompt["category"],
                        "description": prompt["description"],
                        "complexity": prompt["complexity"],
                        "expected_elements": prompt["expected_elements"]
                    }
                }
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate evaluation summary"""
        
        summary = {
            "total_providers": len(results),
            "total_models": 0,
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "success_rate": 0.0,
            "average_generation_time": 0.0,
            "provider_performance": {},
            "model_performance": {},
            "category_performance": {}
        }
        
        total_time = 0.0
        successful_time_count = 0
        
        for provider, provider_data in results.items():
            provider_stats = provider_data["statistics"]
            
            # Update totals
            summary["total_models"] += len(provider_data["models"])
            summary["total_generations"] += provider_stats["total_generations"]
            summary["successful_generations"] += provider_stats["successful_generations"]
            summary["failed_generations"] += provider_stats["failed_generations"]
            total_time += provider_stats["total_time"]
            
            # Provider performance
            summary["provider_performance"][provider] = {
                "models_tested": len(provider_data["models"]),
                "success_rate": (
                    provider_stats["successful_generations"] / max(provider_stats["total_generations"], 1)
                ),
                "average_time": provider_stats["average_time"]
            }
            
            # Model performance
            for model, model_data in provider_data["models"].items():
                model_stats = model_data["statistics"]
                summary["model_performance"][f"{provider}_{model}"] = {
                    "success_rate": (
                        model_stats["successful_generations"] / max(model_stats["total_generations"], 1)
                    ),
                    "average_time": model_stats["average_time"],
                    "total_generations": model_stats["total_generations"]
                }
                
                # Count successful generations for average time calculation
                if model_stats["successful_generations"] > 0:
                    successful_time_count += model_stats["successful_generations"]
        
        # Calculate overall metrics
        if summary["total_generations"] > 0:
            summary["success_rate"] = (
                summary["successful_generations"] / summary["total_generations"]
            )
        
        if successful_time_count > 0:
            summary["average_generation_time"] = total_time / successful_time_count
        
        return summary
    
    async def _save_evaluation_results(self, results: Dict[str, Any]) -> None:
        """Save evaluation results to files"""
        
        session_id = results["session_id"]
        
        # Save JSON results
        json_path = self.results_dir / f"image_evaluation_{session_id}.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save markdown report
        markdown_path = self.results_dir / f"image_evaluation_report_{session_id}.md"
        markdown_content = self._generate_markdown_report(results)
        with open(markdown_path, "w") as f:
            f.write(markdown_content)
        
        logger.info(f"Results saved to {json_path} and {markdown_path}")
    
    def _generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Generate markdown report from evaluation results"""
        
        summary = results["summary"]
        
        report = f"""# Image Generation Evaluation Report

## Session Information
- **Session ID**: {results['session_id']}
- **Start Time**: {results['start_time']}
- **End Time**: {results['end_time']}

## Summary Statistics
- **Total Providers**: {summary['total_providers']}
- **Total Models**: {summary['total_models']}
- **Total Generations**: {summary['total_generations']}
- **Successful Generations**: {summary['successful_generations']}
- **Failed Generations**: {summary['failed_generations']}
- **Overall Success Rate**: {summary['success_rate']:.2%}
- **Average Generation Time**: {summary['average_generation_time']:.2f} seconds

## Provider Performance
"""
        
        for provider, perf in summary["provider_performance"].items():
            report += f"""
### {provider.title()}
- **Models Tested**: {perf['models_tested']}
- **Success Rate**: {perf['success_rate']:.2%}
- **Average Time**: {perf['average_time']:.2f} seconds
"""
        
        report += "\n## Model Performance\n"
        
        for model, perf in summary["model_performance"].items():
            report += f"""
### {model}
- **Success Rate**: {perf['success_rate']:.2%}
- **Average Time**: {perf['average_time']:.2f} seconds
- **Total Generations**: {perf['total_generations']}
"""
        
        # Add detailed results for each provider
        report += "\n## Detailed Results\n"
        
        for provider, provider_data in results["results"].items():
            report += f"\n### {provider.title()} Results\n"
            
            for model, model_data in provider_data["models"].items():
                report += f"\n#### {model}\n"
                
                successful = [g for g in model_data["generations"] if g.get("success", False)]
                failed = [g for g in model_data["generations"] if not g.get("success", False)]
                
                if successful:
                    report += f"\n**Successful Generations ({len(successful)}):**\n"
                    for gen in successful:
                        prompt_meta = gen.get("prompt_metadata", {})
                        report += f"- {prompt_meta.get('category', 'Unknown')}: {gen.get('prompt', 'N/A')[:50]}...\n"
                
                if failed:
                    report += f"\n**Failed Generations ({len(failed)}):**\n"
                    for gen in failed:
                        prompt_meta = gen.get("prompt_metadata", {})
                        error = gen.get("error", "Unknown error")
                        report += f"- {prompt_meta.get('category', 'Unknown')}: {error}\n"
        
        return report