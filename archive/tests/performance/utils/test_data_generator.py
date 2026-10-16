"""
Test data generation utilities for performance benchmarks.
"""

import json
import random
import string
from typing import Dict, List, Any
from pathlib import Path


def create_benchmark_problems(output_file: str, count: int = 10) -> Dict[str, Any]:
    """
    Create standardized benchmark problems for performance testing.
    
    Args:
        output_file: Path to save benchmark problems
        count: Number of problems to generate
    
    Returns:
        Dictionary containing generated problems
    """
    problems = {
        'metadata': {
            'version': '1.0',
            'problem_count': count,
            'categories': ['simple', 'medium', 'complex']
        },
        'problems': []
    }
    
    # Simple problems (quick execution)
    simple_problems = [
        {
            'id': 'simple_1',
            'category': 'simple',
            'title': 'Hello World',
            'description': 'Write a function that returns "Hello, World!"',
            'input_format': 'No input required',
            'output_format': 'String: "Hello, World!"',
            'expected_complexity': 'O(1)',
            'estimated_time_ms': 10
        },
        {
            'id': 'simple_2',
            'category': 'simple',
            'title': 'Add Two Numbers',
            'description': 'Write a function that adds two integers',
            'input_format': 'Two integers a and b',
            'output_format': 'Integer: a + b',
            'expected_complexity': 'O(1)',
            'estimated_time_ms': 15
        },
        {
            'id': 'simple_3',
            'category': 'simple',
            'title': 'String Length',
            'description': 'Write a function that returns the length of a string',
            'input_format': 'String s',
            'output_format': 'Integer: length of s',
            'expected_complexity': 'O(1)',
            'estimated_time_ms': 12
        }
    ]
    
    # Medium problems (moderate execution time)
    medium_problems = [
        {
            'id': 'medium_1',
            'category': 'medium',
            'title': 'Fibonacci Sequence',
            'description': 'Calculate the nth Fibonacci number using recursion',
            'input_format': 'Integer n (0 <= n <= 30)',
            'output_format': 'Integer: nth Fibonacci number',
            'expected_complexity': 'O(2^n)',
            'estimated_time_ms': 500
        },
        {
            'id': 'medium_2',
            'category': 'medium',
            'title': 'Binary Search',
            'description': 'Implement binary search on a sorted array',
            'input_format': 'Sorted array and target value',
            'output_format': 'Integer: index of target or -1',
            'expected_complexity': 'O(log n)',
            'estimated_time_ms': 100
        },
        {
            'id': 'medium_3',
            'category': 'medium',
            'title': 'Palindrome Check',
            'description': 'Check if a string is a palindrome (case-insensitive)',
            'input_format': 'String s',
            'output_format': 'Boolean: true if palindrome',
            'expected_complexity': 'O(n)',
            'estimated_time_ms': 200
        }
    ]
    
    # Complex problems (longer execution time)
    complex_problems = [
        {
            'id': 'complex_1',
            'category': 'complex',
            'title': 'Graph Traversal',
            'description': 'Implement depth-first search on a graph',
            'input_format': 'Graph as adjacency list and start node',
            'output_format': 'List: nodes in DFS order',
            'expected_complexity': 'O(V + E)',
            'estimated_time_ms': 1000
        },
        {
            'id': 'complex_2',
            'category': 'complex',
            'title': 'Dynamic Programming',
            'description': 'Solve 0/1 knapsack problem using dynamic programming',
            'input_format': 'Items with weights/values and capacity',
            'output_format': 'Integer: maximum value',
            'expected_complexity': 'O(nW)',
            'estimated_time_ms': 2000
        },
        {
            'id': 'complex_3',
            'category': 'complex',
            'title': 'Sorting Algorithm',
            'description': 'Implement quicksort algorithm',
            'input_format': 'Array of integers',
            'output_format': 'Array: sorted integers',
            'expected_complexity': 'O(n log n)',
            'estimated_time_ms': 800
        }
    ]
    
    # Combine problems based on requested count
    all_problems = simple_problems + medium_problems + complex_problems
    
    # Select problems to reach desired count
    selected_problems = all_problems[:min(count, len(all_problems))]
    
    # If we need more problems, duplicate with variations
    while len(selected_problems) < count:
        base_problem = random.choice(all_problems)
        variation = base_problem.copy()
        variation['id'] = f"{base_problem['id']}_var_{len(selected_problems)}"
        variation['title'] = f"{base_problem['title']} (Variation)"
        selected_problems.append(variation)
    
    problems['problems'] = selected_problems
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(problems, f, indent=2)
    
    return problems


