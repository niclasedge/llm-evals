"""
Validation utilities for unified evaluation

This module provides validation functions for evaluation requests,
model configurations, and other evaluation parameters.
"""

import re
import os
from typing import List, Dict, Optional, Any
from pathlib import Path

from src.core.llm_unified_config import get_unified_config
from ..models import EvaluationRequest, ModelSelection, OutputConfig, EvaluationType


def validate_request(request: EvaluationRequest) -> List[str]:
    """
    Validate evaluation request
    
    Args:
        request: Evaluation request to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Validate model selection
    model_errors = validate_model_selection(request.model_selection)
    errors.extend(model_errors)
    
    # Validate output configuration
    output_errors = validate_output_config(request.output_config)
    errors.extend(output_errors)
    
    # Validate evaluation type specific parameters
    type_errors = validate_evaluation_type_params(request)
    errors.extend(type_errors)
    
    # Validate general parameters
    if request.timeout <= 0:
        errors.append("Timeout must be positive")
    
    if request.max_retries < 0:
        errors.append("Max retries cannot be negative")
    
    return errors


def validate_model_selection(model_selection: ModelSelection) -> List[str]:
    """
    Validate model selection
    
    Args:
        model_selection: Model selection to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    config = get_unified_config()
    
    # Validate specific models
    if model_selection.models:
        for model_name in model_selection.models:
            if not config.resolve_model_name(model_name):
                errors.append(f"Model '{model_name}' not found or not configured")
    
    # Validate providers
    if model_selection.providers:
        available_providers = config.list_providers()
        for provider in model_selection.providers:
            if provider not in available_providers:
                errors.append(f"Provider '{provider}' not available")
    
    # Validate capabilities
    if model_selection.capabilities:
        valid_capabilities = ['text', 'vision', 'code', 'function_calling']
        for capability in model_selection.capabilities:
            if capability not in valid_capabilities:
                errors.append(f"Invalid capability '{capability}'. Valid capabilities: {valid_capabilities}")
    
    # Check if any models match the selection criteria
    try:
        available_models = config.list_models(
            provider=model_selection.providers[0] if model_selection.providers else None,
            capability=model_selection.capabilities[0] if model_selection.capabilities else None,
            free_only=model_selection.free_only,
            enabled_only=model_selection.enabled_only
        )
        
        if not available_models and not model_selection.models:
            errors.append("No models found matching the selection criteria")
    except Exception as e:
        errors.append(f"Error checking model availability: {str(e)}")
    
    return errors


def validate_output_config(output_config: OutputConfig) -> List[str]:
    """
    Validate output configuration
    
    Args:
        output_config: Output configuration to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Validate output file path
    if output_config.file_path:
        file_path = Path(output_config.file_path)
        
        # Check if parent directory exists or can be created
        parent_dir = file_path.parent
        if not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create output directory '{parent_dir}': {str(e)}")
        
        # Check if file is writable
        if file_path.exists():
            if not file_path.is_file():
                errors.append(f"Output path '{file_path}' exists but is not a file")
            elif not os.access(file_path, os.W_OK):
                errors.append(f"Output file '{file_path}' is not writable")
    
    return errors


def validate_evaluation_type_params(request: EvaluationRequest) -> List[str]:
    """
    Validate evaluation type specific parameters
    
    Args:
        request: Evaluation request to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if request.evaluation_type == EvaluationType.CODING:
        errors.extend(validate_coding_params(request))
    elif request.evaluation_type == EvaluationType.VISION:
        errors.extend(validate_vision_params(request))
    elif request.evaluation_type == EvaluationType.TOOLS:
        errors.extend(validate_tools_params(request))
    elif request.evaluation_type == EvaluationType.INTELLIGENCE:
        errors.extend(validate_intelligence_params(request))
    
    return errors


def validate_coding_params(request: EvaluationRequest) -> List[str]:
    """Validate coding evaluation parameters"""
    errors = []
    
    # Validate languages
    if request.languages:
        valid_languages = ['python', 'javascript', 'java', 'cpp', 'c']
        for language in request.languages:
            if language not in valid_languages:
                errors.append(f"Invalid language '{language}'. Valid languages: {valid_languages}")
    
    # Validate difficulty
    if request.difficulty:
        valid_difficulties = ['easy', 'medium', 'hard']
        if request.difficulty.lower() not in valid_difficulties:
            errors.append(f"Invalid difficulty '{request.difficulty}'. Valid difficulties: {valid_difficulties}")
    
    # Validate problems (if specific problems are requested)
    if request.problems:
        # This would require checking against available problems
        # For now, just validate format
        for problem in request.problems:
            if not isinstance(problem, str) or not problem.strip():
                errors.append(f"Invalid problem identifier: '{problem}'")
    
    return errors


