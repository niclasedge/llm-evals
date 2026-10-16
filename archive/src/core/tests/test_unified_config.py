"""
Test suite for the unified LLM configuration system.
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.core.llm_unified_config import (
    ModelConfig, UnifiedLLMConfig, get_unified_config, reset_unified_config
)
from src.core.model_migration import ModelMigration, migrate_legacy_config, validate_unified_config


class TestModelConfig:
    """Test ModelConfig class"""
    
    def test_model_config_creation(self):
        """Test basic ModelConfig creation"""
        config = ModelConfig(
            name="test-model",
            provider="openrouter",
            model_id="test/model:free",
            aliases=["test", "tm"],
            capabilities=["text", "code"],
            free=True,
            enabled=True
        )
        
        assert config.name == "test-model"
        assert config.provider == "openrouter"
        assert config.model_id == "test/model:free"
        assert config.aliases == ["test", "tm"]
        assert config.capabilities == ["text", "code"]
        assert config.free is True
        assert config.enabled is True
    
    def test_model_config_validation(self):
        """Test ModelConfig validation"""
        # Test empty name
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            ModelConfig(name="", provider="openrouter", model_id="test/model:free")
        
        # Test empty provider
        with pytest.raises(ValueError, match="Provider cannot be empty"):
            ModelConfig(name="test", provider="", model_id="test/model:free")
        
        # Test empty model_id
        with pytest.raises(ValueError, match="Model ID cannot be empty"):
            ModelConfig(name="test", provider="openrouter", model_id="")
    
    def test_model_config_defaults(self):
        """Test ModelConfig default values"""
        config = ModelConfig(
            name="test-model",
            provider="openrouter",
            model_id="test/model:free"
        )
        
        assert config.aliases == []
        assert config.capabilities == []
        assert config.free is True
        assert config.enabled is True
        assert config.metadata == {}


class TestUnifiedLLMConfig:
    """Test UnifiedLLMConfig class"""
    
    def setup_method(self):
        """Setup test method"""
        # Create a temporary YAML config file
        self.test_config = {
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
                        }
                    ]
                }
            }
        }
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.test_config, self.temp_file)
        self.temp_file.close()
        
        # Create config instance
        self.config = UnifiedLLMConfig(self.temp_file.name)
    
    def teardown_method(self):
        """Teardown test method"""
        os.unlink(self.temp_file.name)
    
    def test_config_loading(self):
        """Test configuration loading"""
        assert len(self.config.models) == 3
        assert len(self.config.providers) == 2
        assert len(self.config.aliases) == 6  # llama3, llama3-8b, gemma1b, gemma-1b, llama-local, l3
    
    def test_get_model_by_name(self):
        """Test getting model by name"""
        model = self.config.get_model_by_name("llama-3.3-8b")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        assert model.provider == "openrouter"
        assert model.model_id == "meta-llama/llama-3.3-8b-instruct:free"
        
        # Test non-existent model
        model = self.config.get_model_by_name("non-existent")
        assert model is None
    
    def test_get_model_by_alias(self):
        """Test getting model by alias"""
        model = self.config.get_model_by_alias("llama3")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        
        model = self.config.get_model_by_alias("gemma1b")
        assert model is not None
        assert model.name == "gemma-3-1b"
        
        # Test non-existent alias
        model = self.config.get_model_by_alias("non-existent")
        assert model is None
    
    def test_get_model_by_id(self):
        """Test getting model by ID"""
        model = self.config.get_model_by_id("meta-llama/llama-3.3-8b-instruct:free")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        
        # Test non-existent ID
        model = self.config.get_model_by_id("non-existent")
        assert model is None
    
    def test_resolve_model_name(self):
        """Test model name resolution"""
        # Test direct name
        model = self.config.resolve_model_name("llama-3.3-8b")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        
        # Test alias
        model = self.config.resolve_model_name("llama3")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        
        # Test provider format
        model = self.config.resolve_model_name("openrouter/llama3")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        
        # Test full model ID
        model = self.config.resolve_model_name("meta-llama/llama-3.3-8b-instruct:free")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        
        # Test LLM CLI format
        model = self.config.resolve_model_name("openrouter:meta-llama/llama-3.3-8b-instruct:free")
        assert model is not None
        assert model.name == "llama-3.3-8b"
        
        # Test non-existent
        model = self.config.resolve_model_name("non-existent")
        assert model is None
    
    def test_get_llm_cli_format(self):
        """Test LLM CLI format conversion"""
        # Test with alias
        result = self.config.get_llm_cli_format("llama3")
        assert result == "openrouter:meta-llama/llama-3.3-8b-instruct:free"
        
        # Test with model name
        result = self.config.get_llm_cli_format("gemma-3-1b")
        assert result == "openrouter:google/gemma-3-1b-it:free"
        
        # Test with ollama model
        result = self.config.get_llm_cli_format("llama3-local")
        assert result == "ollama:llama3"
        
        # Test non-existent
        result = self.config.get_llm_cli_format("non-existent")
        assert result is None
    
    def test_get_provider_format(self):
        """Test provider format conversion"""
        # Test with alias
        result = self.config.get_provider_format("llama3")
        assert result == "meta-llama/llama-3.3-8b-instruct:free"
        
        # Test with model name
        result = self.config.get_provider_format("gemma-3-1b")
        assert result == "google/gemma-3-1b-it:free"
        
        # Test non-existent
        result = self.config.get_provider_format("non-existent")
        assert result is None
    
    def test_list_models(self):
        """Test listing models with filtering"""
        # Test all models
        models = self.config.list_models()
        assert len(models) == 2  # ollama model is disabled by default
        
        # Test by provider
        openrouter_models = self.config.list_models(provider="openrouter")
        assert len(openrouter_models) == 2
        
        ollama_models = self.config.list_models(provider="ollama", enabled_only=False)
        assert len(ollama_models) == 1
        
        # Test by capability
        text_models = self.config.list_models(capability="text", enabled_only=False)
        assert len(text_models) == 3
        
        code_models = self.config.list_models(capability="code", enabled_only=False)
        assert len(code_models) == 2
        
        # Test enabled only
        enabled_models = self.config.list_models(enabled_only=True)
        assert len(enabled_models) == 2  # ollama model is disabled
        
        # Test free only
        free_models = self.config.list_models(free_only=True, enabled_only=False)
        assert len(free_models) == 3
    
    def test_list_providers(self):
        """Test listing providers"""
        providers = self.config.list_providers()
        assert len(providers) == 2
        assert "openrouter" in providers
        assert "ollama" in providers
    
    def test_get_provider_config(self):
        """Test getting provider configuration"""
        config = self.config.get_provider_config("openrouter")
        assert config is not None
        assert config["base_url"] == "https://openrouter.ai/api/v1"
        assert config["api_key_env"] == "OPENROUTER_API_KEY"
        
        # Test non-existent provider
        config = self.config.get_provider_config("non-existent")
        assert config is None
    
    def test_get_api_key(self):
        """Test getting API key"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            api_key = self.config.get_api_key("openrouter")
            assert api_key == "test-key"
        
        # Test non-existent key
        api_key = self.config.get_api_key("non-existent")
        assert api_key is None
    
    def test_validate_model_availability(self):
        """Test model availability validation"""
        # Test enabled model
        is_available = self.config.validate_model_availability("llama3")
        assert is_available is False  # No API key set
        
        # Test disabled model
        is_available = self.config.validate_model_availability("llama3-local")
        assert is_available is False  # Disabled
        
        # Test non-existent model
        is_available = self.config.validate_model_availability("non-existent")
        assert is_available is False
        
        # Test with API key
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            is_available = self.config.validate_model_availability("llama3")
            assert is_available is True
    
    def test_get_backward_compatible_lists(self):
        """Test backward compatible lists"""
        lists = self.config.get_backward_compatible_lists()
        
        assert "openrouter" in lists
        assert "ollama" in lists
        assert "vision" in lists
        
        assert len(lists["openrouter"]) == 2
        assert len(lists["ollama"]) == 1
        assert len(lists["vision"]) == 0  # No vision models in test config
        
        assert "meta-llama/llama-3.3-8b-instruct:free" in lists["openrouter"]
        assert "google/gemma-3-1b-it:free" in lists["openrouter"]
        assert "llama3" in lists["ollama"]
    
    def test_config_file_not_found(self):
        """Test behavior when config file doesn't exist"""
        config = UnifiedLLMConfig("/non/existent/path.yaml")
        
        # Should use default configuration
        assert len(config.models) > 0
        assert len(config.providers) > 0
    
    def test_invalid_yaml_file(self):
        """Test behavior with invalid YAML file"""
        # Create invalid YAML file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        temp_file.write("invalid: yaml: content: [")
        temp_file.close()
        
        try:
            config = UnifiedLLMConfig(temp_file.name)
            # Should use default configuration
            assert len(config.models) > 0
            assert len(config.providers) > 0
        finally:
            os.unlink(temp_file.name)
    
    def test_empty_config_file(self):
        """Test behavior with empty config file"""
        # Create empty file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        temp_file.write("")
        temp_file.close()
        
        try:
            config = UnifiedLLMConfig(temp_file.name)
            # Should use default configuration
            assert len(config.models) > 0
            assert len(config.providers) > 0
        finally:
            os.unlink(temp_file.name)


