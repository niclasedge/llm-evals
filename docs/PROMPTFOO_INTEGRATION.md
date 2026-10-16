# Promptfoo Integration for llm-evals

This document describes the promptfoo integration added to the llm-evals project.

## Overview

Promptfoo is a powerful, YAML-based evaluation framework for LLMs that provides:
- **Side-by-side model comparison** across multiple providers
- **Flexible assertion types** (contains, regex, LLM-as-judge)
- **Web-based results viewer** with interactive dashboards
- **Multi-provider support** (Ollama, OpenRouter, OpenAI, Anthropic)

## Directory Structure

```
llm-evals/
└── promptfoo/                         # New promptfoo evaluation system
    ├── package.json                   # Node dependencies
    ├── promptfoo_cli.py              # Python CLI wrapper
    ├── .env.example                   # Environment variable template
    ├── .gitignore                     # Git ignore rules
    ├── README.md                      # Comprehensive documentation
    ├── QUICKSTART.md                  # Quick start guide
    ├── requirements.txt               # Python dependencies (reference)
    ├── configs/                       # Evaluation configurations
    │   ├── basic_text.yaml           # Text generation tests
    │   ├── code_generation.yaml      # Code generation tests
    │   └── reasoning.yaml            # Logic & reasoning tests
    ├── tests/                         # Custom test data (future)
    └── results/                       # Evaluation results
        ├── basic_text_results.json
        ├── code_generation_results.json
        └── reasoning_results.json
```

## Files Created

### Core Files

1. **promptfoo/package.json**
   - Defines Node dependencies (promptfoo)
   - Provides package scripts for running evaluations
   - Scripts: eval, eval:basic, eval:code, eval:reasoning, eval:all, view

2. **promptfoo/promptfoo_cli.py** (755 lines)
   - Python wrapper for promptfoo CLI
   - Commands: run, view, models, info, check
   - Dependency checking and validation
   - Ollama connectivity testing

3. **promptfoo/.env.example**
   - Template for environment variables
   - Documents required API keys (OpenRouter, OpenAI, Anthropic)
   - Ollama configuration notes

4. **promptfoo/.gitignore**
   - Ignores node_modules, .env, cache files
   - Preserves results/ by default

### Configuration Files

5. **promptfoo/configs/basic_text.yaml**
   - Tests: Question answering, creative writing, knowledge
   - 4 test cases with various assertion types
   - 6 providers (4 Ollama local, 2 OpenRouter)
   - Assertions: contains, llm-rubric, javascript, contains-all

6. **promptfoo/configs/code_generation.yaml**
   - Tests: Algorithm implementation, multi-language code
   - 6 test cases (Python, JavaScript, algorithms)
   - 6 providers (code-focused models)
   - Assertions: contains-all, llm-rubric for code quality

7. **promptfoo/configs/reasoning.yaml**
   - Tests: Math, logic puzzles, pattern recognition, probability
   - 7 test cases covering diverse reasoning tasks
   - 5 providers (reasoning-specialized models)
   - Assertions: contains, contains-any, llm-rubric

### Documentation

8. **promptfoo/README.md** (400+ lines)
   - Comprehensive documentation
   - Setup instructions
   - Configuration examples
   - Troubleshooting guide
   - Integration details

9. **promptfoo/QUICKSTART.md** (300+ lines)
   - Quick start guide
   - Step-by-step setup
   - Common issues and solutions
   - Tips for best results

10. **PROMPTFOO_INTEGRATION.md** (this file)
    - Integration overview
    - Architecture details
    - Usage instructions

### Makefile Integration

Added to `Makefile`:
```makefile
# New help section
@echo "📊 Promptfoo Evaluations:"
@echo "  make promptfoo-setup    - Setup promptfoo and dependencies"
@echo "  make promptfoo-basic    - Run basic text evaluation"
@echo "  make promptfoo-code     - Run code generation evaluation"
@echo "  make promptfoo-reasoning- Run reasoning evaluation"
@echo "  make promptfoo-all      - Run all promptfoo evaluations"
@echo "  make promptfoo-view     - View promptfoo results in browser"
@echo "  make promptfoo-models   - List available models"

# New targets
promptfoo-setup        # Setup Node dependencies
promptfoo-check        # Verify environment
promptfoo-basic        # Run basic text tests
promptfoo-code         # Run code tests
promptfoo-reasoning    # Run reasoning tests
promptfoo-all          # Run all tests
promptfoo-view         # Start web viewer
promptfoo-models       # List models
promptfoo-info         # Show config info
promptfoo-clean        # Clean cache
```

