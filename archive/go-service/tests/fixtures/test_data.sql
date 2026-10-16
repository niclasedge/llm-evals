-- Test data fixtures for database testing

-- Sample evaluation results
INSERT INTO evaluation_results (
    model_provider, model_name, test_name, test_type, query, response,
    expected_response, metrics, score, passed, execution_time, error_message, metadata
) VALUES 
(
    'ollama', 'llama3.2:3b', 'fibonacci_test', 'coding',
    'Write a function to calculate fibonacci numbers',
    'def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)',
    'def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)',
    '{"accuracy": 1.0, "completeness": 1.0}',
    1.0, 1, 1.5, NULL,
    '{"language": "python", "difficulty": "medium"}'
),
(
    'openrouter', 'gemma3:27b', 'sorting_test', 'coding',
    'Implement a quicksort algorithm',
    'def quicksort(arr): ...',
    'def quicksort(arr): ...',
    '{"accuracy": 0.8, "completeness": 0.9}',
    0.85, 1, 2.3, NULL,
    '{"language": "python", "difficulty": "hard"}'
),
(
    'ollama', 'phi4', 'image_description', 'vision',
    'Describe what you see in this image',
    'I see a cat sitting on a windowsill',
    'A cat sitting near a window',
    '{"relevance": 0.9, "detail": 0.7}',
    0.8, 1, 0.8, NULL,
    '{"image_type": "jpeg", "size": "1024x768"}'
),
(
    'openrouter', 'llama3.2:90b', 'logic_puzzle', 'intelligence',
    'Solve this logic puzzle...',
    'The answer is B',
    'The answer is A',
    '{"logical_reasoning": 0.6, "explanation_quality": 0.8}',
    0.7, 0, 3.2, NULL,
    '{"puzzle_type": "syllogism", "difficulty": "medium"}'
),
(
    'ollama', 'mistral-small', 'tool_call_test', 'tools',
    'Calculate the weather for New York',
    'I need to call the weather API for New York',
    NULL,
    '{"tool_usage": 0.9, "accuracy": 0.95}',
    0.925, 1, 1.1, NULL,
    '{"tool": "weather_api", "location": "New York"}'
),
(
    'openrouter', 'qwen2.5-coder', 'error_test', 'coding',
    'Debug this broken code',
    'Error in processing',
    'Fixed code should be...',
    '{}',
    0.0, 0, 0.5, 'API timeout error',
    '{"language": "javascript", "error_type": "timeout"}'
);

-- Sample evaluation sessions
INSERT INTO evaluation_sessions (
    session_id, started_at, completed_at, status, total_tests, completed_tests, metadata
) VALUES 
(
    'session_001', 
    datetime('now', '-2 hours'),
    datetime('now', '-1 hour'),
    'completed',
    10, 10,
    '{"test_suite": "coding_evaluation", "version": "1.0"}'
),
(
    'session_002',
    datetime('now', '-30 minutes'),
    NULL,
    'running',
    15, 8,
    '{"test_suite": "comprehensive", "version": "1.1"}'
),
(
    'session_003',
    datetime('now', '-1 day'),
    datetime('now', '-1 day', '+2 hours'),
    'completed',
    5, 5,
    '{"test_suite": "vision_only", "version": "1.0"}'
);

-- Sample performance metrics
INSERT INTO performance_metrics (
    timestamp, model_name, test_type, avg_execution_time, success_rate, total_requests, metadata
) VALUES 
(
    datetime('now', '-1 hour'),
    'llama3.2:3b',
    'coding',
    1.8, 0.85, 20,
    '{"provider": "ollama", "hardware": "cpu"}'
),
(
    datetime('now', '-1 hour'),
    'gemma3:27b',
    'vision',
    2.5, 0.92, 15,
    '{"provider": "openrouter", "hardware": "gpu"}'
),
(
    datetime('now', '-30 minutes'),
    'phi4',
    'intelligence',
    3.1, 0.78, 12,
    '{"provider": "ollama", "hardware": "cpu"}'
);

-- Sample model performance summary
INSERT INTO model_performance_summary (
    model_provider, model_name, test_type, period_start, period_end,
    total_tests, passed_tests, failed_tests, avg_score, avg_execution_time, success_rate
) VALUES 
(
    'ollama', 'llama3.2:3b', 'coding',
    datetime('now', '-1 day'), datetime('now'),
    25, 20, 5, 0.82, 1.7, 0.8
),
(
    'openrouter', 'gemma3:27b', 'vision',
    datetime('now', '-1 day'), datetime('now'),
    18, 16, 2, 0.88, 2.3, 0.89
),
(
    'ollama', 'phi4', 'intelligence',
    datetime('now', '-1 day'), datetime('now'),
    15, 12, 3, 0.75, 2.9, 0.8
);