class TestModelMigration:
    """Test ModelMigration class"""
    
    def setup_method(self):
        """Setup test method"""
        # Create a temporary YAML config file
        test_config = {
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
                        }
                    ]
                }
            }
        }
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(test_config, self.temp_file)
        self.temp_file.close()
        
        # Create migration instance
        self.migration = ModelMigration(self.temp_file.name)
    
    def teardown_method(self):
        """Teardown test method"""
        os.unlink(self.temp_file.name)
    
    def test_migrate_openrouter_models(self):
        """Test OpenRouter model migration"""
        legacy_models = [
            "meta-llama/llama-3.3-8b-instruct:free",
            "non-existent-model"
        ]
        
        report = self.migration.migrate_openrouter_models(legacy_models)
        
        assert report.success is True  # Success despite warnings
        assert len(report.migrated_models) == 1
        assert len(report.failed_models) == 1
        assert "meta-llama/llama-3.3-8b-instruct:free -> llama-3.3-8b" in report.migrated_models
        assert "non-existent-model" in report.failed_models
    
    def test_migrate_ollama_models(self):
        """Test Ollama model migration"""
        legacy_models = [
            "llama3",
            "non-existent-model"
        ]
        
        report = self.migration.migrate_ollama_models(legacy_models)
        
        assert report.success is True  # Success despite warnings
        assert len(report.migrated_models) == 1
        assert len(report.failed_models) == 1
        assert "llama3 -> llama3-local" in report.migrated_models
        assert "non-existent-model" in report.failed_models
    
    def test_validate_model_availability(self):
        """Test model availability validation"""
        models = ["llama3", "llama3-local", "non-existent"]
        
        availability = self.migration.validate_model_availability(models)
        
        assert availability["llama3"] is False  # No API key
        assert availability["llama3-local"] is False  # Disabled
        assert availability["non-existent"] is False  # Non-existent
    
    def test_generate_migration_report(self):
        """Test migration report generation"""
        report = self.migration.generate_migration_report()
        
        assert report.success is True
        assert len(report.migrated_models) > 0
        assert len(report.warnings) > 0
    
    def test_validate_configuration(self):
        """Test configuration validation"""
        report = self.migration.validate_configuration()
        
        assert report.success is True
        assert len(report.warnings) > 0
    
    def test_export_legacy_format(self):
        """Test legacy format export"""
        legacy_format = self.migration.export_legacy_format()
        
        assert "openrouter" in legacy_format
        assert "ollama" in legacy_format
        assert "vision" in legacy_format
        
        assert len(legacy_format["openrouter"]) == 1
        assert len(legacy_format["ollama"]) == 1
        assert "meta-llama/llama-3.3-8b-instruct:free" in legacy_format["openrouter"]
        assert "llama3" in legacy_format["ollama"]


