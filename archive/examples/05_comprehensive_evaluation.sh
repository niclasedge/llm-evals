#!/bin/bash

# Comprehensive Evaluation Example
# 
# This script demonstrates how to run a comprehensive evaluation across all evaluation types.
# It provides a complete assessment of LLM capabilities including coding, vision, tools, and intelligence.
#
# Usage:
#   ./examples/05_comprehensive_evaluation.sh
#   ./examples/05_comprehensive_evaluation.sh --models llama3,phi4 --output comprehensive_results.json
#   ./examples/05_comprehensive_evaluation.sh --free-only --format markdown

set -e  # Exit on any error

# Configuration (can be overridden by command line arguments)
MODELS="llama3"
OUTPUT_FORMAT="console"
OUTPUT_FILE=""
FREE_ONLY=""
VERBOSE=""
TIMEOUT=600
PARALLEL="--parallel"
EVALUATION_TYPES="all"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_step() {
    echo -e "${PURPLE}🔄 $1${NC}"
}

print_header() {
    echo -e "${BLUE}🚀 Comprehensive LLM Evaluation${NC}"
    echo "============================================"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --models)
            MODELS="$2"
            shift 2
            ;;
        --model)
            MODELS="$2"
            shift 2
            ;;
        --types)
            EVALUATION_TYPES="$2"
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
        --sequential)
            PARALLEL="--sequential"
            shift
            ;;
        --parallel)
            PARALLEL="--parallel"
            shift
            ;;
        --coding-only)
            EVALUATION_TYPES="coding"
            shift
            ;;
        --vision-only)
            EVALUATION_TYPES="vision"
            shift
            ;;
        --tools-only)
            EVALUATION_TYPES="tools"
            shift
            ;;
        --intelligence-only)
            EVALUATION_TYPES="intelligence"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --models LIST      Comma-separated model list (default: llama3)"
            echo "  --model MODEL      Single model to use"
            echo "  --types LIST       Evaluation types: all, coding, vision, tools, intelligence (default: all)"
            echo "  --output FILE      Output file path"
            echo "  --format FORMAT    Output format: console, json, markdown, csv (default: console)"
            echo "  --free-only        Use only free models"
            echo "  --verbose          Enable verbose output"
            echo "  --timeout SECONDS  Timeout in seconds (default: 600)"
            echo "  --parallel         Run evaluations in parallel (default)"
            echo "  --sequential       Run evaluations sequentially"
            echo "  --coding-only      Run only coding evaluation"
            echo "  --vision-only      Run only vision evaluation"
            echo "  --tools-only       Run only tool evaluation"
            echo "  --intelligence-only Run only intelligence evaluation"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                          # Default comprehensive evaluation"
            echo "  $0 --models llama3,phi4,gemma3             # Compare multiple models"
            echo "  $0 --free-only --output results.json       # Free models, save to JSON"
            echo "  $0 --coding-only --models llama3,phi4      # Coding evaluation only"
            echo "  $0 --sequential --timeout 900              # Sequential execution with extended timeout"
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

# Pre-flight checks
print_step "Running pre-flight checks..."

# Check available models
print_info "Checking model availability..."
if [[ -n "$FREE_ONLY" ]]; then
    AVAILABLE_MODELS=$(./llm-eval models --free-only --format list 2>/dev/null || echo "")
    if [[ -z "$AVAILABLE_MODELS" ]]; then
        print_error "No free models available"
        print_info "Try without --free-only or ensure models are properly configured"
        exit 1
    fi
    print_info "Available free models:"
    echo "$AVAILABLE_MODELS"
else
    # Verify specific models if not using free-only
    IFS=',' read -ra MODEL_ARRAY <<< "$MODELS"
    for model in "${MODEL_ARRAY[@]}"; do
        model=$(echo "$model" | xargs)  # Trim whitespace
        if ! ./llm-eval test-model "$model" > /dev/null 2>&1; then
            print_warning "Model '$model' may not be available"
        else
            print_success "Model '$model' is available"
        fi
    done
fi

# Check evaluation requirements
if [[ "$EVALUATION_TYPES" == "all" ]] || [[ "$EVALUATION_TYPES" == *"vision"* ]]; then
    if [[ ! -d "test_images" ]]; then
        print_warning "test_images directory not found - vision evaluation may fail"
    else
        print_success "Test images available for vision evaluation"
    fi
