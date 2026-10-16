"""
Compatibility layer for LLM Evaluation Framework

This module provides backward compatibility for existing users migrating
to the unified configuration system and new architecture patterns.

Features:
- Legacy environment variable support
- Model name mapping and aliases
- Import path compatibility
- Configuration format conversion
- Deprecation warnings
"""

import os
import warnings
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json
import yaml

# Setup logging
logger = logging.getLogger(__name__)

# Model name mapping for backward compatibility
LEGACY_MODEL_MAPPING = {
    # Ollama model mappings
    "llama3": "llama3.3-8b-local",
    "mistral": "mistral-small-local", 
    "phi3": "phi4-reasoning-local",
    "gemma": "gemma3-27b-local",
    "devstral": "devstral-local",
    "deepseek-r1": "deepseek-r1-8b-local",
    
    # OpenRouter model mappings (short names to full)
    "llama-3.3-8b": "llama3.3-8b-free",
    "gemma-3-1b": "gemma3-1b-free",
    "mistral-7b": "mistral-7b-free",
    
    # Full OpenRouter model IDs to unified names
    "meta-llama/llama-3.3-8b-instruct:free": "llama3.3-8b-free",
    "google/gemma-3-1b-it:free": "gemma3-1b-free",
    "mistralai/mistral-7b-instruct:free": "mistral-7b-free",
    "google/gemma-2-27b-it:free": "gemma3-27b-free",
    "google/gemma-2-9b-it:free": "gemma3-9b-free",
}

# Reverse mapping for model ID resolution
UNIFIED_TO_LEGACY_MAPPING = {v: k for k, v in LEGACY_MODEL_MAPPING.items()}

# Environment variable mappings
LEGACY_ENV_MAPPING = {
    "ENABLE_LOCAL_MODELS": "ENABLE_OLLAMA",
    "ENABLE_OPENROUTER": "ENABLE_OPENROUTER", 
    "OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
    "DEFAULT_OLLAMA_MODEL": "DEFAULT_OLLAMA_MODEL",
    "DEFAULT_OPENROUTER_MODEL": "DEFAULT_OPENROUTER_MODEL",
}

# Configuration file paths
LEGACY_CONFIG_PATH = "src/features/llm_evaluation/config.py"
UNIFIED_CONFIG_PATH = "configs/llm_model_mapping.yaml"