## Models Configured

### Local Models (Ollama)

Text & General:
- qwen3:8b - General-purpose local model
- deepseek-r1:8b - Advanced reasoning model
- phi4-reasoning:latest - Microsoft's reasoning specialist
- qwen3:4b - Efficient smaller model
- llama3.2:3b - Compact multi-purpose
- gemma3:4b - Google's efficient model
- mistral:7b - Versatile local model

Code-Focused:
- qwen2.5-coder:7b - Specialized code model
- deepseek-r1:8b - Code + reasoning
- mistral:7b - General code support

Vision:
- llama3.2-vision:11b - Multi-modal vision model

### Cloud Models (OpenRouter - Free Tier)
- meta-llama/llama-3.1-8b-instruct:free
- qwen/qwen-2-7b-instruct:free

## Usage Methods

### 1. Makefile (Recommended for llm-evals project)

```bash
# Setup
make promptfoo-setup

# Run evaluations
make promptfoo-basic
make promptfoo-code
make promptfoo-reasoning
make promptfoo-all

# View results
make promptfoo-view

# Utilities
make promptfoo-models
make promptfoo-info
make promptfoo-clean
```

### 2. Python CLI

```bash
cd promptfoo

# Setup and check
python promptfoo_cli.py check

# Run evaluations
python promptfoo_cli.py run basic
python promptfoo_cli.py run code
python promptfoo_cli.py run reasoning
python promptfoo_cli.py run all

# View results
python promptfoo_cli.py view

# Utilities
python promptfoo_cli.py models
python promptfoo_cli.py info
```

### 3. Package Scripts

```bash
cd promptfoo

# Install
pnpm install

# Run evaluations
pnpm run eval:basic
pnpm run eval:code
pnpm run eval:reasoning
pnpm run eval:all

# View results
pnpm run view

# Clean cache
pnpm run cache:clear
```

### 4. Direct promptfoo CLI

```bash
cd promptfoo

# Run with custom config
pnpm exec promptfoo eval -c configs/basic_text.yaml

# View results
pnpm exec promptfoo view

# List evaluations
pnpm exec promptfoo list
```

## Evaluation Types

### Basic Text Generation
- **Purpose**: Test fundamental text generation
- **Test Cases**: 4
- **Models**: 6 (4 local + 2 cloud)
- **Categories**:
  - Factual knowledge
  - Creative writing
  - Concise explanations
  - List comprehension

### Code Generation
- **Purpose**: Test programming capabilities
- **Test Cases**: 6
- **Models**: 6 (4 local + 2 cloud)
- **Categories**:
  - Algorithm implementation (Fibonacci, binary search, quicksort)
  - Language-specific tasks (Python, JavaScript)
  - Code quality and structure
  - Error handling

### Reasoning
- **Purpose**: Test logical reasoning
- **Test Cases**: 7
- **Models**: 5 (3 local + 2 cloud)
- **Categories**:
  - Mathematical reasoning
  - Logic puzzles
  - Pattern recognition
  - Deductive reasoning
  - Probability calculations
  - Spatial reasoning

## Assertion Types Used

### 1. contains
Checks if output contains specific text:
```yaml
assert:
  - type: contains
    value: "Paris"
```

### 2. contains-all
Checks if output contains all specified values:
```yaml
assert:
  - type: contains-all
    value: ["red", "blue", "yellow"]
```

### 3. contains-any
Checks if output contains any of the values:
```yaml
assert:
  - type: contains-any
    value: ["cannot", "can't", "no"]
```

### 4. llm-rubric
Uses an LLM to judge if output meets criteria:
```yaml
assert:
  - type: llm-rubric
    value: "The answer should mention Paris as the capital of France"
```

### 5. javascript
Custom JavaScript assertion for complex checks:
```yaml
assert:
  - type: javascript
    value: "output.length < 500"
```