fi

# Check disk space for results
AVAILABLE_SPACE=$(df . | tail -1 | awk '{print $4}')
if [[ "$AVAILABLE_SPACE" -lt 100000 ]]; then  # Less than ~100MB
    print_warning "Low disk space available"
fi

# Build command
if [[ "$EVALUATION_TYPES" == "all" ]]; then
    CMD="./llm-eval all"
else
    CMD="./llm-eval $EVALUATION_TYPES"
fi

# Add model selection
if [[ -n "$FREE_ONLY" ]]; then
    CMD="$CMD $FREE_ONLY"
else
    CMD="$CMD --models $MODELS"
fi

# Add execution options
CMD="$CMD $PARALLEL"
CMD="$CMD --timeout $TIMEOUT"

# Add output options
CMD="$CMD --format $OUTPUT_FORMAT"
if [[ -n "$OUTPUT_FILE" ]]; then
    CMD="$CMD --output $OUTPUT_FILE"
fi

# Add verbose if requested
if [[ -n "$VERBOSE" ]]; then
    CMD="$CMD $VERBOSE"
fi

# Display configuration summary
print_info "Evaluation Configuration:"
if [[ -n "$FREE_ONLY" ]]; then
    echo "  Models: Free models only"
else
    echo "  Models: $MODELS"
fi
echo "  Evaluation Types: $EVALUATION_TYPES"
echo "  Execution Mode: $(echo $PARALLEL | sed 's/--//')"
echo "  Output Format: $OUTPUT_FORMAT"
if [[ -n "$OUTPUT_FILE" ]]; then
    echo "  Output File: $OUTPUT_FILE"
fi
echo "  Timeout: ${TIMEOUT}s"

# Estimate duration
if [[ "$EVALUATION_TYPES" == "all" ]]; then
    MODEL_COUNT=$(echo "$MODELS" | tr ',' '\n' | wc -l)
    if [[ -n "$FREE_ONLY" ]]; then
        MODEL_COUNT=$(echo "$AVAILABLE_MODELS" | wc -l)
    fi
    
    if [[ "$PARALLEL" == "--parallel" ]]; then
        ESTIMATED_DURATION=$((TIMEOUT / 2))  # Parallel execution is roughly 2x faster
    else
        ESTIMATED_DURATION=$((TIMEOUT * MODEL_COUNT))
    fi
    
    echo "  Estimated Duration: ${ESTIMATED_DURATION}s ($(($ESTIMATED_DURATION / 60))m)"
fi
echo ""

# Show what will be evaluated
print_info "Evaluation will include:"
if [[ "$EVALUATION_TYPES" == "all" ]] || [[ "$EVALUATION_TYPES" == *"coding"* ]]; then
    echo "  📝 Coding: Programming problems in multiple languages"
fi
if [[ "$EVALUATION_TYPES" == "all" ]] || [[ "$EVALUATION_TYPES" == *"vision"* ]]; then
    echo "  👁️  Vision: Image understanding and analysis"
fi
if [[ "$EVALUATION_TYPES" == "all" ]] || [[ "$EVALUATION_TYPES" == *"tools"* ]]; then
    echo "  🔧 Tools: Function calling and tool usage"
fi
if [[ "$EVALUATION_TYPES" == "all" ]] || [[ "$EVALUATION_TYPES" == *"intelligence"* ]]; then
    echo "  🧠 Intelligence: Reasoning and logic problems"
fi
echo ""

# Final confirmation
print_warning "This is a comprehensive evaluation that may take significant time and resources."
read -p "Continue with evaluation? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    print_info "Evaluation cancelled"
    exit 0
fi

# Create results directory if needed
if [[ -n "$OUTPUT_FILE" ]]; then
    OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
    mkdir -p "$OUTPUT_DIR"
fi

# Run the evaluation
print_step "Starting comprehensive evaluation..."
print_info "Command: $CMD"
echo ""

# Record start time
START_TIME=$(date +%s)

