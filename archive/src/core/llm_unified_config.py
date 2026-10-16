"""
Unified LLM Configuration System

This module provides a unified configuration system that maps existing evaluation models
to LLM CLI format and integrates Simon Willison's naming conventions.
"""

import os
import yaml
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    name: str                           # Display name (e.g., "llama-3.3-8b")
    provider: str                       # Provider (openrouter, ollama, openai)
    model_id: str                       # Provider-specific model ID
    aliases: List[str] = field(default_factory=list)  # Short aliases
    capabilities: List[str] = field(default_factory=list)  # text, vision, code, etc.
    free: bool = True                   # Whether it's free
    enabled: bool = True                # Whether it's currently enabled
    metadata: Dict = field(default_factory=dict)  # Additional metadata
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.name:
            raise ValueError("Model name cannot be empty")
        if not self.provider:
            raise ValueError("Provider cannot be empty")
        if not self.model_id:
            raise ValueError("Model ID cannot be empty")


class UnifiedLLMConfig:
    """
    Unified configuration manager for all LLM providers
    
    This class handles loading and managing model configurations from YAML files,
    provides mapping between different naming conventions, and supports the
    LLM CLI format.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the unified configuration
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.models: Dict[str, ModelConfig] = {}
        self.aliases: Dict[str, str] = {}  # alias -> model_name mapping
        self.providers: Dict[str, Dict] = {}
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration path"""
        # Try to find the config relative to the current working directory
        possible_paths = [
            "configs/llm_model_mapping.yaml",
            "../configs/llm_model_mapping.yaml",
            "../../configs/llm_model_mapping.yaml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If not found, use the default path
        return "configs/llm_model_mapping.yaml"
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            if not os.path.exists(self.config_path):
                print(f"Warning: Configuration file {self.config_path} not found. Using defaults.")
                self._load_default_config()
                return
            
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'providers' not in config_data:
                print(f"Warning: Invalid configuration file {self.config_path}. Using defaults.")
                self._load_default_config()
                return
            
            self.providers = config_data['providers']
            self._parse_providers()
            
        except Exception as e:
            print(f"Error loading configuration: {e}. Using defaults.")
            self._load_default_config()
    
    def _load_default_config(self):
        """Load default configuration when YAML file is not available"""
        # Default configuration based on the existing config.py
        default_config = {
            'providers': {
                'openrouter': {
                    'base_url': 'https://openrouter.ai/api/v1',
                    'api_key_env': 'OPENROUTER_API_KEY',
                    'models': [
                        {
                            'name': 'llama-3.3-8b',
                            'model_id': 'meta-llama/llama-3.3-8b-instruct:free',
                            'aliases': ['llama3', 'llama3-8b'],
                            'capabilities': ['text', 'code'],
                            'free': True,
                            'enabled': True
                        },
                        {
                            'name': 'gemma-3-1b',
                            'model_id': 'google/gemma-3-1b-it:free',
                            'aliases': ['gemma1b', 'gemma-1b'],
                            'capabilities': ['text'],
                            'free': True,
                            'enabled': True
                        },
                        {
                            'name': 'llama-3.2-11b-vision',
                            'model_id': 'meta-llama/llama-3.2-11b-vision-instruct:free',
                            'aliases': ['llama3-vision', 'llama-vision'],
                            'capabilities': ['text', 'vision'],
                            'free': True,
                            'enabled': True
                        },
                        {
                            'name': 'llama-3.2-90b-vision',
                            'model_id': 'meta-llama/llama-3.2-90b-vision-instruct:free',
                            'aliases': ['llama3-vision-90b', 'llama-vision-90b'],
                            'capabilities': ['text', 'vision'],
                            'free': True,
                            'enabled': True
                        },
                        {
                            'name': 'gemma-2-9b',
                            'model_id': 'google/gemma-2-9b-it:free',
                            'aliases': ['gemma2-9b'],
                            'capabilities': ['text'],
                            'free': True,
                            'enabled': True
                        },
                        {
                            'name': 'gemma-2-27b',
                            'model_id': 'google/gemma-2-27b-it:free',
                            'aliases': ['gemma2-27b'],
                            'capabilities': ['text'],
                            'free': True,
                            'enabled': True
                        },
                        {
                            'name': 'qwen2-vl-7b',
                            'model_id': 'qwen/qwen2-vl-7b-instruct:free',
                            'aliases': ['qwen-vision-7b'],
                            'capabilities': ['text', 'vision'],
                            'free': True,
                            'enabled': True
                        },
                        {
                            'name': 'qwen2-vl-72b',
                            'model_id': 'qwen/qwen2-vl-72b-instruct:free',
                            'aliases': ['qwen-vision-72b'],
                            'capabilities': ['text', 'vision'],
                            'free': True,
                            'enabled': True
                        }
                    ]
                },
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'models': [
                        {
                            'name': 'llama3-local',
                            'model_id': 'llama3',
                            'aliases': ['llama-local', 'l3'],
                            'capabilities': ['text', 'code'],
                            'free': True,
                            'enabled': False
                        },
                        {
                            'name': 'mistral-local',
                            'model_id': 'mistral',
                            'aliases': ['mistral-local'],
                            'capabilities': ['text', 'code'],
                            'free': True,
                            'enabled': False
                        },
                        {
                            'name': 'llava-local',
                            'model_id': 'llava:latest',
                            'aliases': ['llava', 'llava-vision'],
                            'capabilities': ['text', 'vision'],
                            'free': True,
                            'enabled': False
                        }
                    ]
                }
            }
        }
        
        self.providers = default_config['providers']
        self._parse_providers()
    
    def _parse_providers(self):
        """Parse provider configurations and build model registry"""
        self.models = {}
        self.aliases = {}
        
        for provider_name, provider_config in self.providers.items():
            models = provider_config.get('models', [])
            
            for model_data in models:
                model_config = ModelConfig(
                    name=model_data['name'],
                    provider=provider_name,
                    model_id=model_data['model_id'],
                    aliases=model_data.get('aliases', []),
                    capabilities=model_data.get('capabilities', []),
                    free=model_data.get('free', True),
                    enabled=model_data.get('enabled', True),
                    metadata=model_data.get('metadata', {})
                )
                
                self.models[model_config.name] = model_config
                
                # Register aliases
                for alias in model_config.aliases:
                    self.aliases[alias] = model_config.name
    
    def get_model_by_name(self, name: str) -> Optional[ModelConfig]:
        """Get model configuration by name"""
        return self.models.get(name)
    
    def get_model_by_alias(self, alias: str) -> Optional[ModelConfig]:
        """Get model configuration by alias"""
        model_name = self.aliases.get(alias)
        if model_name:
            return self.models.get(model_name)
        return None
    
    def get_model_by_id(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by provider-specific model ID"""
        for model in self.models.values():
            if model.model_id == model_id:
                return model
        return None
    
    def resolve_model_name(self, name: str) -> Optional[ModelConfig]:
        """
        Resolve any supported format to ModelConfig
        
        Supports:
        - Direct name: "llama-3.3-8b"
        - Alias: "llama3"
        - Provider format: "openrouter/llama3"
        - Full model ID: "meta-llama/llama-3.3-8b-instruct:free"
        - LLM CLI format: "openrouter:meta-llama/llama-3.3-8b-instruct:free"
        """
        # Try direct name first
        if name in self.models:
            return self.models[name]
        
        # Try alias
        if name in self.aliases:
            return self.models[self.aliases[name]]
        
        # Try provider format: "openrouter/llama3"
        if '/' in name and ':' not in name:
            parts = name.split('/', 1)
            if len(parts) == 2:
                provider, model_name = parts
                # Try to find by alias in specific provider
                for model in self.models.values():
                    if model.provider == provider and (model.name == model_name or model_name in model.aliases):
                        return model
        
        # Try LLM CLI format: "openrouter:model-id"
        if ':' in name:
            parts = name.split(':', 1)
            if len(parts) == 2:
                provider, model_id = parts
                # Try to find by model_id in specific provider
                for model in self.models.values():
                    if model.provider == provider and model.model_id == model_id:
                        return model
        
        # Try full model ID
        model = self.get_model_by_id(name)
        if model:
            return model
        
        return None
    
    def get_llm_cli_format(self, name: str) -> Optional[str]:
        """
        Convert model name to LLM CLI format
        
        Args:
            name: Model name, alias, or ID
            
        Returns:
            LLM CLI format string (e.g., "openrouter:meta-llama/llama-3.3-8b-instruct:free")
        """
        model = self.resolve_model_name(name)
        if model:
            return f"{model.provider}:{model.model_id}"
        return None
    
    def get_provider_format(self, name: str) -> Optional[str]:
        """
        Convert model name to provider-specific format
        
        Args:
            name: Model name, alias, or ID
            
        Returns:
            Provider-specific format string (e.g., "meta-llama/llama-3.3-8b-instruct:free")
        """
        model = self.resolve_model_name(name)
        if model:
            return model.model_id
        return None
    
    def list_models(self, provider: str = None, capability: str = None, free_only: bool = False, enabled_only: bool = True) -> List[ModelConfig]:
        """
        List models with optional filtering
        
        Args:
            provider: Filter by provider (openrouter, ollama, etc.)
            capability: Filter by capability (text, vision, code, etc.)
            free_only: Only include free models
            enabled_only: Only include enabled models
            
        Returns:
            List of matching ModelConfig objects
        """
        models = []
        
        for model in self.models.values():
            # Apply filters
            if provider and model.provider != provider:
                continue
            if capability and capability not in model.capabilities:
                continue
            if free_only and not model.free:
                continue
            if enabled_only and not model.enabled:
                continue
            
            models.append(model)
        
        return models
    
    def list_providers(self) -> List[str]:
        """List all available providers"""
        return list(self.providers.keys())
    
    def get_provider_config(self, provider: str) -> Optional[Dict]:
        """Get provider configuration"""
        return self.providers.get(provider)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider"""
        provider_config = self.get_provider_config(provider)
        if provider_config and 'api_key_env' in provider_config:
            return os.getenv(provider_config['api_key_env'])
        return None
    
    def validate_model_availability(self, name: str) -> bool:
        """
        Validate if a model is available and configured properly
        
        Args:
            name: Model name, alias, or ID
            
        Returns:
            True if model is available and properly configured
        """
        model = self.resolve_model_name(name)
        if not model:
            return False
        
        if not model.enabled:
            return False
        
        # Check if API key is available for the provider (if required)
        if model.provider == 'openrouter':
            api_key = self.get_api_key('openrouter')
            if not api_key:
                return False
        
        return True
    
    def get_backward_compatible_lists(self) -> Dict[str, List[str]]:
        """
        Get backward compatible model lists for existing configuration
        
        Returns:
            Dictionary with model lists in the old format
        """
        openrouter_models = []
        ollama_models = []
        vision_models = []
        
        for model in self.models.values():
            if model.provider == 'openrouter':
                openrouter_models.append(model.model_id)
                if 'vision' in model.capabilities:
                    vision_models.append(model.model_id)
            elif model.provider == 'ollama':
                ollama_models.append(model.model_id)
        
        return {
            'openrouter': openrouter_models,
            'ollama': ollama_models,
            'vision': vision_models
        }


# Global instance for backward compatibility
_unified_config = None

def get_unified_config() -> UnifiedLLMConfig:
    """Get the global unified configuration instance"""
    global _unified_config
    if _unified_config is None:
        _unified_config = UnifiedLLMConfig()
    return _unified_config

def reset_unified_config():
    """Reset the global unified configuration instance"""
    global _unified_config
    _unified_config = None