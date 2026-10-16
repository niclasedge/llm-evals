#!/bin/bash

# Environment Setup Example
# 
# This script demonstrates how to set up the environment for LLM evaluations,
# including API keys, local models, and configuration options.
#
# Usage:
#   source examples/configs/setup_environment.sh
#   source examples/configs/setup_environment.sh --interactive
#   source examples/configs/setup_environment.sh --ollama-only

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}🔧 Environment Setup for LLM Evaluations${NC}"
    echo "=============================================="
}

# Parse arguments
INTERACTIVE=false
OLLAMA_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --ollama-only)
            OLLAMA_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: source $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --interactive    Interactive setup with prompts"
            echo "  --ollama-only    Setup only Ollama (skip API keys)"
            echo "  --help           Show this help message"
            echo ""
            echo "Environment variables configured:"
            echo "  OPENROUTER_API_KEY     - API key for OpenRouter service"
            echo "  ENABLE_LOCAL_MODELS    - Enable Ollama local models"
            echo "  ENABLE_OPENROUTER      - Enable OpenRouter API access"
            echo "  PYTHONPATH             - Python path for imports"
            echo ""
            echo "Example usage:"
            echo "  source $0                    # Basic setup"
            echo "  source $0 --interactive      # Interactive setup"
            echo "  source $0 --ollama-only      # Ollama only"
            return 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            return 1
            ;;
    esac
done

print_header

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to set environment variable
set_env_var() {
    local var_name="$1"
    local var_value="$2"
    local description="$3"
    
    export "$var_name"="$var_value"
    print_success "Set $var_name=$var_value"
    
    # Add to shell profile for persistence (if interactive)
    if [[ "$INTERACTIVE" == true ]]; then
        read -p "Add to shell profile for persistence? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Detect shell
            if [[ -n "$ZSH_VERSION" ]]; then
                SHELL_RC="$HOME/.zshrc"
            elif [[ -n "$BASH_VERSION" ]]; then
                SHELL_RC="$HOME/.bashrc"
            else
                SHELL_RC="$HOME/.profile"
            fi
            
            # Check if already exists
            if ! grep -q "export $var_name=" "$SHELL_RC" 2>/dev/null; then
                echo "export $var_name=\"$var_value\"" >> "$SHELL_RC"
                print_success "Added to $SHELL_RC"
            else
                print_info "Already exists in $SHELL_RC"
            fi
        fi
    fi
}

# 1. Set up Python path
print_info "Setting up Python path..."
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
set_env_var "PYTHONPATH" "$PROJECT_ROOT/src:$PYTHONPATH" "Add project src to Python path"

# 2. Configure local models (Ollama)
print_info "Configuring local models..."

if command_exists ollama; then
    print_success "Ollama is installed"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_success "Ollama service is running"
        
        # List installed models
        INSTALLED_MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v '^$' || echo "")
        if [[ -n "$INSTALLED_MODELS" ]]; then
            print_success "Installed Ollama models:"
            echo "$INSTALLED_MODELS" | sed 's/^/    • /'
        else
            print_warning "No Ollama models installed"
            
            if [[ "$INTERACTIVE" == true ]]; then
                read -p "Install recommended models? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    print_info "Installing recommended models (this may take a while)..."
                    ollama pull llama3.3:8b
                    ollama pull phi4-reasoning
                    print_success "Models installed"
                fi
            else
                print_info "To install models later, run:"
                echo "    ollama pull llama3.3:8b"
                echo "    ollama pull phi4-reasoning"
                echo "    ollama pull gemma3:27b"
            fi
        fi
        
        # Enable local models
        set_env_var "ENABLE_LOCAL_MODELS" "true" "Enable Ollama local models"
        
    else
        print_warning "Ollama service is not running"
        print_info "Start Ollama with: ollama serve"
        
        if [[ "$INTERACTIVE" == true ]]; then
            read -p "Start Ollama now? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_info "Starting Ollama service..."
                ollama serve &
                sleep 3
                if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
                    print_success "Ollama service started"
                    set_env_var "ENABLE_LOCAL_MODELS" "true" "Enable Ollama local models"
                else
                    print_error "Failed to start Ollama service"
                fi
            fi
        else
            set_env_var "ENABLE_LOCAL_MODELS" "false" "Ollama not running - disabled"
        fi
    fi