class TestGlobalFunctions:
    """Test global utility functions"""
    
    def test_get_unified_config(self):
        """Test global config instance"""
        config1 = get_unified_config()
        config2 = get_unified_config()
        
        # Should return same instance
        assert config1 is config2
    
    def test_reset_unified_config(self):
        """Test resetting global config"""
        config1 = get_unified_config()
        reset_unified_config()
        config2 = get_unified_config()
        
        # Should return new instance
        assert config1 is not config2
    
    def test_migrate_legacy_config(self):
        """Test legacy config migration function"""
        report = migrate_legacy_config()
        
        assert report is not None
        assert hasattr(report, 'success')
        assert hasattr(report, 'migrated_models')
        assert hasattr(report, 'failed_models')
    
    def test_validate_unified_config(self):
        """Test unified config validation function"""
        report = validate_unified_config()
        
        assert report is not None
        assert hasattr(report, 'success')
        assert hasattr(report, 'warnings')
        assert hasattr(report, 'errors')


class TestIntegration:
    """Integration tests for the unified configuration system"""
    
    def test_config_integration_with_environment(self):
        """Test configuration integration with environment variables"""
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "test-key",
            "DEFAULT_TEXT_MODEL": "llama3",
            "DEFAULT_VISION_MODEL": "llama3-vision"
        }):
            config = UnifiedLLMConfig()
            
            # Test API key retrieval
            api_key = config.get_api_key("openrouter")
            assert api_key == "test-key"
            
            # Test model availability with API key
            is_available = config.validate_model_availability("llama3")
            # Should be True if the model exists and is enabled
            assert isinstance(is_available, bool)
    
    def test_config_backward_compatibility(self):
        """Test backward compatibility with existing configuration"""
        config = UnifiedLLMConfig()
        
        # Test that we can get backward compatible lists
        lists = config.get_backward_compatible_lists()
        
        assert "openrouter" in lists
        assert "ollama" in lists
        assert "vision" in lists
        
        # Test that lists contain expected models
        assert isinstance(lists["openrouter"], list)
        assert isinstance(lists["ollama"], list)
        assert isinstance(lists["vision"], list)
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test with non-existent config path
        config = UnifiedLLMConfig("/non/existent/path.yaml")
        
        # Should not crash and should use defaults
        assert len(config.models) > 0
        assert len(config.providers) > 0
        
        # Test with None config path
        config = UnifiedLLMConfig(None)
        
        # Should not crash and should use defaults
        assert len(config.models) > 0
        assert len(config.providers) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])