def generate_load_test_data(scenarios_file: str) -> Dict[str, Any]:
    """
    Generate load testing scenarios and configurations.
    
    Args:
        scenarios_file: Path to save load test scenarios
    
    Returns:
        Dictionary containing load test scenarios
    """
    scenarios = {
        'metadata': {
            'version': '1.0',
            'scenario_count': 6
        },
        'scenarios': [
            {
                'name': 'light_load',
                'description': 'Light concurrent load testing',
                'concurrent_users': 2,
                'duration_minutes': 1,
                'ramp_up_time_seconds': 10,
                'test_categories': ['simple'],
                'expected_avg_response_ms': 100
            },
            {
                'name': 'moderate_load',
                'description': 'Moderate concurrent load testing',
                'concurrent_users': 5,
                'duration_minutes': 2,
                'ramp_up_time_seconds': 30,
                'test_categories': ['simple', 'medium'],
                'expected_avg_response_ms': 300
            },
            {
                'name': 'heavy_load',
                'description': 'Heavy concurrent load testing',
                'concurrent_users': 10,
                'duration_minutes': 3,
                'ramp_up_time_seconds': 60,
                'test_categories': ['simple', 'medium', 'complex'],
                'expected_avg_response_ms': 800
            },
            {
                'name': 'stress_test',
                'description': 'Stress testing to find breaking point',
                'concurrent_users': 20,
                'duration_minutes': 5,
                'ramp_up_time_seconds': 120,
                'test_categories': ['medium', 'complex'],
                'expected_avg_response_ms': 2000
            },
            {
                'name': 'endurance_test',
                'description': 'Long-running endurance testing',
                'concurrent_users': 3,
                'duration_minutes': 10,
                'ramp_up_time_seconds': 30,
                'test_categories': ['simple', 'medium'],
                'expected_avg_response_ms': 200
            },
            {
                'name': 'spike_test',
                'description': 'Sudden load spike testing',
                'concurrent_users': 15,
                'duration_minutes': 1,
                'ramp_up_time_seconds': 5,
                'test_categories': ['simple'],
                'expected_avg_response_ms': 500
            }
        ]
    }
    
    # Save to file
    with open(scenarios_file, 'w') as f:
        json.dump(scenarios, f, indent=2)
    
    return scenarios