else
    print_warning "Ollama is not installed"
    print_info "Install Ollama:"
    echo "    curl -fsSL https://ollama.ai/install.sh | sh"
    echo "    # or on macOS: brew install ollama"
    
    if [[ "$INTERACTIVE" == true ]] && [[ "$OLLAMA_ONLY" == false ]]; then
        read -p "Continue without Ollama? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            print_info "Setup cancelled"
            return 1
        fi
    fi
    
    set_env_var "ENABLE_LOCAL_MODELS" "false" "Ollama not available"
fi

# 3. Configure API access (skip if ollama-only)
if [[ "$OLLAMA_ONLY" == false ]]; then
    print_info "Configuring API access..."
    
    # OpenRouter API key
    if [[ -n "$OPENROUTER_API_KEY" ]]; then
        print_success "OpenRouter API key is already set"
        set_env_var "ENABLE_OPENROUTER" "true" "OpenRouter API enabled"
    else
        print_warning "OpenRouter API key not set"
        
        if [[ "$INTERACTIVE" == true ]]; then
            read -p "Do you have an OpenRouter API key? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                read -p "Enter your OpenRouter API key: " -s OPENROUTER_KEY
                echo
                if [[ -n "$OPENROUTER_KEY" ]]; then
                    set_env_var "OPENROUTER_API_KEY" "$OPENROUTER_KEY" "OpenRouter API key"
                    set_env_var "ENABLE_OPENROUTER" "true" "OpenRouter API enabled"
                else
                    print_warning "Empty API key provided"
                    set_env_var "ENABLE_OPENROUTER" "false" "No API key"
                fi
            else
                print_info "You can get an API key from: https://openrouter.ai/"
                set_env_var "ENABLE_OPENROUTER" "false" "No API key"
            fi
        else
            print_info "Set OPENROUTER_API_KEY environment variable to enable API access"
            print_info "Get API key from: https://openrouter.ai/"
            set_env_var "ENABLE_OPENROUTER" "false" "No API key provided"
        fi
    fi
else
    print_info "Skipping API configuration (--ollama-only mode)"
    set_env_var "ENABLE_OPENROUTER" "false" "Ollama-only mode"
fi

# 4. Verify setup
print_info "Verifying setup..."

# Check if CLI is working
if [[ -x "$PROJECT_ROOT/llm-eval" ]]; then
    print_success "LLM evaluation CLI is available"
    
    # Test CLI
    if "$PROJECT_ROOT/llm-eval" --help >/dev/null 2>&1; then
        print_success "CLI is working"
        
        # List available models
        print_info "Available models:"
        if "$PROJECT_ROOT/llm-eval" models --format list 2>/dev/null | head -5; then
            print_success "Models are accessible"
        else
            print_warning "No models available or CLI error"
        fi
    else
        print_error "CLI is not working properly"
    fi
else
    print_error "LLM evaluation CLI not found"
    print_info "Make sure you're in the project root directory"
    print_info "Run: chmod +x llm-eval"
fi

# 5. Summary
print_info "Environment Setup Summary:"
echo "  Project Root: $PROJECT_ROOT"
echo "  Python Path: $PYTHONPATH"
echo "  Local Models: ${ENABLE_LOCAL_MODELS:-false}"
echo "  OpenRouter API: ${ENABLE_OPENROUTER:-false}"

if [[ "${ENABLE_LOCAL_MODELS:-false}" == "true" ]] || [[ "${ENABLE_OPENROUTER:-false}" == "true" ]]; then
    print_success "Setup completed successfully!"
    print_info "You can now run evaluations:"
    echo "    ./llm-eval models                    # List available models"
    echo "    ./llm-eval coding --free-only        # Run coding evaluation"
    echo "    ./llm-eval all --free-only           # Run comprehensive evaluation"
else
    print_warning "No models or APIs configured"
    print_info "You need either:"
    echo "  • Ollama installed and running with models"
    echo "  • OpenRouter API key for cloud models"
fi

# 6. Next steps
echo ""
print_info "Next steps:"
if [[ "${ENABLE_LOCAL_MODELS:-false}" == "false" ]]; then
    echo "  • Install and setup Ollama: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "  • Pull models: ollama pull llama3.3:8b"
fi
if [[ "${ENABLE_OPENROUTER:-false}" == "false" ]]; then
    echo "  • Get OpenRouter API key: https://openrouter.ai/"
    echo "  • Set API key: export OPENROUTER_API_KEY='your-key'"
fi
echo "  • Test setup: ./llm-eval models"
echo "  • Run examples: ./examples/01_basic_coding_evaluation.sh"
echo "  • Read documentation: docs/unified_interface.md"

print_success "Environment setup complete!"