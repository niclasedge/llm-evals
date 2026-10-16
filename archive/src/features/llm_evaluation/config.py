# Configuration for LLM Evaluations

import os
from typing import List, Optional

# Import the unified configuration system
try:
    from src.core.llm_unified_config import get_unified_config, UnifiedLLMConfig
    _unified_config = get_unified_config()
    UNIFIED_CONFIG_AVAILABLE = True
except ImportError:
    print("Warning: Unified configuration system not available. Using legacy configuration.")
    _unified_config = None
    UNIFIED_CONFIG_AVAILABLE = False

# --- Unified Configuration Integration ---
# The unified configuration system provides a centralized way to manage all LLM models
# and their configurations. It supports LLM CLI format and provides backward compatibility.

def get_unified_config_instance() -> Optional[UnifiedLLMConfig]:
    """Get the unified configuration instance"""
    return _unified_config

# --- Ollama Configuration ---
# Set to True to enable evaluations using Ollama, False to disable.
ENABLE_OLLAMA = os.getenv("ENABLE_LOCAL_MODELS", "false").lower() == "true"

# Ollama provider settings
# Default base URL for Ollama. Change if your Ollama server runs elsewhere.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# --- Go Service Integration Configuration ---
# Set to True to enable Go service integration, False to use direct Ollama only
ENABLE_GO_SERVICE = os.getenv("ENABLE_GO_SERVICE", "false").lower() == "true"

# Go service settings
GO_SERVICE_URL = os.getenv("GO_SERVICE_URL", "http://localhost:8080")
GO_SERVICE_FALLBACK = os.getenv("GO_SERVICE_FALLBACK", "true").lower() == "true"
GO_SERVICE_TIMEOUT = int(os.getenv("GO_SERVICE_TIMEOUT", "30"))
GO_SERVICE_RETRY_ATTEMPTS = int(os.getenv("GO_SERVICE_RETRY_ATTEMPTS", "3"))
GO_SERVICE_CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("GO_SERVICE_CIRCUIT_BREAKER_THRESHOLD", "5"))
GO_SERVICE_CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("GO_SERVICE_CIRCUIT_BREAKER_TIMEOUT", "60"))

# Enhanced Ollama configuration with Go service integration
OLLAMA_VIA_GO_SERVICE = ENABLE_GO_SERVICE and ENABLE_OLLAMA

# List of Ollama model names to test (e.g., ["llama3", "mistral"])
# Ensure these models are pulled and available in your Ollama instance (`ollama list`)
def get_ollama_models_to_test() -> List[str]:
    """Get Ollama models to test from unified config or fallback to legacy"""
    if UNIFIED_CONFIG_AVAILABLE and _unified_config:
        backward_compatible = _unified_config.get_backward_compatible_lists()
        return backward_compatible.get('ollama', [])
    else:
        return [
            "llama3",
            # "mistral", 
            # Add more Ollama models here
        ]

OLLAMA_MODELS_TO_TEST = get_ollama_models_to_test()

# --- OpenRouter Configuration ---
# Set to True to enable evaluations using OpenRouter, False to disable.
ENABLE_OPENROUTER = os.getenv("ENABLE_OPENROUTER", "true").lower() == "true"

# OpenRouter API Key. It's recommended to set this as an environment variable.
# The code will try to fetch it from 'OPENROUTER_API_KEY'.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter provider settings
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# List of OpenRouter model identifiers to test
# Find model identifiers on the OpenRouter website (e.g., "mistralai/mistral-7b-instruct")
def get_openrouter_models_to_test() -> List[str]:
    """Get OpenRouter models to test from unified config or fallback to legacy"""
    if UNIFIED_CONFIG_AVAILABLE and _unified_config:
        backward_compatible = _unified_config.get_backward_compatible_lists()
        return backward_compatible.get('openrouter', [])
    else:
        return [
            "meta-llama/llama-3.3-8b-instruct:free", # Known to work and return AgentRunResult
            "google/gemma-3-1b-it:free",             # Known to return None
            "google/gemma-3-4b-it:free",             # Enabled for testing
            "google/gemma-3-12b-it:free",            # Enabled for testing
            "google/gemma-3-27b-it:free",            # Enabled for testing
            "microsoft/phi-4-reasoning:free",        # Microsoft Phi-4 reasoning model
            "microsoft/phi-4-reasoning-plus:free",   # Microsoft Phi-4 reasoning plus model
            "deepseek/deepseek-chat-v3-0324:free",  # DeepSeek Chat v3 model
            "deepseek/deepseek-r1-zero:free",       # DeepSeek R1 Zero model
            "mistralai/devstral-small:free",        # Mistral Devstral Small model
            # "mistralai/mistral-7b-instruct:free", # Example, often available
            # "openai/gpt-3.5-turbo", # Requires credits
            # "anthropic/claude-3-haiku:beta", # Might require credits or be restricted
            # "google/gemma-7b-it:free", # Example, often available
            # "nousresearch/nous-hermes-2-mixtral-8x7b-dpo:free", # Large, might be slow or have issues
            # "meta-llama/llama-3-8b-instruct:free", # Good to test
            # Add more models from the openrouter-models.csv or openrouter-free-models.txt as needed
            # --- From openrouter-free-models.txt (Top Tier, July 2024) ---
            # "qwen/qwen3-30b-a3b:free",
            # "qwen/qwen3-8b:free",
            # "qwen/qwen3-14b:free",
            # "qwen/qwen3-32b:free",
            # "qwen/qwen3-235b-a22b:free",
            # "google/gemma-3n-e4b-it:free",
            # "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
        ]

