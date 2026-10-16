#!/bin/bash

# Basic Coding Evaluation Example
# 
# This script demonstrates how to run a basic coding evaluation using the unified CLI.
# It tests programming capabilities with a selection of common problems.
#
# Usage:
#   ./examples/01_basic_coding_evaluation.sh
#   ./examples/01_basic_coding_evaluation.sh --model phi4 --problems fibonacci,sorting
#   ./examples/01_basic_coding_evaluation.sh --free-only --output results.json

set -e  # Exit on any error

# Configuration (can be overridden by command line arguments)
MODEL_NAME="llama3"
PROBLEMS="fibonacci,palindrome"
LANGUAGES="python,javascript"
OUTPUT_FORMAT="console"
OUTPUT_FILE=""
FREE_ONLY=""
VERBOSE=""
TIMEOUT=300

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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
    echo -e "${BLUE}📝 Basic Coding Evaluation Example${NC}"
    echo "========================================"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --problems)
            PROBLEMS="$2"
            shift 2
            ;;
        --languages)
            LANGUAGES="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --free-only)
            FREE_ONLY="--free-only"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --model MODEL      Model to use (default: llama3)"
            echo "  --problems LIST    Comma-separated problem list (default: fibonacci,palindrome)"
            echo "  --languages LIST   Comma-separated language list (default: python,javascript)"
            echo "  --output FILE      Output file path"
            echo "  --format FORMAT    Output format: console, json, markdown, csv (default: console)"
            echo "  --free-only        Use only free models"
            echo "  --verbose          Enable verbose output"
            echo "  --timeout SECONDS  Timeout in seconds (default: 300)"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --model phi4 --problems fibonacci,sorting"
            echo "  $0 --free-only --output results.json --format json"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print header
print_header

# Check if llm-eval exists and is executable
if [[ ! -x "./llm-eval" ]]; then
    print_error "llm-eval not found or not executable"
    print_info "Make sure you're in the project root directory"
    print_info "Run: chmod +x llm-eval"
    exit 1
fi

# Verify model availability
print_info "Verifying model availability..."
if ! ./llm-eval test-model "$MODEL_NAME" > /dev/null 2>&1; then
    print_warning "Model '$MODEL_NAME' may not be available"
    print_info "Available models:"
    ./llm-eval models --format list
    
    # If using free-only, suggest free models
    if [[ -n "$FREE_ONLY" ]]; then
        print_info "Free models:"
        ./llm-eval models --free-only --format list
    fi
    
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Exiting..."
        exit 0
    fi
fi

# Build command
CMD="./llm-eval coding"

# Add model selection
if [[ -n "$FREE_ONLY" ]]; then
    CMD="$CMD $FREE_ONLY"
else
    CMD="$CMD --model $MODEL_NAME"
fi

# Add problems and languages
CMD="$CMD --problems $PROBLEMS"
CMD="$CMD --languages $LANGUAGES"

# Add output options
CMD="$CMD --format $OUTPUT_FORMAT"
if [[ -n "$OUTPUT_FILE" ]]; then
    CMD="$CMD --output $OUTPUT_FILE"
fi

# Add other options
if [[ -n "$VERBOSE" ]]; then
    CMD="$CMD $VERBOSE"
fi

CMD="$CMD --timeout $TIMEOUT"

# Display configuration
print_info "Configuration:"
echo "  Model: $MODEL_NAME"
echo "  Problems: $PROBLEMS"
echo "  Languages: $LANGUAGES"
echo "  Output Format: $OUTPUT_FORMAT"
if [[ -n "$OUTPUT_FILE" ]]; then
    echo "  Output File: $OUTPUT_FILE"
fi
if [[ -n "$FREE_ONLY" ]]; then
    echo "  Free Models Only: Yes"
fi
echo "  Timeout: ${TIMEOUT}s"
echo ""

# Ask for confirmation
read -p "Run evaluation? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    print_info "Evaluation cancelled"
    exit 0
fi

# Run the evaluation
print_info "Starting coding evaluation..."
print_info "Command: $CMD"
echo ""

# Record start time
START_TIME=$(date +%s)

# Execute the command
if eval "$CMD"; then
    # Calculate duration
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    print_success "Evaluation completed successfully in ${DURATION}s"
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        print_success "Results saved to: $OUTPUT_FILE"
        
        # Show file size and basic info
        if [[ -f "$OUTPUT_FILE" ]]; then
            FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
            print_info "File size: ${FILE_SIZE} bytes"
            
            # If JSON, show basic structure
            if [[ "$OUTPUT_FORMAT" == "json" && -f "$OUTPUT_FILE" ]]; then
                print_info "Results preview:"
                if command -v jq >/dev/null 2>&1; then
                    jq '.summary // .model_results[0].metrics // .' "$OUTPUT_FILE" 2>/dev/null | head -10
                else
                    head -5 "$OUTPUT_FILE"
                fi
            fi
        fi
    fi
    
    # Suggest next steps
    echo ""
    print_info "Next steps:"
    echo "  • View results in detail: cat $OUTPUT_FILE"
    echo "  • Run vision evaluation: ./examples/02_basic_vision_evaluation.sh"
    echo "  • Compare multiple models: ./examples/05_comprehensive_evaluation.sh"
    echo "  • View troubleshooting: docs/troubleshooting.md"
    
else
    print_error "Evaluation failed"
    print_info "Troubleshooting steps:"
    echo "  1. Check model availability: ./llm-eval models"
    echo "  2. Test model connectivity: ./llm-eval test-model $MODEL_NAME"
    echo "  3. Check logs: tail -f logs/evaluation.log"
    echo "  4. Try with free models: $0 --free-only"
    echo "  5. See troubleshooting guide: docs/troubleshooting.md"
    exit 1
fi