class DeprecationLevel:
    """Deprecation warning levels"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"

def emit_deprecation_warning(message: str, level: str = DeprecationLevel.WARNING, stacklevel: int = 2):
    """Emit deprecation warning with appropriate level"""
    full_message = f"[DEPRECATED] {message}"
    
    if level == DeprecationLevel.INFO:
        logger.info(full_message)
    elif level == DeprecationLevel.WARNING:
        warnings.warn(full_message, DeprecationWarning, stacklevel=stacklevel)
        logger.warning(full_message)
    elif level == DeprecationLevel.ERROR:
        logger.error(full_message)
        raise DeprecationWarning(full_message)

def get_legacy_env_var(name: str, default: Any = None, warn: bool = True) -> Any:
    """
    Get environment variable with legacy support and deprecation warning
    
    Args:
        name: Environment variable name
        default: Default value if not found
        warn: Whether to emit deprecation warning
        
    Returns:
        Environment variable value or default
    """
    value = os.getenv(name, default)
    
    if value is not None and warn:
        if name in LEGACY_ENV_MAPPING:
            new_name = LEGACY_ENV_MAPPING[name]
            emit_deprecation_warning(
                f"Environment variable '{name}' is deprecated. "
                f"Use '{new_name}' or unified configuration instead."
            )
    
    return value

def get_legacy_boolean_env(name: str, default: bool = False, warn: bool = True) -> bool:
    """Get boolean environment variable with legacy support"""
    value = get_legacy_env_var(name, str(default).lower(), warn)
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)

def migrate_model_name(model_name: str, warn: bool = True) -> str:
    """
    Migrate legacy model name to unified name
    
    Args:
        model_name: Legacy model name
        warn: Whether to emit deprecation warning
        
    Returns:
        Unified model name
    """
    if model_name in LEGACY_MODEL_MAPPING:
        new_name = LEGACY_MODEL_MAPPING[model_name]
        if warn:
            emit_deprecation_warning(
                f"Model name '{model_name}' is deprecated. "
                f"Use '{new_name}' instead."
            )
        return new_name
    
    return model_name

def migrate_model_list(model_list: List[str], warn: bool = True) -> List[str]:
    """
    Migrate list of legacy model names to unified names
    
    Args:
        model_list: List of legacy model names
        warn: Whether to emit deprecation warning
        
    Returns:
        List of unified model names
    """
    return [migrate_model_name(model, warn) for model in model_list]

def get_legacy_model_list(env_var_name: str, default: Optional[List[str]] = None, warn: bool = True) -> List[str]:
    """
    Get model list from environment variable with legacy support
    
    Args:
        env_var_name: Environment variable name containing comma-separated model names
        default: Default model list if environment variable not found
        warn: Whether to emit deprecation warning
        
    Returns:
        List of unified model names
    """
    if default is None:
        default = []
    
    env_value = get_legacy_env_var(env_var_name, warn=warn)
    if env_value:
        if isinstance(env_value, str):
            model_list = [model.strip() for model in env_value.split(",")]
        else:
            model_list = env_value
        return migrate_model_list(model_list, warn)
    
    return default

def get_model_mapping() -> Dict[str, str]:
    """Get complete model mapping dictionary"""
    return LEGACY_MODEL_MAPPING.copy()

def resolve_model_id(unified_name: str) -> str:
    """
    Resolve unified model name to actual model ID for provider
    
    Args:
        unified_name: Unified model name
        
    Returns:
        Actual model ID for the provider
    """
    # Try to load from unified config first
    try:
        from src.core.llm_unified_config import get_model_config
        config = get_model_config(unified_name)
        if config and "model_id" in config:
            return config["model_id"]
    except ImportError:
        pass
    
    # Fall back to reverse mapping
    if unified_name in UNIFIED_TO_LEGACY_MAPPING:
        return UNIFIED_TO_LEGACY_MAPPING[unified_name]
    
    # Return as-is if no mapping found
    return unified_name

class LegacyConfigSupport:
    """Support for legacy configuration patterns"""
    
    def __init__(self):
        self._legacy_config = {}
        self._load_legacy_config()
    
    def _load_legacy_config(self):
        """Load legacy configuration from config.py"""
        try:
            # Try to import legacy config
            import importlib.util
            spec = importlib.util.spec_from_file_location("legacy_config", LEGACY_CONFIG_PATH)
            if spec and spec.loader:
                legacy_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(legacy_module)
                
                # Extract configuration values
                self._legacy_config = {
                    "ENABLE_OLLAMA": getattr(legacy_module, "ENABLE_OLLAMA", False),
                    "ENABLE_OPENROUTER": getattr(legacy_module, "ENABLE_OPENROUTER", False),
                    "OLLAMA_MODELS_TO_TEST": getattr(legacy_module, "OLLAMA_MODELS_TO_TEST", []),
                    "OPENROUTER_MODELS_TO_TEST": getattr(legacy_module, "OPENROUTER_MODELS_TO_TEST", []),
                }
        except (ImportError, FileNotFoundError, AttributeError) as e:
            logger.debug(f"Could not load legacy config: {e}")
    
    def get_ollama_models(self, warn: bool = True) -> List[str]:
        """Get Ollama models from legacy config with migration"""
        models = self._legacy_config.get("OLLAMA_MODELS_TO_TEST", [])
        if models and warn:
            emit_deprecation_warning(
                "Using OLLAMA_MODELS_TO_TEST from legacy config. "
                "Migrate to unified configuration."
            )
        return migrate_model_list(models, warn)
    
    def get_openrouter_models(self, warn: bool = True) -> List[str]:
        """Get OpenRouter models from legacy config with migration"""
        models = self._legacy_config.get("OPENROUTER_MODELS_TO_TEST", [])
        if models and warn:
            emit_deprecation_warning(
                "Using OPENROUTER_MODELS_TO_TEST from legacy config. "
                "Migrate to unified configuration."
            )
        return migrate_model_list(models, warn)
    
    def is_ollama_enabled(self, warn: bool = True) -> bool:
        """Check if Ollama is enabled in legacy config"""
        # Check environment variable first
        env_enabled = get_legacy_boolean_env("ENABLE_LOCAL_MODELS", warn=warn)
        if env_enabled:
            return True
        
        # Fall back to legacy config
        enabled = self._legacy_config.get("ENABLE_OLLAMA", False)
        if enabled and warn:
            emit_deprecation_warning(
                "Using ENABLE_OLLAMA from legacy config. "
                "Use ENABLE_LOCAL_MODELS environment variable or unified configuration."
            )
        return enabled
    
    def is_openrouter_enabled(self, warn: bool = True) -> bool:
        """Check if OpenRouter is enabled in legacy config"""
        # Check environment variable first
        env_enabled = get_legacy_boolean_env("ENABLE_OPENROUTER", warn=warn)
        if env_enabled:
            return True
        
        # Fall back to legacy config
        enabled = self._legacy_config.get("ENABLE_OPENROUTER", False)
        if enabled and warn:
            emit_deprecation_warning(
                "Using ENABLE_OPENROUTER from legacy config. "
                "Use environment variable or unified configuration."
            )
        return enabled

# Global instance for backward compatibility
_legacy_config_support = LegacyConfigSupport()

def get_backward_compatible_ollama_models() -> List[str]:
    """Get Ollama models with full backward compatibility"""
    return _legacy_config_support.get_ollama_models()

def get_backward_compatible_openrouter_models() -> List[str]:
    """Get OpenRouter models with full backward compatibility"""
    return _legacy_config_support.get_openrouter_models()

def is_ollama_enabled_legacy() -> bool:
    """Check if Ollama is enabled with legacy support"""
    return _legacy_config_support.is_ollama_enabled()

def is_openrouter_enabled_legacy() -> bool:
    """Check if OpenRouter is enabled with legacy support"""
    return _legacy_config_support.is_openrouter_enabled()

def migrate_model_names_in_file(file_path: str, backup: bool = True) -> bool:
    """
    Migrate model names in a Python file
    
    Args:
        file_path: Path to Python file to migrate
        backup: Whether to create backup before migration
        
    Returns:
        True if file was modified, False otherwise
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read original content
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Apply migrations
    modified_content = original_content
    changes_made = False
    
    for legacy_name, unified_name in LEGACY_MODEL_MAPPING.items():
        # Replace quoted model names
        old_pattern = f'"{legacy_name}"'
        new_pattern = f'"{unified_name}"'
        if old_pattern in modified_content:
            modified_content = modified_content.replace(old_pattern, new_pattern)
            changes_made = True
            logger.info(f"Replaced {old_pattern} with {new_pattern} in {file_path}")
        
        # Replace single-quoted model names
        old_pattern = f"'{legacy_name}'"
        new_pattern = f"'{unified_name}'"
        if old_pattern in modified_content:
            modified_content = modified_content.replace(old_pattern, new_pattern)
            changes_made = True
            logger.info(f"Replaced {old_pattern} with {new_pattern} in {file_path}")
    
    # Write changes if any were made
    if changes_made:
        # Create backup if requested
        if backup:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            logger.info(f"Created backup: {backup_path}")
        
        # Write modified content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        logger.info(f"Updated file: {file_path}")
    
    return changes_made

