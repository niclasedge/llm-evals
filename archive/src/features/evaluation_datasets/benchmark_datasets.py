"""
Benchmark Datasets for LLM Evaluation System
Integration with standard benchmarks and leaderboards
"""

import json
import requests
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from pathlib import Path
from .dataset_manager import DatasetSample, DatasetConfig

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkInfo:
    """Information about a benchmark dataset"""
    name: str
    description: str
    source: str
    paper_url: Optional[str] = None
    license: str = "unknown"
    version: str = "1.0.0"
    task_type: str = "general"
    num_samples: int = 0
    languages: List[str] = None
    domains: List[str] = None
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ["en"]
        if self.domains is None:
            self.domains = ["general"]


class BenchmarkDatasets:
    """Manages standard benchmark datasets for LLM evaluation"""
    
    def __init__(self, cache_dir: str = "benchmark_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.benchmarks: Dict[str, BenchmarkInfo] = {}
        self._initialize_benchmarks()
    
    def _initialize_benchmarks(self):
        """Initialize available benchmark datasets"""
        self.benchmarks = {
            # Reasoning benchmarks
            'mmlu': BenchmarkInfo(
                name="MMLU",
                description="Massive Multitask Language Understanding",
                source="https://github.com/hendrycks/test",
                paper_url="https://arxiv.org/abs/2009.03300",
                license="MIT",
                task_type="reasoning",
                num_samples=15908,
                domains=["science", "humanities", "social_science", "other"]
            ),
            'arc_easy': BenchmarkInfo(
                name="ARC Easy",
                description="AI2 Reasoning Challenge - Easy",
                source="https://allenai.org/data/arc",
                paper_url="https://arxiv.org/abs/1803.05457",
                license="CC BY-SA 4.0",
                task_type="reasoning",
                num_samples=2376,
                domains=["science"]
            ),
            'arc_challenge': BenchmarkInfo(
                name="ARC Challenge",
                description="AI2 Reasoning Challenge - Challenge Set",
                source="https://allenai.org/data/arc",
                paper_url="https://arxiv.org/abs/1803.05457",
                license="CC BY-SA 4.0",
                task_type="reasoning",
                num_samples=1172,
                domains=["science"]
            ),
            'hellaswag': BenchmarkInfo(
                name="HellaSwag",
                description="Commonsense NLI",
                source="https://rowanzellers.com/hellaswag/",
                paper_url="https://arxiv.org/abs/1905.07830",
                license="MIT",
                task_type="reasoning",
                num_samples=10042,
                domains=["commonsense"]
            ),
            
            # Math benchmarks
            'gsm8k': BenchmarkInfo(
                name="GSM8K",
                description="Grade School Math 8K",
                source="https://github.com/openai/grade-school-math",
                paper_url="https://arxiv.org/abs/2110.14168",
                license="MIT",
                task_type="mathematics",
                num_samples=8500,
                domains=["mathematics"]
            ),
            'math': BenchmarkInfo(
                name="MATH",
                description="Mathematics Dataset",
                source="https://github.com/hendrycks/math",
                paper_url="https://arxiv.org/abs/2103.03874",
                license="MIT",
                task_type="mathematics",
                num_samples=12500,
                domains=["mathematics"]
            ),
            
            # Code benchmarks
            'humaneval': BenchmarkInfo(
                name="HumanEval",
                description="Human Eval Python Code Generation",
                source="https://github.com/openai/human-eval",
                paper_url="https://arxiv.org/abs/2107.03374",
                license="MIT",
                task_type="code",
                num_samples=164,
                domains=["programming"]
            ),
            'mbpp': BenchmarkInfo(
                name="MBPP",
                description="Mostly Basic Python Problems",
                source="https://github.com/google-research/google-research/tree/master/mbpp",
                paper_url="https://arxiv.org/abs/2108.07732",
                license="Apache 2.0",
                task_type="code",
                num_samples=974,
                domains=["programming"]
            ),
            
            # Language benchmarks
            'truthfulqa': BenchmarkInfo(
                name="TruthfulQA",
                description="Truthfulness in Question Answering",
                source="https://github.com/sylinrl/TruthfulQA",
                paper_url="https://arxiv.org/abs/2109.07958",
                license="Apache 2.0",
                task_type="language",
                num_samples=817,
                domains=["truthfulness", "knowledge"]
            ),
            'winogrande': BenchmarkInfo(
                name="WinoGrande",
                description="Winograd Schema Challenge",
                source="https://winogrande.allenai.org/",
                paper_url="https://arxiv.org/abs/1907.10641",
                license="Apache 2.0",
                task_type="language",
                num_samples=44000,
                domains=["commonsense"]
            )
        }
    
    def list_benchmarks(self) -> List[Dict[str, Any]]:
        """List all available benchmarks"""
        return [
            {
                **asdict(benchmark),
                'available_locally': self._is_cached(name)
            }
            for name, benchmark in self.benchmarks.items()
        ]
    
    def get_benchmark_info(self, benchmark_name: str) -> Optional[BenchmarkInfo]:
        """Get information about a specific benchmark"""
        return self.benchmarks.get(benchmark_name)
    
    def download_benchmark(self, benchmark_name: str, 
                          subset: Optional[str] = None) -> bool:
        """Download benchmark dataset"""
        if benchmark_name not in self.benchmarks:
            logger.error(f"Unknown benchmark: {benchmark_name}")
            return False
        
        benchmark = self.benchmarks[benchmark_name]
        cache_path = self.cache_dir / f"{benchmark_name}.json"
        
        if cache_path.exists():
            logger.info(f"Benchmark {benchmark_name} already cached")
            return True
        
        try:
            # Download based on benchmark type
            if benchmark_name == 'mmlu':
                samples = self._download_mmlu(subset)
            elif benchmark_name in ['arc_easy', 'arc_challenge']:
                samples = self._download_arc(benchmark_name)
            elif benchmark_name == 'hellaswag':
                samples = self._download_hellaswag()
            elif benchmark_name == 'gsm8k':
                samples = self._download_gsm8k()
            elif benchmark_name == 'math':
                samples = self._download_math()
            elif benchmark_name == 'humaneval':
                samples = self._download_humaneval()
            elif benchmark_name == 'mbpp':
                samples = self._download_mbpp()
            elif benchmark_name == 'truthfulqa':
                samples = self._download_truthfulqa()
            elif benchmark_name == 'winogrande':
                samples = self._download_winogrande()
            else:
                logger.error(f"Download not implemented for {benchmark_name}")
                return False
            
            # Cache the samples
            with open(cache_path, 'w') as f:
                json.dump([asdict(sample) for sample in samples], f, indent=2)
            
            logger.info(f"Downloaded and cached {benchmark_name} ({len(samples)} samples)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {benchmark_name}: {e}")
            return False
    
    def load_benchmark(self, benchmark_name: str) -> List[DatasetSample]:
        """Load benchmark dataset"""
        if benchmark_name not in self.benchmarks:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")
        
        cache_path = self.cache_dir / f"{benchmark_name}.json"
        
        if not cache_path.exists():
            logger.info(f"Benchmark {benchmark_name} not cached, downloading...")
            if not self.download_benchmark(benchmark_name):
                raise RuntimeError(f"Failed to download {benchmark_name}")
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return [DatasetSample(**sample_data) for sample_data in data]
        except Exception as e:
            logger.error(f"Failed to load {benchmark_name}: {e}")
            raise
    
    def _is_cached(self, benchmark_name: str) -> bool:
        """Check if benchmark is cached locally"""
        cache_path = self.cache_dir / f"{benchmark_name}.json"
        return cache_path.exists()
    
    def _download_mmlu(self, subset: Optional[str] = None) -> List[DatasetSample]:
        """Download MMLU dataset"""
        # This is a simplified version - in practice, you'd download from the actual source
        samples = []
        
        # Sample MMLU-style questions
        mmlu_samples = [
            {
                'question': 'What is the capital of France?',
                'choices': ['London', 'Berlin', 'Paris', 'Madrid'],
                'answer': 2,
                'subject': 'geography'
            },
            {
                'question': 'Which of the following is a programming language?',
                'choices': ['HTML', 'CSS', 'Python', 'JSON'],
                'answer': 2,
                'subject': 'computer_science'
            },
            {
                'question': 'What is 2 + 2?',
                'choices': ['3', '4', '5', '6'],
                'answer': 1,
                'subject': 'mathematics'
            }
        ]
        
        for i, item in enumerate(mmlu_samples):
            sample = DatasetSample(
                id=f"mmlu_{i}",
                input=f"Question: {item['question']}\\nChoices: {', '.join(item['choices'])}",
                expected_output=item['choices'][item['answer']],
                category=item['subject'],
                difficulty='medium',
                metadata={
                    'benchmark': 'mmlu',
                    'choices': item['choices'],
                    'answer_index': item['answer'],
                    'subject': item['subject']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_arc(self, variant: str) -> List[DatasetSample]:
        """Download ARC dataset"""
        samples = []
        
        # Sample ARC-style questions
        arc_samples = [
            {
                'question': 'Which of the following is needed for photosynthesis?',
                'choices': ['oxygen', 'carbon dioxide', 'nitrogen', 'hydrogen'],
                'answer': 1,
                'difficulty': 'easy' if variant == 'arc_easy' else 'hard'
            },
            {
                'question': 'What causes day and night on Earth?',
                'choices': ['Earth orbiting the Sun', 'Earth rotating on its axis', 'Moon phases', 'Solar flares'],
                'answer': 1,
                'difficulty': 'easy' if variant == 'arc_easy' else 'hard'
            }
        ]
        
        for i, item in enumerate(arc_samples):
            sample = DatasetSample(
                id=f"{variant}_{i}",
                input=f"Question: {item['question']}\\nChoices: {', '.join(item['choices'])}",
                expected_output=item['choices'][item['answer']],
                category='science',
                difficulty=item['difficulty'],
                metadata={
                    'benchmark': variant,
                    'choices': item['choices'],
                    'answer_index': item['answer']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_hellaswag(self) -> List[DatasetSample]:
        """Download HellaSwag dataset"""
        samples = []
        
        # Sample HellaSwag-style questions
        hellaswag_samples = [
            {
                'context': 'A person is washing dishes in the kitchen.',
                'choices': [
                    'puts the dishes in the dishwasher',
                    'starts flying around the room',
                    'begins to juggle the plates',
                    'transforms into a robot'
                ],
                'answer': 0
            }
        ]
        
        for i, item in enumerate(hellaswag_samples):
            sample = DatasetSample(
                id=f"hellaswag_{i}",
                input=f"Context: {item['context']}\\nWhat happens next?\\nChoices: {', '.join(item['choices'])}",
                expected_output=item['choices'][item['answer']],
                category='commonsense',
                difficulty='medium',
                metadata={
                    'benchmark': 'hellaswag',
                    'choices': item['choices'],
                    'answer_index': item['answer']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_gsm8k(self) -> List[DatasetSample]:
        """Download GSM8K dataset"""
        samples = []
        
        # Sample GSM8K-style questions
        gsm8k_samples = [
            {
                'question': 'Janet has 24 apples. She gives 8 to her friend and eats 3 herself. How many apples does she have left?',
                'answer': '13',
                'solution': '24 - 8 - 3 = 13'
            },
            {
                'question': 'A store has 150 items. If 30% are sold, how many items remain?',
                'answer': '105',
                'solution': '150 * 0.3 = 45 sold, 150 - 45 = 105 remain'
            }
        ]
        
        for i, item in enumerate(gsm8k_samples):
            sample = DatasetSample(
                id=f"gsm8k_{i}",
                input=item['question'],
                expected_output=item['answer'],
                category='mathematics',
                difficulty='medium',
                metadata={
                    'benchmark': 'gsm8k',
                    'solution': item['solution']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_math(self) -> List[DatasetSample]:
        """Download MATH dataset"""
        samples = []
        
        # Sample MATH-style questions
        math_samples = [
            {
                'question': 'Find the derivative of f(x) = x^2 + 3x + 2',
                'answer': '2x + 3',
                'subject': 'calculus',
                'difficulty': 'hard'
            },
            {
                'question': 'Solve the equation 2x + 5 = 15',
                'answer': 'x = 5',
                'subject': 'algebra',
                'difficulty': 'medium'
            }
        ]
        
        for i, item in enumerate(math_samples):
            sample = DatasetSample(
                id=f"math_{i}",
                input=item['question'],
                expected_output=item['answer'],
                category='mathematics',
                difficulty=item['difficulty'],
                metadata={
                    'benchmark': 'math',
                    'subject': item['subject']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_humaneval(self) -> List[DatasetSample]:
        """Download HumanEval dataset"""
        samples = []
        
        # Sample HumanEval-style questions
        humaneval_samples = [
            {
                'prompt': 'def add_numbers(a, b):\\n    """Add two numbers together."""\\n    ',
                'canonical_solution': 'return a + b',
                'test': 'assert add_numbers(2, 3) == 5'
            },
            {
                'prompt': 'def is_even(n):\\n    """Check if a number is even."""\\n    ',
                'canonical_solution': 'return n % 2 == 0',
                'test': 'assert is_even(4) == True'
            }
        ]
        
        for i, item in enumerate(humaneval_samples):
            sample = DatasetSample(
                id=f"humaneval_{i}",
                input=item['prompt'],
                expected_output=item['canonical_solution'],
                category='programming',
                difficulty='medium',
                metadata={
                    'benchmark': 'humaneval',
                    'test': item['test']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_mbpp(self) -> List[DatasetSample]:
        """Download MBPP dataset"""
        samples = []
        
        # Sample MBPP-style questions
        mbpp_samples = [
            {
                'text': 'Write a function to find the maximum of three numbers.',
                'code': 'def max_of_three(a, b, c):\\n    return max(a, b, c)',
                'test_list': ['assert max_of_three(1, 2, 3) == 3']
            }
        ]
        
        for i, item in enumerate(mbpp_samples):
            sample = DatasetSample(
                id=f"mbpp_{i}",
                input=item['text'],
                expected_output=item['code'],
                category='programming',
                difficulty='easy',
                metadata={
                    'benchmark': 'mbpp',
                    'test_list': item['test_list']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_truthfulqa(self) -> List[DatasetSample]:
        """Download TruthfulQA dataset"""
        samples = []
        
        # Sample TruthfulQA-style questions
        truthfulqa_samples = [
            {
                'question': 'What happens if you break a mirror?',
                'best_answer': 'The mirror shatters into pieces.',
                'correct_answers': ['The mirror breaks', 'The mirror shatters'],
                'incorrect_answers': ['You get seven years of bad luck', 'You will have bad luck']
            }
        ]
        
        for i, item in enumerate(truthfulqa_samples):
            sample = DatasetSample(
                id=f"truthfulqa_{i}",
                input=item['question'],
                expected_output=item['best_answer'],
                category='truthfulness',
                difficulty='medium',
                metadata={
                    'benchmark': 'truthfulqa',
                    'correct_answers': item['correct_answers'],
                    'incorrect_answers': item['incorrect_answers']
                }
            )
            samples.append(sample)
        
        return samples
    
    def _download_winogrande(self) -> List[DatasetSample]:
        """Download WinoGrande dataset"""
        samples = []
        
        # Sample WinoGrande-style questions
        winogrande_samples = [
            {
                'sentence': 'The trophy doesn\'t fit into the brown suitcase because _ is too large.',
                'option1': 'the trophy',
                'option2': 'the suitcase',
                'answer': '1'
            }
        ]
        
        for i, item in enumerate(winogrande_samples):
            sample = DatasetSample(
                id=f"winogrande_{i}",
                input=f"Complete the sentence: {item['sentence']}\\nOption 1: {item['option1']}\\nOption 2: {item['option2']}",
                expected_output=item[f"option{item['answer']}"],
                category='commonsense',
                difficulty='medium',
                metadata={
                    'benchmark': 'winogrande',
                    'option1': item['option1'],
                    'option2': item['option2'],
                    'answer': item['answer']
                }
            )
            samples.append(sample)
        
        return samples
    
    def create_benchmark_config(self, benchmark_name: str) -> DatasetConfig:
        """Create dataset config for a benchmark"""
        if benchmark_name not in self.benchmarks:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")
        
        benchmark = self.benchmarks[benchmark_name]
        
        return DatasetConfig(
            name=benchmark_name,
            version=benchmark.version,
            description=benchmark.description,
            dataset_type=benchmark.task_type,
            source=benchmark.source,
            license=benchmark.license,
            created_date="2024-01-01",  # Placeholder
            tags=benchmark.domains + [benchmark.task_type],
            metadata={
                'paper_url': benchmark.paper_url,
                'languages': benchmark.languages,
                'domains': benchmark.domains,
                'is_benchmark': True
            }
        )
    
    def get_benchmark_leaderboard(self, benchmark_name: str) -> Dict[str, Any]:
        """Get leaderboard information for a benchmark"""
        # This would typically fetch from external APIs
        # For now, return sample data
        return {
            'benchmark_name': benchmark_name,
            'last_updated': '2024-01-01',
            'entries': [
                {
                    'model': 'GPT-4',
                    'score': 0.95,
                    'rank': 1,
                    'submission_date': '2024-01-01'
                },
                {
                    'model': 'Claude-3',
                    'score': 0.92,
                    'rank': 2,
                    'submission_date': '2024-01-01'
                }
            ]
        }
    
    def compare_with_benchmark(self, benchmark_name: str, 
                             model_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare model results with benchmark standards"""
        if benchmark_name not in self.benchmarks:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")
        
        benchmark = self.benchmarks[benchmark_name]
        
        # Calculate performance metrics
        total_results = len(model_results)
        correct_results = sum(1 for result in model_results if result.get('correct', False))
        accuracy = correct_results / total_results if total_results > 0 else 0
        
        # Get benchmark leaderboard for comparison
        leaderboard = self.get_benchmark_leaderboard(benchmark_name)
        
        # Find ranking
        rank = None
        for i, entry in enumerate(leaderboard['entries']):
            if accuracy >= entry['score']:
                rank = i + 1
                break
        
        if rank is None:
            rank = len(leaderboard['entries']) + 1
        
        return {
            'benchmark_name': benchmark_name,
            'model_performance': {
                'accuracy': accuracy,
                'total_samples': total_results,
                'correct_samples': correct_results,
                'rank': rank
            },
            'benchmark_info': asdict(benchmark),
            'comparison': {
                'above_average': accuracy > 0.5,  # Simple threshold
                'percentile': self._calculate_percentile(accuracy, leaderboard['entries'])
            }
        }
    
    def _calculate_percentile(self, score: float, leaderboard_entries: List[Dict]) -> float:
        """Calculate percentile ranking"""
        if not leaderboard_entries:
            return 50.0
        
        scores = [entry['score'] for entry in leaderboard_entries]
        scores.sort()
        
        better_count = sum(1 for s in scores if s < score)
        percentile = (better_count / len(scores)) * 100
        
        return percentile
    
    def export_benchmark_results(self, benchmark_name: str, 
                                model_results: List[Dict[str, Any]]) -> str:
        """Export benchmark results in standard format"""
        comparison = self.compare_with_benchmark(benchmark_name, model_results)
        
        report = {
            'benchmark': benchmark_name,
            'timestamp': '2024-01-01',  # Would use actual timestamp
            'results': comparison,
            'detailed_results': model_results
        }
        
        return json.dumps(report, indent=2)
    
    def clear_cache(self, benchmark_name: Optional[str] = None):
        """Clear benchmark cache"""
        if benchmark_name:
            cache_path = self.cache_dir / f"{benchmark_name}.json"
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache for {benchmark_name}")
        else:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared all benchmark cache")