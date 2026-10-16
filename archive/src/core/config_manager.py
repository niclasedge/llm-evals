"""
Enhanced Configuration Management System for LLM Evaluation Platform
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class ConfigFormat(Enum):
    """Supported configuration formats"""
    JSON = "json"
    YAML = "yaml"
    PYTHON = "py"


@dataclass
class EvaluationConfig:
    """Configuration for evaluation settings"""
    enable_ollama: bool = False
    enable_openrouter: bool = True
    ollama_base_url: str = "http://localhost:11434"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: Optional[str] = None
    ollama_models: List[str] = field(default_factory=list)
    openrouter_models: List[str] = field(default_factory=list)
    default_system_prompt: str = "You are a helpful assistant."
    max_concurrent_evaluations: int = 3
    timeout_seconds: int = 120
    retry_attempts: int = 3


@dataclass
class MetricsConfig:
    """Configuration for evaluation metrics"""
    enabled_metrics: List[str] = field(default_factory=lambda: [
        "relevance", "accuracy", "coherence", "similarity"
    ])
    similarity_threshold: float = 0.7
    accuracy_threshold: float = 0.8
    coherence_threshold: float = 0.6
    custom_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    """Configuration for dashboard settings"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 8080
    auto_refresh: bool = True
    refresh_interval: int = 30
    max_results_display: int = 100
    theme: str = "light"


@dataclass
class DatabaseConfig:
    """Configuration for database settings"""
    database_type: str = "sqlite"
    database_path: str = "data/evaluation_results.db"
    backup_enabled: bool = True
    backup_interval: int = 3600
    max_connections: int = 10


@dataclass
class LLMEvaluationConfig:
    """Main configuration class for LLM evaluation system"""
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    def __post_init__(self):
        """Post-initialization setup"""
        if self.evaluation.openrouter_api_key is None:
            self.evaluation.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")