OPENROUTER_MODELS_TO_TEST = get_openrouter_models_to_test()

# --- Unified Configuration Helper Functions ---
def get_model_by_name(name: str) -> Optional[str]:
    """
    Get model ID by name using unified configuration
    
    Args:
        name: Model name, alias, or LLM CLI format
        
    Returns:
        Provider-specific model ID or None if not found
    """
    if UNIFIED_CONFIG_AVAILABLE and _unified_config:
        return _unified_config.get_provider_format(name)
    return None

def get_model_by_llm_cli_format(name: str) -> Optional[str]:
    """
    Get model ID from LLM CLI format using unified configuration
    
    Args:
        name: LLM CLI format (e.g., "openrouter:meta-llama/llama-3.3-8b-instruct:free")
        
    Returns:
        Provider-specific model ID or None if not found
    """
    if UNIFIED_CONFIG_AVAILABLE and _unified_config:
        return _unified_config.get_provider_format(name)
    return None

def list_available_models(provider: str = None, capability: str = None) -> List[str]:
    """
    List available models with optional filtering
    
    Args:
        provider: Filter by provider (openrouter, ollama, etc.)
        capability: Filter by capability (text, vision, code, etc.)
        
    Returns:
        List of model names
    """
    if UNIFIED_CONFIG_AVAILABLE and _unified_config:
        models = _unified_config.list_models(provider=provider, capability=capability)
        return [model.name for model in models]
    return []

def get_default_model(use_case: str = "text") -> Optional[str]:
    """
    Get default model for a specific use case
    
    Args:
        use_case: Use case (text, vision, code, local, free)
        
    Returns:
        Default model name or None if not found
    """
    env_var_map = {
        "text": "DEFAULT_TEXT_MODEL",
        "vision": "DEFAULT_VISION_MODEL", 
        "code": "DEFAULT_CODE_MODEL",
        "local": "DEFAULT_LOCAL_MODEL",
        "free": "DEFAULT_FREE_MODEL"
    }
    
    env_var = env_var_map.get(use_case)
    if env_var:
        return os.getenv(env_var)
    
    return None

# --- Vision Testing Configuration ---
# Set to True to enable vision model testing, False to disable.
ENABLE_VISION_TESTING = os.getenv("ENABLE_VISION_MODELS", "true").lower() == "true"

# Path to vision test images
VISION_TEST_IMAGES_PATH = "test_images/"

# Vision-capable models for OpenRouter
def get_openrouter_vision_models_to_test() -> List[str]:
    """Get OpenRouter vision models to test from unified config or fallback to legacy"""
    if UNIFIED_CONFIG_AVAILABLE and _unified_config:
        models = _unified_config.list_models(provider="openrouter", capability="vision")
        return [model.model_id for model in models if model.enabled]
    else:
        return [
            "meta-llama/llama-3.2-11b-vision-instruct:free",
            "meta-llama/llama-3.2-90b-vision-instruct:free",
            "google/gemma-2-9b-it:free",
            "google/gemma-2-27b-it:free",
            "qwen/qwen2-vl-7b-instruct:free",
            "qwen/qwen2-vl-72b-instruct:free",
        ]

OPENROUTER_VISION_MODELS_TO_TEST = get_openrouter_vision_models_to_test()

# Vision-capable models for Ollama  
def get_ollama_vision_models_to_test() -> List[str]:
    """Get Ollama vision models to test from unified config or fallback to legacy"""
    if UNIFIED_CONFIG_AVAILABLE and _unified_config:
        models = _unified_config.list_models(provider="ollama", capability="vision")
        return [model.model_id for model in models if model.enabled]
    else:
        return [
            "llava:latest",
            "llava:7b",
            "llava:13b",
            "bakllava:latest",
            "moondream:latest",
        ]