## Integration with Existing System

### Shared Configuration
- Uses same models from `configs/llm_model_mapping.yaml`
- Follows same naming conventions
- Integrates with existing Makefile structure

### Complementary to Existing Tests
- Promptfoo: YAML-based, comparative evaluations
- Existing system: Python-based, programmatic tests
- Both systems can run independently
- Results can be cross-referenced

### Results Storage
- Promptfoo results: `promptfoo/results/*.json`
- Existing results: `test_results/`
- Separate but compatible storage

## Advantages of Promptfoo

1. **Easy Configuration**: YAML-based, no coding required
2. **Visual Comparison**: Web UI shows side-by-side results
3. **Multiple Assertion Types**: Flexible validation methods
4. **LLM-as-Judge**: Uses LLMs to evaluate responses
5. **Multi-Provider**: Test same prompt across providers
6. **Fast Setup**: Quick to add new test cases
7. **Standard Tool**: Industry-standard evaluation framework

## Comparison with Existing System

| Feature | Existing System | Promptfoo |
|---------|----------------|-----------|
| Configuration | Python code | YAML files |
| Test Definition | Python classes | YAML objects |
| Assertion Types | Python functions | Multiple types |
| Visualization | Custom dashboard | Built-in web UI |
| Model Switching | Configuration | Per-test basis |
| Results Format | Custom JSON | Standard JSON |
| Learning Curve | Python knowledge | YAML knowledge |
| Flexibility | Very high | High |
| Speed of Setup | Medium | Fast |

## Use Cases

### Use Promptfoo When:
- Quick comparative testing needed
- Non-developers creating tests
- Standard evaluation patterns
- Visual comparison important
- Multiple models to compare
- YAML configuration preferred

### Use Existing System When:
- Complex custom evaluation logic
- Deep integration with codebase
- Programmatic test generation
- Custom metrics required
- Python-based workflow
- Advanced test orchestration

## Future Enhancements

Potential additions:
1. **Custom Test Data**: Add test datasets in `tests/`
2. **CI/CD Integration**: Automated evaluation runs
3. **Result Comparison**: Compare with existing system results
4. **More Providers**: Add Anthropic, Gemini configs
5. **Custom Assertions**: JavaScript-based custom checks
6. **Template Library**: Common test templates
7. **Result Export**: Export to various formats

## Troubleshooting

### Setup Issues
```bash
# Check environment
make promptfoo-check
# or
cd promptfoo && python promptfoo_cli.py check
```

### Ollama Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# List models
ollama list
```

### OpenRouter Issues
```bash
# Verify API key
echo $OPENROUTER_API_KEY

# Or check .env file
cat promptfoo/.env
```

### pnpm Issues
```bash
# Clear cache and reinstall
cd promptfoo
rm -rf node_modules package-lock.json
pnpm install
```

## Getting Started

Quick start steps:
```bash
# 1. Setup promptfoo
make promptfoo-setup

# 2. Configure environment (if using OpenRouter)
cd promptfoo
cp .env.example .env
# Edit .env with your API key

# 3. Download local models
ollama pull qwen3:8b
ollama pull deepseek-r1:8b
ollama pull phi4-reasoning:latest

# 4. Run first evaluation
make promptfoo-basic

# 5. View results
make promptfoo-view
```

## Documentation

- **Quick Start**: See `promptfoo/QUICKSTART.md`
- **Full Docs**: See `promptfoo/README.md`
- **Configurations**: See YAML files in `promptfoo/configs/`
- **Examples**: Run `make promptfoo-info` for config details

## Contributing

To add new evaluation types:
1. Create YAML config in `promptfoo/configs/`
2. Add package script to `package.json`
3. Add make target to `Makefile`
4. Update documentation

## Summary

The promptfoo integration provides a complementary evaluation system to the existing llm-evals framework. It offers:
- Fast YAML-based test configuration
- Side-by-side model comparison
- Built-in web visualization
- Industry-standard evaluation patterns

It integrates seamlessly with the existing project structure while maintaining independence for different use cases.

---

**Status**: ✅ Complete and ready to use

**Last Updated**: 2025-10-17

**Version**: 1.0.0