class ConfigManager:
    """Enhanced configuration manager with validation and schema support"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = LLMEvaluationConfig()
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration path"""
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "llm_evaluation.yaml")
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            self._create_default_config()
            return
        
        try:
            format_type = self._detect_format(self.config_path)
            
            if format_type == ConfigFormat.YAML:
                self._load_yaml_config()
            elif format_type == ConfigFormat.JSON:
                self._load_json_config()
            elif format_type == ConfigFormat.PYTHON:
                self._load_python_config()
            else:
                raise ValueError(f"Unsupported configuration format: {format_type}")
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration")
    
    def _detect_format(self, path: str) -> ConfigFormat:
        """Detect configuration file format"""
        ext = Path(path).suffix.lower()
        if ext in ['.yaml', '.yml']:
            return ConfigFormat.YAML
        elif ext == '.json':
            return ConfigFormat.JSON
        elif ext == '.py':
            return ConfigFormat.PYTHON
        else:
            raise ValueError(f"Unknown configuration format: {ext}")
    
    def _load_yaml_config(self) -> None:
        """Load YAML configuration"""
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
        self._update_config_from_dict(data)
    
    def _load_json_config(self) -> None:
        """Load JSON configuration"""
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        self._update_config_from_dict(data)
    
    def _load_python_config(self) -> None:
        """Load Python configuration (legacy compatibility)"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", self.config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        # Convert legacy config format
        self.config.evaluation.enable_ollama = getattr(config_module, 'ENABLE_OLLAMA', False)
        self.config.evaluation.enable_openrouter = getattr(config_module, 'ENABLE_OPENROUTER', True)
        self.config.evaluation.ollama_base_url = getattr(config_module, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.config.evaluation.openrouter_base_url = getattr(config_module, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.config.evaluation.openrouter_api_key = getattr(config_module, 'OPENROUTER_API_KEY', None)
        self.config.evaluation.ollama_models = getattr(config_module, 'OLLAMA_MODELS_TO_TEST', [])
        self.config.evaluation.openrouter_models = getattr(config_module, 'OPENROUTER_MODELS_TO_TEST', [])
        self.config.evaluation.default_system_prompt = getattr(config_module, 'DEFAULT_SYSTEM_PROMPT', 'You are a helpful assistant.')
    
    def _update_config_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        if 'evaluation' in data:
            eval_data = data['evaluation']
            for key, value in eval_data.items():
                if hasattr(self.config.evaluation, key):
                    setattr(self.config.evaluation, key, value)
        
        if 'metrics' in data:
            metrics_data = data['metrics']
            for key, value in metrics_data.items():
                if hasattr(self.config.metrics, key):
                    setattr(self.config.metrics, key, value)
        
        if 'dashboard' in data:
            dashboard_data = data['dashboard']
            for key, value in dashboard_data.items():
                if hasattr(self.config.dashboard, key):
                    setattr(self.config.dashboard, key, value)
        
        if 'database' in data:
            db_data = data['database']
            for key, value in db_data.items():
                if hasattr(self.config.database, key):
                    setattr(self.config.database, key, value)
    
    def _create_default_config(self) -> None:
        """Create default configuration file"""
        default_config = {
            'evaluation': {
                'enable_ollama': False,
                'enable_openrouter': True,
                'ollama_base_url': 'http://localhost:11434',
                'openrouter_base_url': 'https://openrouter.ai/api/v1',
                'openrouter_api_key': None,
                'ollama_models': ['llama3'],
                'openrouter_models': [
                    'meta-llama/llama-3.3-8b-instruct:free',
                    'google/gemma-3-1b-it:free'
                ],
                'default_system_prompt': 'You are a helpful assistant.',
                'max_concurrent_evaluations': 3,
                'timeout_seconds': 120,
                'retry_attempts': 3
            },
            'metrics': {
                'enabled_metrics': ['relevance', 'accuracy', 'coherence', 'similarity'],
                'similarity_threshold': 0.7,
                'accuracy_threshold': 0.8,
                'coherence_threshold': 0.6,
                'custom_metrics': {}
            },
            'dashboard': {
                'enabled': True,
                'host': 'localhost',
                'port': 8080,
                'auto_refresh': True,
                'refresh_interval': 30,
                'max_results_display': 100,
                'theme': 'light'
            },
            'database': {
                'database_type': 'sqlite',
                'database_path': 'data/evaluation_results.db',
                'backup_enabled': True,
                'backup_interval': 3600,
                'max_connections': 10
            }
        }
        
        # Create config directory if it doesn't exist
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        config_dict = {
            'evaluation': {
                'enable_ollama': self.config.evaluation.enable_ollama,
                'enable_openrouter': self.config.evaluation.enable_openrouter,
                'ollama_base_url': self.config.evaluation.ollama_base_url,
                'openrouter_base_url': self.config.evaluation.openrouter_base_url,
                'openrouter_api_key': self.config.evaluation.openrouter_api_key,
                'ollama_models': self.config.evaluation.ollama_models,
                'openrouter_models': self.config.evaluation.openrouter_models,
                'default_system_prompt': self.config.evaluation.default_system_prompt,
                'max_concurrent_evaluations': self.config.evaluation.max_concurrent_evaluations,
                'timeout_seconds': self.config.evaluation.timeout_seconds,
                'retry_attempts': self.config.evaluation.retry_attempts
            },
            'metrics': {
                'enabled_metrics': self.config.metrics.enabled_metrics,
                'similarity_threshold': self.config.metrics.similarity_threshold,
                'accuracy_threshold': self.config.metrics.accuracy_threshold,
                'coherence_threshold': self.config.metrics.coherence_threshold,
                'custom_metrics': self.config.metrics.custom_metrics
            },
            'dashboard': {
                'enabled': self.config.dashboard.enabled,
                'host': self.config.dashboard.host,
                'port': self.config.dashboard.port,
                'auto_refresh': self.config.dashboard.auto_refresh,
                'refresh_interval': self.config.dashboard.refresh_interval,
                'max_results_display': self.config.dashboard.max_results_display,
                'theme': self.config.dashboard.theme
            },
            'database': {
                'database_type': self.config.database.database_type,
                'database_path': self.config.database.database_path,
                'backup_enabled': self.config.database.backup_enabled,
                'backup_interval': self.config.database.backup_interval,
                'max_connections': self.config.database.max_connections
            }
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def validate_config(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Check required fields
        if self.config.evaluation.enable_openrouter and not self.config.evaluation.openrouter_api_key:
            errors.append("OpenRouter API key is required when OpenRouter is enabled")
        
        if not self.config.evaluation.ollama_models and not self.config.evaluation.openrouter_models:
            errors.append("At least one model must be configured")
        
        # Check thresholds
        if not (0 <= self.config.metrics.similarity_threshold <= 1):
            errors.append("Similarity threshold must be between 0 and 1")
        
        if not (0 <= self.config.metrics.accuracy_threshold <= 1):
            errors.append("Accuracy threshold must be between 0 and 1")
        
        if not (0 <= self.config.metrics.coherence_threshold <= 1):
            errors.append("Coherence threshold must be between 0 and 1")
        
        # Check port range
        if not (1024 <= self.config.dashboard.port <= 65535):
            errors.append("Dashboard port must be between 1024 and 65535")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def get_config(self) -> LLMEvaluationConfig:
        """Get current configuration"""
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        self._update_config_from_dict(updates)
        self.save_config()
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        self._load_config()


# Global configuration instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> LLMEvaluationConfig:
    """Get current configuration"""
    return get_config_manager().get_config()