OLLAMA_VISION_MODELS_TO_TEST = get_ollama_vision_models_to_test()

# Vision test categories
VISION_TEST_CATEGORIES = [
    "object_recognition",
    "scene_description", 
    "text_in_image",
    "visual_reasoning",
    "chart_analysis"
]

# --- General Evaluation Settings ---
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
DEFAULT_VISION_SYSTEM_PROMPT = "You are a helpful assistant that can analyze images and provide detailed descriptions."

# Request timeouts (in seconds)
REQUEST_TIMEOUT = 120
VISION_REQUEST_TIMEOUT = 180  # Vision requests may take longer

# --- Intelligence Testing Configuration ---
# Set to True to enable intelligence tests, False to disable.
ENABLE_INTELLIGENCE_TESTING = True

# Intelligence test settings
INTELLIGENCE_TEST_TIMEOUT = 300  # 5 minutes for complex reasoning tasks
INTELLIGENCE_MAX_CONCURRENT_TESTS = 3  # Limit concurrent tests to avoid overwhelming models

# Intelligence test categories to run by default
DEFAULT_INTELLIGENCE_CATEGORIES = [
    "graphical_representation",  # GraphViz DOT diagrams
    "mathematical_reasoning",    # Math word problems, calculations
    "logical_reasoning",         # Logic puzzles, syllogisms
    "pattern_recognition",       # Sequence patterns, abstract patterns
    "creative_thinking",         # Creative problem solving, divergent thinking
    "abstract_reasoning",        # Analogies, concept formation
    "spatial_reasoning"          # Spatial transformations, mental rotation
]

# Default complexity levels to test (1=basic, 2=intermediate, 3=advanced, 4=expert)
DEFAULT_COMPLEXITY_LEVELS = [1, 2, 3]

# Intelligence test output settings
INTELLIGENCE_RESULTS_DIR = "intelligence_test_results/"
SAVE_DETAILED_RESPONSES = True  # Save full model responses for analysis
GENERATE_MARKDOWN_REPORTS = True  # Generate human-readable markdown reports

# --- Image Generation Configuration ---
# Set to True to enable image generation model testing, False to disable.
ENABLE_IMAGE_GENERATION = True

# OpenAI DALL-E Configuration
ENABLE_DALLE = True
DALLE_API_KEY = os.getenv("OPENAI_API_KEY")
DALLE_MODELS_TO_TEST = [
    "dall-e-3",
    "dall-e-2"
]

# Stability AI Configuration  
ENABLE_STABILITY_AI = False
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
STABILITY_MODELS_TO_TEST = [
    "stable-diffusion-xl-1024-v1-0",
    "stable-diffusion-v1-6"
]

# Image Generation Settings
IMAGE_OUTPUT_DIR = "generated_images"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_IMAGE_QUALITY = "standard"
IMAGE_GENERATION_TIMEOUT = 300  # 5 minutes for image generation

# --- Advanced Evaluation Optimization Configuration ---
# Statistical Evaluation Settings
STATISTICAL_VALIDATION_ENABLED = True
CONFIDENCE_LEVEL = 0.95
MIN_SAMPLE_SIZE = 30
MULTIPLE_RUNS_COUNT = 5
SIGNIFICANCE_THRESHOLD = 0.05
BOOTSTRAP_SAMPLES = 1000

# LLM Judge Configuration
LLM_JUDGE_ENABLED = True
JUDGE_MODELS = ["gpt-4", "claude-3-opus", "gemini-pro"]
JUDGE_CONSENSUS_THRESHOLD = 0.8
JUDGE_CALIBRATION_ENABLED = True
JUDGE_BIAS_CORRECTION_ENABLED = True

# Evaluation Quality Settings
EVALUATION_QUALITY_CHECKS = True
BIAS_DETECTION_ENABLED = True
REPRODUCIBILITY_CHECKS = True
PERFORMANCE_REGRESSION_DETECTION = True

# Test Data Management
DATASET_VERSIONING_ENABLED = True
DATASET_VALIDATION_ENABLED = True
DATA_AUGMENTATION_ENABLED = True
STRATIFIED_SAMPLING_ENABLED = True

# Automated Test Generation
AUTO_TEST_GENERATION_ENABLED = True
ADVERSARIAL_TESTING_ENABLED = True
EDGE_CASE_GENERATION_ENABLED = True
SYNTHETIC_DATA_GENERATION_ENABLED = True

# Performance Analytics
PERFORMANCE_ANALYTICS_ENABLED = True
TREND_ANALYSIS_ENABLED = True
COMPARATIVE_ANALYSIS_ENABLED = True
AUTOMATED_INSIGHTS_ENABLED = True

