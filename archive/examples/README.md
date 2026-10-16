# Examples

This directory contains working examples and scripts for all evaluation types in the LLM Evaluation Framework. Each example is designed to be self-contained and demonstrate specific features.

## Quick Start Examples

### 1. Basic CLI Usage
```bash
# Run these from the project root directory

# Basic coding evaluation
./examples/01_basic_coding_evaluation.sh

# Vision evaluation
./examples/02_basic_vision_evaluation.sh

# Tool call evaluation  
./examples/03_basic_tool_evaluation.sh

# Intelligence evaluation
./examples/04_basic_intelligence_evaluation.sh

# Comprehensive evaluation
./examples/05_comprehensive_evaluation.sh
```

### 2. Python API Examples
```bash
# Run coding evaluation via Python API
python examples/python/coding_evaluation_api.py

# Run unified evaluation via Python API
python examples/python/unified_evaluation_api.py

# Compare multiple models
python examples/python/model_comparison.py
```

### 3. Configuration Examples
```bash
# Custom model configuration
cp examples/configs/custom_model_config.yaml configs/

# Environment setup examples
source examples/configs/setup_environment.sh
```

## Directory Structure

```
examples/
├── README.md                          # This file
├── 01_basic_coding_evaluation.sh      # Basic coding evaluation
├── 02_basic_vision_evaluation.sh      # Basic vision evaluation  
├── 03_basic_tool_evaluation.sh        # Basic tool evaluation
├── 04_basic_intelligence_evaluation.sh # Basic intelligence evaluation
├── 05_comprehensive_evaluation.sh     # All evaluation types
├── configs/                           # Configuration examples
│   ├── custom_model_config.yaml       # Custom model configuration
│   ├── setup_environment.sh           # Environment setup
│   └── ollama_models.sh               # Ollama model setup
├── python/                            # Python API examples
│   ├── coding_evaluation_api.py       # Coding evaluation API
│   ├── unified_evaluation_api.py      # Unified evaluation API
│   ├── model_comparison.py            # Model comparison
│   ├── batch_evaluation.py            # Batch evaluation script
│   └── custom_problem_generator.py    # Custom problem generation
├── web_interface/                     # Web interface examples
│   ├── custom_ui_integration.html     # Custom UI integration
│   └── api_client_example.js          # JavaScript API client
└── automation/                       # Automation scripts
    ├── ci_evaluation_pipeline.sh      # CI/CD pipeline integration
    ├── model_benchmark_runner.py      # Automated benchmarking
    └── report_generator.py            # Automated report generation
```

## Prerequisites

Before running the examples:

1. **Install the framework:**
   ```bash
   make install
   ```

2. **Setup environment (optional):**
   ```bash
   # For OpenRouter API access
   export OPENROUTER_API_KEY="your-api-key"
   
   # For local Ollama models
   export ENABLE_LOCAL_MODELS=true
   ```

3. **Verify setup:**
   ```bash
   ./llm-eval models
   ./llm-eval test-model llama3
   ```

## Running Examples

### Shell Script Examples

All shell scripts can be run directly:

```bash
# Make scripts executable
chmod +x examples/*.sh

# Run basic coding evaluation
./examples/01_basic_coding_evaluation.sh

# Run with custom parameters
./examples/01_basic_coding_evaluation.sh --model phi4 --problems fibonacci,sorting
```

### Python Examples

Python examples require the framework to be installed:

```bash
# Install dependencies
pip install -r requirements.txt

# Run Python examples
python examples/python/coding_evaluation_api.py
python examples/python/model_comparison.py
```

### Web Interface Examples

Web examples require the server to be running:

```bash
# Start the server
python -m src.features.coding_evaluation.main server

# Open web examples in browser
open examples/web_interface/custom_ui_integration.html
```

## Customization

### Modifying Examples

Each example includes comments explaining how to customize:

```bash
# Edit model selection
MODEL_NAME="your-preferred-model"

# Edit evaluation parameters
PROBLEMS="fibonacci,sorting,palindrome"
LANGUAGES="python,javascript"

# Edit output format
OUTPUT_FORMAT="json"
OUTPUT_FILE="my_results.json"
```

### Creating New Examples

1. **Copy existing example:**
   ```bash
   cp examples/01_basic_coding_evaluation.sh examples/my_custom_evaluation.sh
   ```

2. **Modify parameters:**
   ```bash
   # Edit the script to use your preferred settings
   ```

3. **Test the example:**
   ```bash
   ./examples/my_custom_evaluation.sh
   ```

## Common Use Cases

### Research Evaluation
```bash
# Compare multiple models on coding tasks
./examples/05_comprehensive_evaluation.sh --free-only --output research_results.json

# Generate detailed comparison report
python examples/python/model_comparison.py --models llama3,phi4,gemma3 --format markdown
```

### Development Testing
```bash
# Quick coding test during development
./examples/01_basic_coding_evaluation.sh --model llama3 --problems fibonacci

# Test new model integration
./llm-eval test-model new-model-name
```

### Production Validation
```bash
# Comprehensive model validation
./examples/05_comprehensive_evaluation.sh --model production-model --timeout 600

# Generate production readiness report
python examples/automation/model_benchmark_runner.py --model production-model
```

### CI/CD Integration
```bash
# Run in CI pipeline
./examples/automation/ci_evaluation_pipeline.sh

# Generate reports for deployment
python examples/automation/report_generator.py --format html
```

## Example Outputs

### Console Output
```
Running coding evaluation with model: llama3
Models: ['llama3']
Problems: ['fibonacci', 'sorting']
Languages: ['python', 'javascript']

✅ fibonacci (python): Score 95.0 (4/4 tests passed)
✅ fibonacci (javascript): Score 90.0 (4/4 tests passed)  
✅ sorting (python): Score 100.0 (3/3 tests passed)
✅ sorting (javascript): Score 85.0 (3/3 tests passed)

Summary:
- Average Score: 92.5
- Total Tests: 14
- Passed Tests: 14
- Success Rate: 100%
```

### JSON Output
```json
{
  "evaluation_type": "coding",
  "model_results": [
    {
      "model_name": "llama3",
      "provider": "ollama",
      "metrics": {
        "average_score": 92.5,
        "success_rate": 1.0,
        "total_problems": 2
      },
      "details": {
        "problem_results": [...]
      }
    }
  ],
  "summary": {
    "best_model": "llama3",
    "completion_rate": 1.0,
    "total_duration": 45.2
  }
}
```

## Troubleshooting Examples

If examples fail:

1. **Check model availability:**
   ```bash
   ./llm-eval models
   ./llm-eval test-model llama3
   ```

2. **Check environment:**
   ```bash
   echo $OPENROUTER_API_KEY
   echo $ENABLE_LOCAL_MODELS
   ```

3. **Run with verbose output:**
   ```bash
   ./examples/01_basic_coding_evaluation.sh --verbose
   ```

4. **Check logs:**
   ```bash
   tail -f logs/evaluation.log
   ```

For more troubleshooting, see [docs/troubleshooting.md](../docs/troubleshooting.md).

## Contributing Examples

To contribute new examples:

1. **Follow the naming convention:**
   - Shell scripts: `NN_descriptive_name.sh`
   - Python scripts: `descriptive_name.py`

2. **Include documentation:**
   - Add comments explaining parameters
   - Include usage examples
   - Document expected outputs

3. **Test thoroughly:**
   - Test with different models
   - Test with different parameters
   - Include error handling

4. **Submit pull request:**
   - Include description of the example
   - Explain the use case
   - Provide sample outputs