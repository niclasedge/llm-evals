# LLM Evaluation CLI Tool - Usage Guide

## 🚀 Interactive Menu System

The CLI now features a user-friendly interactive menu system. Simply run:

```bash
python cli_runner.py
```

This will launch the interactive menu with the following options:

### Main Menu Options

1. **📋 List available models** - View all configured models with their providers and status
2. **📝 List test configurations** - Display available test configurations by category
3. **🚀 Run evaluation tests** - Interactive test setup with guided options
4. **📊 View test results** - Browse test results with multiple viewing options
5. **⚡ Show system status** - Quick overview of system health and recent activity
6. **🔍 Quick model health check** - Validate model availability and configuration
7. **❌ Quit** - Exit the CLI

## 🎯 Interactive Test Running

When you select option 3 (Run evaluation tests), you get a guided setup:

### Test Run Setup Steps

1. **Test Run Name** - Provide a name or use auto-generated timestamp
2. **Description** - Optional description for the test run
3. **Model Selection**:
   - Select specific models (interactive list)
   - Use all available models
   - Use only free models
4. **Test Selection**:
   - Select specific tests (interactive list)
   - Use all available tests
   - Select by category (Reasoning, Coding, etc.)
5. **Confirmation** - Review summary before execution

## 📊 Enhanced Results Viewing

Option 4 provides multiple ways to view results:

1. **Latest test run** - Show most recent test with detailed results
2. **All test runs** - Complete history of test executions
3. **Specific test run by ID** - View detailed results for a specific run
4. **Recent test runs** - Quick overview of recent activity

## 🔍 Model Health Check

The health check feature validates:

- **Ollama models**: Checks if Ollama service is running and models are downloaded
- **OpenRouter models**: Verifies API key configuration
- **Model availability**: Shows status and provides diagnostic information

## 💡 Command Line Usage

You can still use traditional command-line arguments:

```bash
# List models
python cli_runner.py list-models

# List tests
python cli_runner.py list-tests

# Run specific tests
python cli_runner.py run --name "My Test" --model "llama3.2-3b-local" --test "Basic Logic Test"

# Run all tests on all models
python cli_runner.py run --name "Full Evaluation" --all-models --all-tests

# View latest results
python cli_runner.py results --latest --detailed

# Show system status
python cli_runner.py status

# Launch interactive menu
python cli_runner.py menu
```

## 🛠️ Recent Fixes

### OpenRouter Model Configuration
- Removed non-working free models that were causing 404 errors
- Updated to only include verified working models:
  - `meta-llama/llama-3.1-8b-instruct:free`
  - `qwen/qwen-2-7b-instruct:free`

### Interactive Improvements
- Added intuitive menu system for users who don't know all commands
- Enhanced error handling and user feedback
- Real-time health checks for model availability
- Guided test setup with confirmation steps

## 🎨 Rich Formatting

The CLI uses rich formatting for better user experience:
- Color-coded status indicators
- Progress bars for long-running operations
- Formatted tables for easy data viewing
- Panel layouts for clear information grouping

## 🚨 Error Handling

The CLI now handles common issues gracefully:
- Model not found or unavailable
- API key missing or invalid
- Network connectivity issues
- Database connection problems

Users receive clear error messages and guidance on how to resolve issues.