# Evaluation Infrastructure
DISTRIBUTED_EVALUATION_ENABLED = False  # Set to True for distributed setup
EVALUATION_CHECKPOINTING_ENABLED = True
EVALUATION_CACHING_ENABLED = True
RESOURCE_OPTIMIZATION_ENABLED = True

# Monitoring and Observability
EVALUATION_MONITORING_ENABLED = True
PERFORMANCE_TRACKING_ENABLED = True
COST_TRACKING_ENABLED = True
ALERT_SYSTEM_ENABLED = True

# Benchmark Integration
BENCHMARK_INTEGRATION_ENABLED = True
STANDARD_BENCHMARKS = ["mmlu", "arc_easy", "arc_challenge", "hellaswag", "gsm8k"]
BENCHMARK_COMPARISON_ENABLED = True
LEADERBOARD_INTEGRATION_ENABLED = True

# You can add more configuration variables here as needed,
# for example, paths to datasets, specific evaluation metrics, etc.

# --- Sanity Checks (Optional but Recommended) ---
if ENABLE_OPENROUTER and not OPENROUTER_API_KEY:
    print("Warning: ENABLE_OPENROUTER is True, but OPENROUTER_API_KEY is not set. OpenRouter evaluations will likely fail.")

if ENABLE_IMAGE_GENERATION and ENABLE_DALLE and not DALLE_API_KEY:
    print("Warning: ENABLE_DALLE is True, but OPENAI_API_KEY is not set. DALL-E evaluations will likely fail.")

# --- Configuration Status Print ---
print(f"Configuration loaded from: src/features/llm_evaluation/config.py")
print(f"  Unified Configuration: {'Available' if UNIFIED_CONFIG_AVAILABLE else 'Not Available (using legacy)'}")
print(f"  Ollama Enabled: {ENABLE_OLLAMA}")
if ENABLE_OLLAMA:
    print(f"    Ollama Models: {OLLAMA_MODELS_TO_TEST}")
    print(f"    Ollama Base URL: {OLLAMA_BASE_URL}")
print(f"  Go Service Integration: {ENABLE_GO_SERVICE}")
if ENABLE_GO_SERVICE:
    print(f"    Go Service URL: {GO_SERVICE_URL}")
    print(f"    Go Service Fallback: {GO_SERVICE_FALLBACK}")
    print(f"    Go Service Timeout: {GO_SERVICE_TIMEOUT}s")
    print(f"    Ollama via Go Service: {OLLAMA_VIA_GO_SERVICE}")
print(f"  OpenRouter Enabled: {ENABLE_OPENROUTER}")
if ENABLE_OPENROUTER:
    print(f"    OpenRouter Models: {OPENROUTER_MODELS_TO_TEST}")
    if not OPENROUTER_API_KEY:
        print(f"    OpenRouter API Key: NOT SET (will cause errors if OpenRouter is enabled)")
    else:
        print(f"    OpenRouter API Key: Set (first/last 4 chars: {OPENROUTER_API_KEY[:4]}...{OPENROUTER_API_KEY[-4:] if len(OPENROUTER_API_KEY) > 7 else ''})")

if UNIFIED_CONFIG_AVAILABLE:
    print(f"  Unified Configuration Status:")
    print(f"    Config Path: {_unified_config.config_path}")
    print(f"    Available Models: {len(_unified_config.models)}")
    print(f"    Available Providers: {_unified_config.list_providers()}")
    print(f"    Available Aliases: {len(_unified_config.aliases)}")
    
    # Print some example model mappings
    print(f"  Example Model Mappings:")
    for alias in ["llama3", "llama3-vision", "gemma1b"]:
        model = _unified_config.get_model_by_alias(alias)
        if model:
            print(f"    {alias} -> {model.model_id} ({model.provider})")
        else:
            print(f"    {alias} -> Not found")

# --- Backward Compatibility Validation ---
if UNIFIED_CONFIG_AVAILABLE and _unified_config:
    # Validate that all existing models in the legacy configuration exist in the unified config
    legacy_models = [
        "meta-llama/llama-3.3-8b-instruct:free",
        "google/gemma-3-1b-it:free",
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        "meta-llama/llama-3.2-90b-vision-instruct:free",
        "qwen/qwen2-vl-7b-instruct:free",
        "qwen/qwen2-vl-72b-instruct:free"
    ]
    
    missing_models = []
    for model_id in legacy_models:
        if not _unified_config.get_model_by_id(model_id):
            missing_models.append(model_id)
    
    if missing_models:
        print(f"Warning: The following legacy models are not found in unified config:")
        for model_id in missing_models:
            print(f"  - {model_id}")
    else:
        print("✓ All legacy models are available in unified configuration")