def create_synthetic_evaluation_data(output_dir: str, test_count: int = 100) -> Dict[str, Any]:
    """
    Create synthetic evaluation data for testing performance at scale.
    
    Args:
        output_dir: Directory to save synthetic data
        test_count: Number of synthetic test cases to generate
    
    Returns:
        Dictionary containing metadata about generated data
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate different types of synthetic prompts
    prompt_types = {
        'short_text': {
            'min_length': 10,
            'max_length': 50,
            'count': test_count // 4
        },
        'medium_text': {
            'min_length': 100,
            'max_length': 500,
            'count': test_count // 4
        },
        'long_text': {
            'min_length': 1000,
            'max_length': 2000,
            'count': test_count // 4
        },
        'code_prompts': {
            'min_length': 50,
            'max_length': 300,
            'count': test_count // 4
        }
    }
    
    generated_data = {
        'metadata': {
            'total_prompts': test_count,
            'types': list(prompt_types.keys()),
            'generated_files': []
        },
        'statistics': {}
    }
    
    for prompt_type, config in prompt_types.items():
        prompts = []
        
        for i in range(config['count']):
            length = random.randint(config['min_length'], config['max_length'])
            
            if prompt_type == 'code_prompts':
                # Generate code-related prompts
                prompt = f"Write a Python function that {_generate_code_task()} "
                prompt += ''.join(random.choices(string.ascii_letters + ' ', k=length - len(prompt)))
            else:
                # Generate text prompts
                prompt = _generate_text_prompt(length)
            
            prompts.append({
                'id': f"{prompt_type}_{i:04d}",
                'prompt': prompt,
                'length': len(prompt),
                'type': prompt_type
            })
        
        # Save prompts to file
        filename = f"{prompt_type}_prompts.json"
        filepath = output_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(prompts, f, indent=2)
        
        generated_data['metadata']['generated_files'].append(filename)
        generated_data['statistics'][prompt_type] = {
            'count': len(prompts),
            'average_length': sum(p['length'] for p in prompts) / len(prompts),
            'min_length': min(p['length'] for p in prompts),
            'max_length': max(p['length'] for p in prompts)
        }
    
    # Save metadata
    with open(output_path / 'synthetic_data_metadata.json', 'w') as f:
        json.dump(generated_data, f, indent=2)
    
    return generated_data


def _generate_text_prompt(length: int) -> str:
    """Generate random text prompt of specified length."""
    words = [
        'analyze', 'evaluate', 'explain', 'describe', 'compare', 'summarize',
        'classify', 'predict', 'recommend', 'optimize', 'design', 'implement',
        'algorithm', 'performance', 'efficiency', 'scalability', 'reliability',
        'system', 'process', 'method', 'approach', 'strategy', 'solution',
        'data', 'information', 'knowledge', 'insight', 'pattern', 'trend',
        'model', 'framework', 'architecture', 'structure', 'component'
    ]
    
    prompt_words = []
    current_length = 0
    
    while current_length < length:
        word = random.choice(words)
        if current_length + len(word) + 1 <= length:
            prompt_words.append(word)
            current_length += len(word) + 1
        else:
            # Fill remaining space with random characters
            remaining = length - current_length
            if remaining > 0:
                prompt_words.append(''.join(random.choices(string.ascii_lowercase, k=remaining)))
            break
    
    return ' '.join(prompt_words)


def _generate_code_task() -> str:
    """Generate random code task description."""
    tasks = [
        "sorts an array of integers",
        "finds the maximum element in a list",
        "checks if a number is prime",
        "calculates factorial recursively",
        "reverses a string",
        "counts word frequency in text",
        "implements binary search",
        "finds duplicate elements",
        "validates email format",
        "converts temperature units",
        "calculates fibonacci sequence",
        "merges two sorted arrays"
    ]
    
    return random.choice(tasks)


def create_performance_baseline_data(baseline_file: str) -> Dict[str, Any]:
    """
    Create baseline performance expectations for comparison.
    
    Args:
        baseline_file: Path to save baseline data
    
    Returns:
        Dictionary containing baseline performance metrics
    """
    baseline_data = {
        'metadata': {
            'version': '1.0',
            'created_for': 'unified_interface_benchmarking'
        },
        'timing_baselines': {
            'simple_evaluation': {
                'max_execution_time_ms': 1000,
                'target_execution_time_ms': 500,
                'acceptable_variance_pct': 20
            },
            'medium_evaluation': {
                'max_execution_time_ms': 5000,
                'target_execution_time_ms': 2000,
                'acceptable_variance_pct': 30
            },
            'complex_evaluation': {
                'max_execution_time_ms': 15000,
                'target_execution_time_ms': 8000,
                'acceptable_variance_pct': 40
            },
            'api_request': {
                'max_execution_time_ms': 2000,
                'target_execution_time_ms': 800,
                'acceptable_variance_pct': 25
            }
        },
        'memory_baselines': {
            'simple_evaluation': {
                'max_peak_memory_mb': 50,
                'target_peak_memory_mb': 25,
                'memory_leak_threshold_mb': 5
            },
            'medium_evaluation': {
                'max_peak_memory_mb': 100,
                'target_peak_memory_mb': 60,
                'memory_leak_threshold_mb': 10
            },
            'complex_evaluation': {
                'max_peak_memory_mb': 200,
                'target_peak_memory_mb': 120,
                'memory_leak_threshold_mb': 15
            }
        },
        'concurrent_baselines': {
            'light_load': {
                'max_concurrent_users': 5,
                'max_response_time_ms': 2000,
                'min_throughput_requests_per_second': 2
            },
            'moderate_load': {
                'max_concurrent_users': 10,
                'max_response_time_ms': 5000,
                'min_throughput_requests_per_second': 1
            },
            'heavy_load': {
                'max_concurrent_users': 20,
                'max_response_time_ms': 10000,
                'min_throughput_requests_per_second': 0.5
            }
        }
    }
    
    # Save baseline data
    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    return baseline_data