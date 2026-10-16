#!/bin/bash

# Basic Vision Evaluation Example
# 
# This script demonstrates how to run a basic vision evaluation using the unified CLI.
# It tests vision capabilities with image understanding tasks.
#
# Usage:
#   ./examples/02_basic_vision_evaluation.sh
#   ./examples/02_basic_vision_evaluation.sh --model llama3-vision --categories object_detection
#   ./examples/02_basic_vision_evaluation.sh --free-only --output vision_results.json

set -e  # Exit on any error

# Configuration (can be overridden by command line arguments)
MODEL_NAME="llama3-vision"
CATEGORIES="object_recognition,scene_description"
IMAGES=""
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
    echo -e "${BLUE}👁️  Basic Vision Evaluation Example${NC}"
    echo "========================================"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --categories)
            CATEGORIES="$2"
            shift 2
            ;;
        --images)
            IMAGES="$2"
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
            echo "  --model MODEL      Vision-capable model to use (default: llama3-vision)"
            echo "  --categories LIST  Comma-separated category list (default: object_recognition,scene_description)"
            echo "  --images LIST      Comma-separated image list (optional, uses test images)"
            echo "  --output FILE      Output file path"
            echo "  --format FORMAT    Output format: console, json, markdown, csv (default: console)"
            echo "  --free-only        Use only free models"
            echo "  --verbose          Enable verbose output"
            echo "  --timeout SECONDS  Timeout in seconds (default: 300)"
            echo "  --help             Show this help message"
            echo ""
            echo "Available categories:"
            echo "  • object_recognition - Identify objects in images"
            echo "  • scene_description - Describe scenes and settings"
            echo "  • text_in_image - Extract and read text from images"
            echo "  • chart_analysis - Analyze charts and graphs"
            echo "  • visual_reasoning - Solve visual puzzles and reasoning tasks"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --model llama3-vision --categories object_recognition"
            echo "  $0 --free-only --output vision_results.json --format json"
            echo "  $0 --images test_images/cat_sitting.jpg,test_images/chart.jpg"
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

# Check if test images directory exists
if [[ ! -d "test_images" ]]; then
    print_warning "test_images directory not found"
    print_info "Vision evaluation requires test images"
    print_info "The evaluation will use default images if available"
fi

# Show available vision models if using free-only
if [[ -n "$FREE_ONLY" ]]; then
    print_info "Available free vision models:"
    ./llm-eval models --free-only --capability vision --format list 2>/dev/null || {
        print_warning "No vision models found with --free-only"
        print_info "Available vision models:"
        ./llm-eval models --capability vision --format list 2>/dev/null || {
            print_error "No vision-capable models found"
            print_info "Please ensure you have vision models configured"
            exit 1
        }
    }
else
    # Verify model availability
    print_info "Verifying model availability..."
    if ! ./llm-eval test-model "$MODEL_NAME" > /dev/null 2>&1; then
        print_warning "Model '$MODEL_NAME' may not be available"
        print_info "Available vision models:"
        ./llm-eval models --capability vision --format list
        
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Exiting..."
            exit 0
        fi
    fi
fi

# Build command
CMD="./llm-eval vision"

# Add model selection
if [[ -n "$FREE_ONLY" ]]; then
    CMD="$CMD $FREE_ONLY"
else
    CMD="$CMD --model $MODEL_NAME"
fi

# Add categories
CMD="$CMD --categories $CATEGORIES"

# Add specific images if provided
if [[ -n "$IMAGES" ]]; then
    CMD="$CMD --images $IMAGES"
fi

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
if [[ -n "$FREE_ONLY" ]]; then
    echo "  Models: Free vision models only"
else
    echo "  Model: $MODEL_NAME"
fi
echo "  Categories: $CATEGORIES"
if [[ -n "$IMAGES" ]]; then
    echo "  Images: $IMAGES"
else
    echo "  Images: Using test image collection"
fi
echo "  Output Format: $OUTPUT_FORMAT"
if [[ -n "$OUTPUT_FILE" ]]; then
    echo "  Output File: $OUTPUT_FILE"
fi
echo "  Timeout: ${TIMEOUT}s"
echo ""

# Show test image info
if [[ -d "test_images" ]] && [[ -z "$IMAGES" ]]; then
    print_info "Available test image categories:"
    for category in test_images/*/; do
        if [[ -d "$category" ]]; then
            category_name=$(basename "$category")
            image_count=$(find "$category" -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l)
            echo "  • $category_name (${image_count} images)"
        fi
    done
    echo ""
fi

# Ask for confirmation
read -p "Run vision evaluation? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    print_info "Evaluation cancelled"
    exit 0
fi

# Run the evaluation
print_info "Starting vision evaluation..."
print_info "Command: $CMD"
echo ""

# Record start time
START_TIME=$(date +%s)

# Execute the command
if eval "$CMD"; then
    # Calculate duration
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    print_success "Vision evaluation completed successfully in ${DURATION}s"
    
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
    echo "  • View detailed results: cat $OUTPUT_FILE"
    echo "  • Run tool evaluation: ./examples/03_basic_tool_evaluation.sh"
    echo "  • Compare vision models: ./examples/05_comprehensive_evaluation.sh --vision-only"
    echo "  • Analyze specific images: ./llm-eval vision --images path/to/image.jpg"
    
else
    print_error "Vision evaluation failed"
    print_info "Troubleshooting steps:"
    echo "  1. Check vision models: ./llm-eval models --capability vision"
    echo "  2. Test model connectivity: ./llm-eval test-model $MODEL_NAME"
    echo "  3. Verify test images exist: ls -la test_images/"
    echo "  4. Check logs: tail -f logs/evaluation.log"
    echo "  5. Try with free models: $0 --free-only"
    echo "  6. See troubleshooting guide: docs/troubleshooting.md"
    exit 1
fi