# Progress indicator function
show_progress() {
    local duration=$1
    local interval=30  # Update every 30 seconds
    local elapsed=0
    
    while [[ $elapsed -lt $duration ]] && kill -0 $! 2>/dev/null; do
        sleep $interval
        elapsed=$((elapsed + interval))
        local progress=$((elapsed * 100 / duration))
        print_info "Progress: ${elapsed}s elapsed (~${progress}% estimated)"
    done
}

# Execute the command with progress tracking
if [[ -n "$VERBOSE" ]]; then
    # Run directly for verbose output
    eval "$CMD"
    EVAL_SUCCESS=$?
else
    # Run in background with progress tracking
    eval "$CMD" &
    EVAL_PID=$!
    
    # Show progress updates
    show_progress $TIMEOUT &
    PROGRESS_PID=$!
    
    # Wait for evaluation to complete
    wait $EVAL_PID
    EVAL_SUCCESS=$?
    
    # Stop progress updates
    kill $PROGRESS_PID 2>/dev/null || true
fi

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))

if [[ $EVAL_SUCCESS -eq 0 ]]; then
    print_success "Comprehensive evaluation completed successfully!"
    print_success "Total duration: ${DURATION_MIN}m ${DURATION_SEC}s"
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        print_success "Results saved to: $OUTPUT_FILE"
        
        # Show file info
        if [[ -f "$OUTPUT_FILE" ]]; then
            FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
            FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
            print_info "File size: ${FILE_SIZE_MB}MB (${FILE_SIZE} bytes)"
            
            # Show results preview
            if [[ "$OUTPUT_FORMAT" == "json" ]]; then
                print_info "Results preview:"
                if command -v jq >/dev/null 2>&1; then
                    echo "Summary:"
                    jq '.summary // {summary: "No summary available"}' "$OUTPUT_FILE" 2>/dev/null
                    echo ""
                    echo "Model Results:"
                    jq '.model_results[] | {model: .model_name, metrics: .metrics}' "$OUTPUT_FILE" 2>/dev/null | head -20
                else
                    echo "Use 'jq' to parse JSON results:"
                    echo "jq '.summary' $OUTPUT_FILE"
                fi
            elif [[ "$OUTPUT_FORMAT" == "markdown" ]]; then
                print_info "Results preview (first 20 lines):"
                head -20 "$OUTPUT_FILE"
            fi
        fi
    fi
    
    # Performance summary
    print_info "Performance Summary:"
    echo "  • Total Duration: ${DURATION_MIN}m ${DURATION_SEC}s"
    echo "  • Execution Mode: $(echo $PARALLEL | sed 's/--//')"
    if [[ -n "$FREE_ONLY" ]]; then
        echo "  • Models Used: Free models only"
    else
        echo "  • Models Used: $MODELS"
    fi
    echo "  • Evaluation Types: $EVALUATION_TYPES"
    
    # Suggest next steps
    echo ""
    print_info "Next steps:"
    echo "  • View detailed results: cat $OUTPUT_FILE"
    echo "  • Generate HTML report: python examples/automation/report_generator.py --input $OUTPUT_FILE"
    echo "  • Compare with previous results: python examples/python/model_comparison.py"
    echo "  • Run individual evaluations for deeper analysis:"
    echo "    - ./examples/01_basic_coding_evaluation.sh"
    echo "    - ./examples/02_basic_vision_evaluation.sh" 
    echo "    - ./examples/03_basic_tool_evaluation.sh"
    echo "    - ./examples/04_basic_intelligence_evaluation.sh"
    
else
    print_error "Comprehensive evaluation failed after ${DURATION_MIN}m ${DURATION_SEC}s"
    print_info "Troubleshooting steps:"
    echo "  1. Check model availability: ./llm-eval models"
    echo "  2. Test individual models: ./llm-eval test-model MODEL_NAME"
    echo "  3. Check logs: tail -f logs/evaluation.log"
    echo "  4. Try sequential execution: $0 --sequential"
    echo "  5. Try individual evaluation types:"
    echo "     - $0 --coding-only"
    echo "     - $0 --tools-only" 
    echo "     - $0 --intelligence-only"
    echo "  6. Use free models only: $0 --free-only"
    echo "  7. Increase timeout: $0 --timeout 900"
    echo "  8. See troubleshooting guide: docs/troubleshooting.md"
    exit 1
fi