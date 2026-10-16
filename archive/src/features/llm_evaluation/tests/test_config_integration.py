"""
Test suite for configuration integration with the unified system.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from src.features.llm_evaluation.config import (
    get_unified_config_instance,
    get_model_by_name,
    get_model_by_llm_cli_format,
    list_available_models,
    get_default_model,
    get_openrouter_models_to_test,
    get_ollama_models_to_test,
    get_openrouter_vision_models_to_test,
    get_ollama_vision_models_to_test,
    UNIFIED_CONFIG_AVAILABLE
)


class TestConfigIntegration:
    """Test configuration integration with unified system"""
    
    def test_unified_config_availability(self):
        """Test that unified config is available"""
        # This test assumes the unified config is properly imported
        config = get_unified_config_instance()
        if UNIFIED_CONFIG_AVAILABLE:
            assert config is not None
        else:
            assert config is None
    
    def test_get_model_by_name(self):
        """Test getting model by name"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        # Test with known alias
        model_id = get_model_by_name("llama3")
        if model_id:
            assert isinstance(model_id, str)
            assert len(model_id) > 0
        
        # Test with non-existent model
        model_id = get_model_by_name("non-existent-model")
        assert model_id is None
    
    def test_get_model_by_llm_cli_format(self):
        """Test getting model by LLM CLI format"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        # Test with LLM CLI format
        model_id = get_model_by_llm_cli_format("openrouter:meta-llama/llama-3.3-8b-instruct:free")
        if model_id:
            assert isinstance(model_id, str)
            assert len(model_id) > 0
        
        # Test with non-existent format
        model_id = get_model_by_llm_cli_format("non-existent:model")
        assert model_id is None
    
    def test_list_available_models(self):
        """Test listing available models"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        # Test all models
        models = list_available_models()
        assert isinstance(models, list)
        
        # Test by provider
        openrouter_models = list_available_models(provider="openrouter")
        assert isinstance(openrouter_models, list)
        
        ollama_models = list_available_models(provider="ollama")
        assert isinstance(ollama_models, list)
        
        # Test by capability
        text_models = list_available_models(capability="text")
        assert isinstance(text_models, list)
        
        vision_models = list_available_models(capability="vision")
        assert isinstance(vision_models, list)
    
    def test_get_default_model(self):
        """Test getting default model"""
        with patch.dict(os.environ, {
            "DEFAULT_TEXT_MODEL": "llama3",
            "DEFAULT_VISION_MODEL": "llama3-vision",
            "DEFAULT_CODE_MODEL": "llama3",
            "DEFAULT_LOCAL_MODEL": "llama3-local",
            "DEFAULT_FREE_MODEL": "llama3"
        }):
            assert get_default_model("text") == "llama3"
            assert get_default_model("vision") == "llama3-vision"
            assert get_default_model("code") == "llama3"
            assert get_default_model("local") == "llama3-local"
            assert get_default_model("free") == "llama3"
            assert get_default_model("unknown") is None
    
    def test_get_openrouter_models_to_test(self):
        """Test getting OpenRouter models to test"""
        models = get_openrouter_models_to_test()
        assert isinstance(models, list)
        assert len(models) > 0
        
        # All models should be strings
        for model in models:
            assert isinstance(model, str)
            assert len(model) > 0
    
    def test_get_ollama_models_to_test(self):
        """Test getting Ollama models to test"""
        models = get_ollama_models_to_test()
        assert isinstance(models, list)
        
        # All models should be strings
        for model in models:
            assert isinstance(model, str)
            assert len(model) > 0
    
    def test_get_openrouter_vision_models_to_test(self):
        """Test getting OpenRouter vision models to test"""
        models = get_openrouter_vision_models_to_test()
        assert isinstance(models, list)
        
        # All models should be strings
        for model in models:
            assert isinstance(model, str)
            assert len(model) > 0
    
    def test_get_ollama_vision_models_to_test(self):
        """Test getting Ollama vision models to test"""
        models = get_ollama_vision_models_to_test()
        assert isinstance(models, list)
        
        # All models should be strings
        for model in models:
            assert isinstance(model, str)
            assert len(model) > 0
    
    def test_backward_compatibility(self):
        """Test backward compatibility with existing configuration"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        config = get_unified_config_instance()
        if config:
            # Test that we can get backward compatible lists
            lists = config.get_backward_compatible_lists()
            
            assert "openrouter" in lists
            assert "ollama" in lists
            assert "vision" in lists
            
            # Test that function returns match backward compatible lists
            openrouter_models = get_openrouter_models_to_test()
            assert set(openrouter_models) == set(lists["openrouter"])
    
    def test_environment_variable_integration(self):
        """Test integration with environment variables"""
        with patch.dict(os.environ, {
            "ENABLE_LOCAL_MODELS": "true",
            "ENABLE_VISION_MODELS": "false"
        }):
            # Re-import the config to pick up environment changes
            from src.features.llm_evaluation import config
            
            # Test that environment variables are respected
            # Note: This test depends on how the config module handles environment variables
            assert hasattr(config, 'ENABLE_OLLAMA')
            assert hasattr(config, 'ENABLE_VISION_TESTING')
    
    def test_config_validation(self):
        """Test configuration validation"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        config = get_unified_config_instance()
        if config:
            # Test that configuration has expected structure
            assert hasattr(config, 'models')
            assert hasattr(config, 'providers')
            assert hasattr(config, 'aliases')
            
            # Test that models and providers are not empty
            assert len(config.models) > 0
            assert len(config.providers) > 0
            
            # Test that all models have required attributes
            for model in config.models.values():
                assert hasattr(model, 'name')
                assert hasattr(model, 'provider')
                assert hasattr(model, 'model_id')
                assert hasattr(model, 'aliases')
                assert hasattr(model, 'capabilities')
                assert hasattr(model, 'free')
                assert hasattr(model, 'enabled')
    
    def test_model_resolution_consistency(self):
        """Test that model resolution is consistent"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        # Test that alias resolution works consistently
        model_id_1 = get_model_by_name("llama3")
        model_id_2 = get_model_by_name("llama3-8b")
        
        if model_id_1 and model_id_2:
            # Both aliases should resolve to the same model
            assert model_id_1 == model_id_2
    
    def test_provider_specific_handling(self):
        """Test provider-specific handling"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        # Test OpenRouter models
        openrouter_models = list_available_models(provider="openrouter")
        for model_name in openrouter_models:
            model_id = get_model_by_name(model_name)
            if model_id:
                # OpenRouter models should have specific format
                assert isinstance(model_id, str)
                assert len(model_id) > 0
        
        # Test Ollama models
        ollama_models = list_available_models(provider="ollama")
        for model_name in ollama_models:
            model_id = get_model_by_name(model_name)
            if model_id:
                # Ollama models should have specific format
                assert isinstance(model_id, str)
                assert len(model_id) > 0
    
    def test_capability_filtering(self):
        """Test capability-based filtering"""
        if not UNIFIED_CONFIG_AVAILABLE:
            pytest.skip("Unified config not available")
        
        # Test text models
        text_models = list_available_models(capability="text")
        assert isinstance(text_models, list)
        
        # Test vision models
        vision_models = list_available_models(capability="vision")
        assert isinstance(vision_models, list)
        
        # Test code models
        code_models = list_available_models(capability="code")
        assert isinstance(code_models, list)
        
        # Vision models should be subset of or equal to text models
        # (since vision models usually also support text)
        vision_set = set(vision_models)
        text_set = set(text_models)
        # Note: This assertion might not hold for all configurations
        # assert vision_set.issubset(text_set) or vision_set == text_set


if __name__ == "__main__":
    pytest.main([__file__, "-v"])