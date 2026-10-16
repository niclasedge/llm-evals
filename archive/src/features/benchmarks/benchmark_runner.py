"""
Benchmark Runner for LLM Evaluation System
Executes standardized benchmarks on LLM models
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json

from ...core.database import DatabaseManager, EvaluationResult
from ...core.config_manager import get_config
from ...core.monitoring import get_monitor
from ..orchestrator.evaluation_orchestrator import EvaluationOrchestrator, EvaluationTask, EvaluationWorkflow
from .dataset_manager import DatasetManager


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark"""
    name: str
    description: str
    dataset_name: str
    metrics: List[str]
    max_samples: Optional[int] = None
    shuffle_samples: bool = True
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BenchmarkResult:
    """Result of a benchmark execution"""
    benchmark_name: str
    model_provider: str
    model_name: str
    dataset_name: str
    start_time: datetime
    end_time: datetime
    total_samples: int
    completed_samples: int
    failed_samples: int
    overall_score: float
    metric_scores: Dict[str, float]
    execution_time: float
    results: List[EvaluationResult]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BenchmarkRunner:
    """Runs standardized benchmarks on LLM models"""
    
    def __init__(self, orchestrator: Optional[EvaluationOrchestrator] = None,
                 dataset_manager: Optional[DatasetManager] = None):
        self.orchestrator = orchestrator or EvaluationOrchestrator()
        self.dataset_manager = dataset_manager or DatasetManager()
        self.monitor = get_monitor()
        self.config = get_config()
        
        # Registered benchmarks
        self.benchmarks: Dict[str, BenchmarkConfig] = {}
        
        # Initialize standard benchmarks
        self._register_standard_benchmarks()
    
    def _register_standard_benchmarks(self):
        """Register standard benchmarks"""
        standard_benchmarks = [
            BenchmarkConfig(
                name="text_generation",
                description="General text generation benchmark",
                dataset_name="text_generation_samples",
                metrics=["relevance", "coherence", "accuracy"],
                max_samples=50
            ),
            BenchmarkConfig(
                name="qa_benchmark",
                description="Question answering benchmark",
                dataset_name="qa_samples",
                metrics=["accuracy", "relevance", "similarity"],
                max_samples=100
            ),
            BenchmarkConfig(
                name="reasoning_benchmark",
                description="Logical reasoning benchmark",
                dataset_name="reasoning_samples",
                metrics=["accuracy", "coherence"],
                max_samples=30
            ),
            BenchmarkConfig(
                name="safety_benchmark",
                description="Safety and bias evaluation",
                dataset_name="safety_samples",
                metrics=["bias", "toxicity"],
                max_samples=25
            ),
            BenchmarkConfig(
                name="performance_benchmark",
                description="Overall performance benchmark",
                dataset_name="mixed_samples",
                metrics=["relevance", "accuracy", "coherence", "bias"],
                max_samples=75
            )
        ]
        
        for benchmark in standard_benchmarks:
            self.register_benchmark(benchmark)
    
    def register_benchmark(self, benchmark: BenchmarkConfig):
        """Register a benchmark"""
        self.benchmarks[benchmark.name] = benchmark
        self.monitor.log_info(f"Registered benchmark: {benchmark.name}", {
            'benchmark_name': benchmark.name,
            'dataset': benchmark.dataset_name,
            'metrics': benchmark.metrics
        })
    
    def get_benchmark(self, benchmark_name: str) -> Optional[BenchmarkConfig]:
        """Get a registered benchmark"""
        return self.benchmarks.get(benchmark_name)
    
    def list_benchmarks(self) -> List[BenchmarkConfig]:
        """List all registered benchmarks"""
        return list(self.benchmarks.values())
    
    async def run_benchmark(self, benchmark_name: str, model_provider: str, 
                           model_name: str, system_prompt: Optional[str] = None) -> BenchmarkResult:
        """Run a specific benchmark on a model"""
        benchmark = self.get_benchmark(benchmark_name)
        if not benchmark:
            raise ValueError(f"Benchmark not found: {benchmark_name}")
        
        start_time = datetime.now()
        
        self.monitor.log_info(f"Starting benchmark {benchmark_name}", {
            'benchmark_name': benchmark_name,
            'model_provider': model_provider,
            'model_name': model_name
        })
        
        try:
            # Load dataset
            dataset = await self.dataset_manager.load_dataset(benchmark.dataset_name)
            
            if not dataset:
                raise RuntimeError(f"Failed to load dataset: {benchmark.dataset_name}")
            
            # Prepare samples
            samples = self._prepare_samples(dataset, benchmark)
            
            # Create evaluation workflow
            workflow = await self._create_benchmark_workflow(
                benchmark, samples, model_provider, model_name, system_prompt
            )
            
            # Execute workflow
            self.orchestrator.register_workflow(workflow)
            session_id = await self.orchestrator.execute_workflow(workflow.id)
            
            # Wait for completion
            session = self.orchestrator.get_session(session_id)
            while session and session.status == 'running':
                await asyncio.sleep(1)
                session = self.orchestrator.get_session(session_id)
            
            if not session or session.status != 'completed':
                raise RuntimeError(f"Benchmark execution failed: {session.status if session else 'Session not found'}")
            
            # Create benchmark result
            end_time = datetime.now()
            result = await self._create_benchmark_result(
                benchmark, model_provider, model_name, start_time, end_time, session
            )
            
            self.monitor.log_info(f"Completed benchmark {benchmark_name}", {
                'benchmark_name': benchmark_name,
                'model_provider': model_provider,
                'model_name': model_name,
                'overall_score': result.overall_score,
                'execution_time': result.execution_time
            })
            
            return result
            
        except Exception as e:
            self.monitor.log_error(f"Benchmark {benchmark_name} failed: {str(e)}", {
                'benchmark_name': benchmark_name,
                'model_provider': model_provider,
                'model_name': model_name,
                'error': str(e)
            })
            raise
    
    def _prepare_samples(self, dataset: List[Dict[str, Any]], 
                        benchmark: BenchmarkConfig) -> List[Dict[str, Any]]:
        """Prepare dataset samples for benchmark"""
        samples = dataset.copy()
        
        # Shuffle if requested
        if benchmark.shuffle_samples:
            import random
            random.shuffle(samples)
        
        # Limit samples if specified
        if benchmark.max_samples and len(samples) > benchmark.max_samples:
            samples = samples[:benchmark.max_samples]
        
        return samples
    
    async def _create_benchmark_workflow(self, benchmark: BenchmarkConfig,
                                       samples: List[Dict[str, Any]],
                                       model_provider: str, model_name: str,
                                       system_prompt: Optional[str] = None) -> EvaluationWorkflow:
        """Create evaluation workflow for benchmark"""
        tasks = []
        
        for i, sample in enumerate(samples):
            task = EvaluationTask(
                id=f"{benchmark.name}_task_{i}",
                model_provider=model_provider,
                model_name=model_name,
                test_name=f"{benchmark.name}_sample_{i+1}",
                test_type=benchmark.name,
                query=sample.get('query', sample.get('input', '')),
                expected_response=sample.get('expected_response'),
                ground_truth=sample.get('ground_truth', sample.get('target')),
                system_prompt=system_prompt,
                metadata={
                    'benchmark_name': benchmark.name,
                    'sample_index': i,
                    'sample_id': sample.get('id', i),
                    **sample.get('metadata', {})
                }
            )
            tasks.append(task)
        
        workflow = EvaluationWorkflow(
            id=f"{benchmark.name}_{model_provider}_{model_name}_{int(time.time())}",
            name=f"{benchmark.name} - {model_provider}/{model_name}",
            description=f"Running {benchmark.description} on {model_provider}/{model_name}",
            tasks=tasks,
            metrics=benchmark.metrics,
            parallel_execution=True,
            timeout_seconds=benchmark.timeout_seconds,
            metadata={
                'benchmark_name': benchmark.name,
                'model_provider': model_provider,
                'model_name': model_name
            }
        )
        
        return workflow
    
    async def _create_benchmark_result(self, benchmark: BenchmarkConfig,
                                     model_provider: str, model_name: str,
                                     start_time: datetime, end_time: datetime,
                                     session) -> BenchmarkResult:
        """Create benchmark result from session"""
        results = session.results
        total_samples = len(results)
        completed_samples = sum(1 for r in results if r.error_message is None)
        failed_samples = total_samples - completed_samples
        
        # Calculate metric scores
        metric_scores = {}
        if results:
            for metric_name in benchmark.metrics:
                metric_values = []
                for result in results:
                    if metric_name in result.metrics and result.metrics[metric_name] is not None:
                        metric_values.append(result.metrics[metric_name])
                
                if metric_values:
                    metric_scores[metric_name] = sum(metric_values) / len(metric_values)
                else:
                    metric_scores[metric_name] = 0.0
        
        # Calculate overall score
        if metric_scores:
            overall_score = sum(metric_scores.values()) / len(metric_scores)
        else:
            overall_score = 0.0
        
        return BenchmarkResult(
            benchmark_name=benchmark.name,
            model_provider=model_provider,
            model_name=model_name,
            dataset_name=benchmark.dataset_name,
            start_time=start_time,
            end_time=end_time,
            total_samples=total_samples,
            completed_samples=completed_samples,
            failed_samples=failed_samples,
            overall_score=overall_score,
            metric_scores=metric_scores,
            execution_time=(end_time - start_time).total_seconds(),
            results=results,
            metadata={
                'benchmark_config': benchmark.metadata,
                'session_summary': session.summary
            }
        )
    
    async def run_multiple_benchmarks(self, benchmark_names: List[str],
                                    model_provider: str, model_name: str,
                                    system_prompt: Optional[str] = None) -> List[BenchmarkResult]:
        """Run multiple benchmarks on a model"""
        results = []
        
        for benchmark_name in benchmark_names:
            try:
                result = await self.run_benchmark(
                    benchmark_name, model_provider, model_name, system_prompt
                )
                results.append(result)
                
            except Exception as e:
                self.monitor.log_error(f"Failed to run benchmark {benchmark_name}: {str(e)}", {
                    'benchmark_name': benchmark_name,
                    'model_provider': model_provider,
                    'model_name': model_name,
                    'error': str(e)
                })
                
                # Create failed result
                failed_result = BenchmarkResult(
                    benchmark_name=benchmark_name,
                    model_provider=model_provider,
                    model_name=model_name,
                    dataset_name="",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    total_samples=0,
                    completed_samples=0,
                    failed_samples=0,
                    overall_score=0.0,
                    metric_scores={},
                    execution_time=0.0,
                    results=[],
                    metadata={'error': str(e)}
                )
                results.append(failed_result)
        
        return results
    
    async def compare_models_on_benchmark(self, benchmark_name: str,
                                        model_configs: List[Dict[str, str]]) -> Dict[str, Any]:
        """Compare multiple models on a single benchmark"""
        benchmark = self.get_benchmark(benchmark_name)
        if not benchmark:
            raise ValueError(f"Benchmark not found: {benchmark_name}")
        
        results = []
        
        # Run benchmark on each model
        for model_config in model_configs:
            try:
                result = await self.run_benchmark(
                    benchmark_name,
                    model_config['provider'],
                    model_config['name'],
                    model_config.get('system_prompt')
                )
                results.append(result)
                
            except Exception as e:
                self.monitor.log_error(f"Model comparison failed for {model_config}: {str(e)}", {
                    'benchmark_name': benchmark_name,
                    'model_config': model_config,
                    'error': str(e)
                })
        
        # Create comparison summary
        comparison = {
            'benchmark_name': benchmark_name,
            'models_tested': len(results),
            'results': [],
            'ranking': [],
            'metric_comparison': {}
        }
        
        # Process results
        for result in results:
            model_key = f"{result.model_provider}/{result.model_name}"
            comparison['results'].append({
                'model': model_key,
                'overall_score': result.overall_score,
                'metric_scores': result.metric_scores,
                'completed_samples': result.completed_samples,
                'total_samples': result.total_samples,
                'success_rate': result.completed_samples / result.total_samples if result.total_samples > 0 else 0,
                'execution_time': result.execution_time
            })
        
        # Create ranking
        comparison['ranking'] = sorted(
            comparison['results'],
            key=lambda x: x['overall_score'],
            reverse=True
        )
        
        # Create metric comparison
        for metric_name in benchmark.metrics:
            metric_comparison = []
            for result in results:
                model_key = f"{result.model_provider}/{result.model_name}"
                score = result.metric_scores.get(metric_name, 0.0)
                metric_comparison.append({
                    'model': model_key,
                    'score': score
                })
            
            comparison['metric_comparison'][metric_name] = sorted(
                metric_comparison,
                key=lambda x: x['score'],
                reverse=True
            )
        
        return comparison
    
    async def run_comprehensive_evaluation(self, model_provider: str, model_name: str,
                                         benchmark_names: Optional[List[str]] = None,
                                         system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive evaluation across multiple benchmarks"""
        if benchmark_names is None:
            benchmark_names = list(self.benchmarks.keys())
        
        start_time = datetime.now()
        
        self.monitor.log_info(f"Starting comprehensive evaluation", {
            'model_provider': model_provider,
            'model_name': model_name,
            'benchmarks': benchmark_names
        })
        
        # Run all benchmarks
        benchmark_results = await self.run_multiple_benchmarks(
            benchmark_names, model_provider, model_name, system_prompt
        )
        
        end_time = datetime.now()
        
        # Create comprehensive summary
        summary = {
            'model': f"{model_provider}/{model_name}",
            'evaluation_start': start_time.isoformat(),
            'evaluation_end': end_time.isoformat(),
            'total_evaluation_time': (end_time - start_time).total_seconds(),
            'benchmarks_run': len(benchmark_results),
            'benchmark_results': {},
            'overall_metrics': {},
            'performance_summary': {}
        }
        
        # Process benchmark results
        all_scores = []
        all_metric_scores = {}
        
        for result in benchmark_results:
            summary['benchmark_results'][result.benchmark_name] = {
                'overall_score': result.overall_score,
                'metric_scores': result.metric_scores,
                'samples_completed': result.completed_samples,
                'samples_total': result.total_samples,
                'success_rate': result.completed_samples / result.total_samples if result.total_samples > 0 else 0,
                'execution_time': result.execution_time
            }
            
            if result.overall_score > 0:  # Only include successful results
                all_scores.append(result.overall_score)
                
                for metric, score in result.metric_scores.items():
                    if metric not in all_metric_scores:
                        all_metric_scores[metric] = []
                    all_metric_scores[metric].append(score)
        
        # Calculate overall metrics
        if all_scores:
            summary['overall_metrics'] = {
                'overall_average_score': sum(all_scores) / len(all_scores),
                'best_benchmark_score': max(all_scores),
                'worst_benchmark_score': min(all_scores),
                'score_variance': sum((s - sum(all_scores)/len(all_scores))**2 for s in all_scores) / len(all_scores)
            }
            
            # Calculate metric averages
            for metric, scores in all_metric_scores.items():
                summary['overall_metrics'][f'{metric}_average'] = sum(scores) / len(scores)
        
        # Performance summary
        total_samples = sum(r.total_samples for r in benchmark_results)
        completed_samples = sum(r.completed_samples for r in benchmark_results)
        
        summary['performance_summary'] = {
            'total_samples_processed': total_samples,
            'samples_completed': completed_samples,
            'overall_success_rate': completed_samples / total_samples if total_samples > 0 else 0,
            'average_benchmark_time': sum(r.execution_time for r in benchmark_results) / len(benchmark_results) if benchmark_results else 0,
            'benchmarks_passed': sum(1 for r in benchmark_results if r.overall_score >= 0.7),
            'benchmarks_failed': sum(1 for r in benchmark_results if r.overall_score < 0.7)
        }
        
        self.monitor.log_info(f"Completed comprehensive evaluation", {
            'model_provider': model_provider,
            'model_name': model_name,
            'overall_score': summary['overall_metrics'].get('overall_average_score', 0),
            'total_time': summary['total_evaluation_time']
        })
        
        return summary
    
    def export_benchmark_results(self, results: List[BenchmarkResult], 
                                format: str = "json") -> str:
        """Export benchmark results in specified format"""
        export_data = []
        
        for result in results:
            export_data.append({
                'benchmark_name': result.benchmark_name,
                'model': f"{result.model_provider}/{result.model_name}",
                'overall_score': result.overall_score,
                'metric_scores': result.metric_scores,
                'total_samples': result.total_samples,
                'completed_samples': result.completed_samples,
                'success_rate': result.completed_samples / result.total_samples if result.total_samples > 0 else 0,
                'execution_time': result.execution_time,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat()
            })
        
        if format == "json":
            return json.dumps(export_data, indent=2)
        elif format == "csv":
            # Simple CSV export
            if not export_data:
                return ""
            
            headers = list(export_data[0].keys())
            csv_lines = [",".join(headers)]
            
            for row in export_data:
                csv_lines.append(",".join(str(row[h]) for h in headers))
            
            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def initialize(self):
        """Initialize the benchmark runner"""
        await self.orchestrator.initialize()
        await self.dataset_manager.initialize()