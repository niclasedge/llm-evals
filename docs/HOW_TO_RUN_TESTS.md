# 🧪 How to Execute Tests for Models

## Quick Start Commands

### 1. Framework Tests (Simple Validation)
```bash
# Test framework without external dependencies
make test-simple

# Test with local models enabled
ENABLE_LOCAL_MODELS=true python archive/test_simple.py

# Test with all providers
ENABLE_LOCAL_MODELS=true ENABLE_OPENROUTER=true python archive/test_simple.py
```

### 2. Category-Specific Tests
```bash
# Text generation tests
make test-text

# Code generation tests
make test-code

# Reasoning tests
make test-reasoning

# Vision tests
make test-vision

# Tool calling tests
make test-tool-calls
```

### 3. Provider-Specific Tests
```bash
# Local Ollama models only
make test-local

# Offline tests (no API calls)
make test-offline

# Full integration tests
make test-integration
```

## API-Based Test Execution

### 1. Via Web Dashboard
```bash
# Access the dashboard
open http://localhost:7500

# Navigate to test execution page
# Select models and test categories
# Start tests via web interface
```

### 2. Via REST API

#### Start a Test Run
```bash
curl -X POST http://localhost:7500/api/tests/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_category_id": 1,
    "models": ["phi4-reasoning", "deepseek-r1:8b"],
    "test_config": {
      "max_tests": 5,
      "timeout": 60
    }
  }'
```

#### Get Test Results
```bash
# List all test runs
curl http://localhost:7500/api/results/runs

# Get specific run results
curl http://localhost:7500/api/results/runs/{run_id}

# Get detailed test results
curl http://localhost:7500/api/results/runs/{run_id}/results
```

## Test Categories and IDs

| ID | Name | Type | Description |
|----|------|------|-------------|
| 1 | Reasoning | reasoning | Logical reasoning and problem-solving |
| 2 | Coding | code_generation | Programming and code generation |
| 3 | Text Generation | text_generation | Creative writing and text generation |
| 4 | Vision | vision | Image analysis and understanding |

## Available Models for Testing

### 🏠 Local Ollama Models (21 models)
| Model | Size | Best For |
|-------|------|----------|
| `phi4-reasoning:latest` | 10.4GB | Reasoning, Math |
| `deepseek-r1:8b` | 4.9GB | Reasoning, Code |
| `qwen2.5-coder:7b` | 4.4GB | Code Generation |
| `gemma3:27b-it-qat` | 16.8GB | Complex Reasoning |
| `llama3.2-vision:11b` | 7.3GB | Vision Tasks |
| `qwen2.5vl:32b` | 19.7GB | Vision + Text |

### 🌐 OpenRouter Free Models (20+ models)
| Model | Best For |
|-------|----------|
| `meta-llama/llama-3.3-8b-instruct:free` | General Text |
| `microsoft/phi-4-reasoning:free` | Reasoning |
| `deepseek/deepseek-chat-v3.1:free` | General Chat |
| `qwen/qwen3-coder:free` | Code Generation |
| `mistralai/devstral-small-2505:free` | Development |

## Sample Test Scripts

### 1. Test Single Model on Reasoning
```python
import requests

# Start reasoning test
response = requests.post("http://localhost:7500/api/tests/run", json={
    "test_category_id": 1,  # Reasoning
    "models": ["phi4-reasoning"],
    "test_config": {"max_tests": 3, "timeout": 30}
})

run_id = response.json()["run_id"]
print(f"Test started: {run_id}")

# Check results
results = requests.get(f"http://localhost:7500/api/results/runs/{run_id}")
print(results.json())
```

### 2. Compare Multiple Models
```python
models_to_test = [
    "phi4-reasoning",
    "deepseek-r1:8b",
    "gemma3:27b-it-qat",
    "meta-llama/llama-3.3-8b-instruct:free"
]

for category_id in [1, 2, 3]:  # Reasoning, Coding, Text
    response = requests.post("http://localhost:7500/api/tests/run", json={
        "test_category_id": category_id,
        "models": models_to_test,
        "test_config": {"max_tests": 5, "timeout": 60}
    })
    print(f"Started test category {category_id}: {response.json()}")
```

## Environment Configuration

### Required for OpenRouter
```bash
export OPENROUTER_API_KEY="your_key_here"
```

### Enable Local Models
```bash
export ENABLE_LOCAL_MODELS=true
export ENABLE_OLLAMA=true
```

### Full Configuration
```bash
export OPENROUTER_API_KEY="your_key_here"
export ENABLE_LOCAL_MODELS=true
export ENABLE_OLLAMA=true
export ENABLE_OPENROUTER=true
export LOG_LEVEL=INFO
```

## Performance Testing

### Benchmark Tests
```bash
# Quick benchmarks
make test-benchmark-quick

# Full performance tests
make test-benchmark-full

# Memory usage tests
python archive/tests/performance/test_memory_usage.py

# Concurrent performance
python archive/tests/performance/test_concurrent_performance.py
```

## Monitoring Test Progress

### Real-time Logs
```bash
# Follow application logs
tail -f llm_evaluator.log

# Make logs command
make logs

# Real-time log streaming
make logs-tail
```

### Dashboard Monitoring
- **Main Dashboard**: http://localhost:7500/
- **API Documentation**: http://localhost:7500/docs
- **Health Check**: http://localhost:7500/health

## Common Test Commands

```bash
# Complete test suite
make test

# Quick validation
make test-simple

# Local models only
make test-local

# Integration tests
make test-integration

# Performance benchmarks
make test-benchmark

# Clean test environment
make clean && make setup
```

## Tips for Effective Testing

1. **Start Small**: Begin with `make test-simple` to validate setup
2. **Use Local Models**: Test with Ollama models first (faster, no API costs)
3. **Monitor Resources**: Large models require significant RAM/VRAM
4. **Check Logs**: Use `make logs` to troubleshoot issues
5. **API Rate Limits**: Be mindful of OpenRouter rate limits for free models
6. **Parallel Testing**: Run multiple test categories simultaneously

## Troubleshooting

### Common Issues
```bash
# Ollama not running
ollama serve

# Port conflicts
lsof -ti:7500 | xargs kill

# Missing dependencies
make install

# Database issues
rm llm_eval.db && make start
```

### Health Checks
```bash
# Check all services
curl http://localhost:7500/health

# Check Ollama
curl http://localhost:11434/api/tags

# Check OpenRouter connectivity
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models
```