def register_legacy_imports():
    """Register legacy import paths for backward compatibility"""
    try:
        import sys
        import importlib.util
        
        # Create compatibility module for legacy imports
        if "src.features.llm_evaluation.config" not in sys.modules:
            # Create a dynamic module that provides legacy constants
            spec = importlib.util.spec_from_loader("src.features.llm_evaluation.config", loader=None)
            compat_module = importlib.util.module_from_spec(spec)
            
            # Add legacy constants with deprecation warnings
            def _get_ollama_models():
                emit_deprecation_warning(
                    "Importing OLLAMA_MODELS_TO_TEST from config.py is deprecated. "
                    "Use unified configuration or compatibility layer."
                )
                return get_backward_compatible_ollama_models()
            
            def _get_openrouter_models():
                emit_deprecation_warning(
                    "Importing OPENROUTER_MODELS_TO_TEST from config.py is deprecated. "
                    "Use unified configuration or compatibility layer."
                )
                return get_backward_compatible_openrouter_models()
            
            # Set as attributes (not function calls) for backward compatibility
            compat_module.OLLAMA_MODELS_TO_TEST = get_backward_compatible_ollama_models()
            compat_module.OPENROUTER_MODELS_TO_TEST = get_backward_compatible_openrouter_models()
            compat_module.ENABLE_OLLAMA = is_ollama_enabled_legacy()
            compat_module.ENABLE_OPENROUTER = is_openrouter_enabled_legacy()
            
            sys.modules["src.features.llm_evaluation.config"] = compat_module
            
    except Exception as e:
        logger.debug(f"Could not register legacy imports: {e}")

def validate_migration() -> Dict[str, Any]:
    """
    Validate migration status and compatibility
    
    Returns:
        Dictionary with validation results
    """
    results = {
        "legacy_config_found": Path(LEGACY_CONFIG_PATH).exists(),
        "unified_config_found": Path(UNIFIED_CONFIG_PATH).exists(),
        "model_mappings": len(LEGACY_MODEL_MAPPING),
        "env_variables": {},
        "recommendations": []
    }
    
    # Check environment variables
    for legacy_var, new_var in LEGACY_ENV_MAPPING.items():
        legacy_value = os.getenv(legacy_var)
        new_value = os.getenv(new_var)
        results["env_variables"][legacy_var] = {
            "legacy_set": legacy_value is not None,
            "new_set": new_value is not None,
            "values_match": legacy_value == new_value
        }
    
    # Generate recommendations
    if results["legacy_config_found"] and not results["unified_config_found"]:
        results["recommendations"].append("Run migration script to create unified configuration")
    
    if any(env["legacy_set"] and not env["new_set"] for env in results["env_variables"].values()):
        results["recommendations"].append("Update environment variables to use new names")
    
    return results

# Initialize compatibility layer on import
register_legacy_imports()

# Export main compatibility functions
__all__ = [
    "migrate_model_name",
    "migrate_model_list", 
    "get_legacy_env_var",
    "get_legacy_boolean_env",
    "get_legacy_model_list",
    "get_model_mapping",
    "resolve_model_id",
    "get_backward_compatible_ollama_models",
    "get_backward_compatible_openrouter_models",
    "is_ollama_enabled_legacy",
    "is_openrouter_enabled_legacy",
    "migrate_model_names_in_file",
    "validate_migration",
    "LegacyConfigSupport",
    "emit_deprecation_warning",
]