def validate_vision_params(request: EvaluationRequest) -> List[str]:
    """Validate vision evaluation parameters"""
    errors = []
    
    # Validate image paths
    if request.images:
        for image_path in request.images:
            path = Path(image_path)
            if not path.exists():
                errors.append(f"Image file not found: '{image_path}'")
            elif not path.is_file():
                errors.append(f"Image path is not a file: '{image_path}'")
            elif not _is_image_file(path):
                errors.append(f"Invalid image file format: '{image_path}'")
    
    # Validate categories
    if request.categories:
        valid_categories = ['description', 'counting', 'ocr', 'classification', 'detection']
        for category in request.categories:
            if category not in valid_categories:
                errors.append(f"Invalid vision category '{category}'. Valid categories: {valid_categories}")
    
    return errors


def validate_tools_params(request: EvaluationRequest) -> List[str]:
    """Validate tools evaluation parameters"""
    errors = []
    
    # Validate scenarios
    if request.scenarios:
        valid_scenarios = ['basic_calculation', 'weather_lookup', 'file_operations', 'multi_step_analysis']
        for scenario in request.scenarios:
            if scenario not in valid_scenarios:
                errors.append(f"Invalid tool scenario '{scenario}'. Valid scenarios: {valid_scenarios}")
    
    return errors


def validate_intelligence_params(request: EvaluationRequest) -> List[str]:
    """Validate intelligence evaluation parameters"""
    errors = []
    
    # Validate categories
    if request.categories:
        valid_categories = ['logic', 'creative', 'pattern', 'reasoning', 'math']
        for category in request.categories:
            if category not in valid_categories:
                errors.append(f"Invalid intelligence category '{category}'. Valid categories: {valid_categories}")
    
    return errors


def validate_model_config(model_config: Dict[str, Any]) -> List[str]:
    """
    Validate model configuration
    
    Args:
        model_config: Model configuration dictionary
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Required fields
    required_fields = ['name', 'provider', 'model_id']
    for field in required_fields:
        if field not in model_config:
            errors.append(f"Missing required field: '{field}'")
        elif not model_config[field]:
            errors.append(f"Empty required field: '{field}'")
    
    # Validate provider
    if 'provider' in model_config:
        valid_providers = ['openrouter', 'ollama', 'openai', 'anthropic']
        if model_config['provider'] not in valid_providers:
            errors.append(f"Invalid provider '{model_config['provider']}'. Valid providers: {valid_providers}")
    
    # Validate capabilities
    if 'capabilities' in model_config:
        valid_capabilities = ['text', 'vision', 'code', 'function_calling']
        for capability in model_config['capabilities']:
            if capability not in valid_capabilities:
                errors.append(f"Invalid capability '{capability}'. Valid capabilities: {valid_capabilities}")
    
    # Validate model name format
    if 'name' in model_config:
        if not re.match(r'^[a-zA-Z0-9_-]+$', model_config['name']):
            errors.append(f"Invalid model name format: '{model_config['name']}'. Use only letters, numbers, underscores, and hyphens.")
    
    return errors


def validate_file_path(file_path: str, must_exist: bool = True) -> List[str]:
    """
    Validate file path
    
    Args:
        file_path: File path to validate
        must_exist: Whether the file must exist
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not file_path:
        errors.append("File path cannot be empty")
        return errors
    
    path = Path(file_path)
    
    if must_exist and not path.exists():
        errors.append(f"File does not exist: '{file_path}'")
    elif path.exists() and not path.is_file():
        errors.append(f"Path is not a file: '{file_path}'")
    
    # Check if parent directory exists
    parent_dir = path.parent
    if not parent_dir.exists():
        errors.append(f"Parent directory does not exist: '{parent_dir}'")
    
    return errors


def _is_image_file(path: Path) -> bool:
    """Check if file is a valid image file"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
    return path.suffix.lower() in image_extensions


def validate_timeout(timeout: int) -> List[str]:
    """
    Validate timeout value
    
    Args:
        timeout: Timeout value in seconds
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if timeout <= 0:
        errors.append("Timeout must be positive")
    elif timeout > 3600:  # 1 hour limit
        errors.append("Timeout cannot exceed 3600 seconds (1 hour)")
    
    return errors


def validate_parallel_settings(parallel: bool, max_concurrent: int = 10) -> List[str]:
    """
    Validate parallel execution settings
    
    Args:
        parallel: Whether parallel execution is enabled
        max_concurrent: Maximum concurrent executions
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if parallel and max_concurrent <= 0:
        errors.append("Max concurrent executions must be positive when parallel is enabled")
    elif max_concurrent > 50:  # Reasonable limit
        errors.append("Max concurrent executions cannot exceed 50")
    
    return errors