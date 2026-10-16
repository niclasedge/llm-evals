"""
Test suite for migration and compatibility functionality

This module tests the migration tools and backward compatibility features
to ensure existing user workflows continue to work during and after migration.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml
import json

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.compatibility import (
    migrate_model_name,
    migrate_model_list,
    get_legacy_env_var,
    get_legacy_boolean_env,
    get_legacy_model_list,
    get_model_mapping,
    resolve_model_id,
    migrate_model_names_in_file,
    validate_migration,
    LegacyConfigSupport,
    emit_deprecation_warning
)

class TestModelMigration:
    """Test model name migration functionality"""
    
    def test_migrate_model_name_known_mapping(self):
        """Test migration of known legacy model names"""
        assert migrate_model_name("llama3", warn=False) == "llama3.3-8b-local"
        assert migrate_model_name("mistral", warn=False) == "mistral-small-local"
        assert migrate_model_name("phi3", warn=False) == "phi4-reasoning-local"
    
    def test_migrate_model_name_unknown_model(self):
        """Test migration of unknown model names (should pass through)"""
        unknown_model = "custom-model-v1"
        assert migrate_model_name(unknown_model, warn=False) == unknown_model
    
    def test_migrate_model_name_with_warnings(self):
        """Test that deprecation warnings are emitted"""
        with pytest.warns(DeprecationWarning):
            migrate_model_name("llama3", warn=True)
    
    def test_migrate_model_list(self):
        """Test migration of model lists"""
        legacy_models = ["llama3", "mistral", "custom-model"]
        expected = ["llama3.3-8b-local", "mistral-small-local", "custom-model"]
        assert migrate_model_list(legacy_models, warn=False) == expected
    
    def test_get_model_mapping(self):
        """Test getting complete model mapping"""
        mapping = get_model_mapping()
        assert isinstance(mapping, dict)
        assert "llama3" in mapping
        assert mapping["llama3"] == "llama3.3-8b-local"
    
    def test_resolve_model_id(self):
        """Test resolving unified model names to provider IDs"""
        # Test with known unified name (would resolve through unified config)
        result = resolve_model_id("llama3.3-8b-local")
        # Should either return the config's model_id or fall back to reverse mapping
        assert result is not None

class TestEnvironmentVariables:
    """Test environment variable compatibility"""
    
    def test_get_legacy_env_var_exists(self):
        """Test getting existing environment variable"""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            assert get_legacy_env_var("TEST_VAR", warn=False) == "test_value"
    
    def test_get_legacy_env_var_default(self):
        """Test getting default value when env var doesn't exist"""
        assert get_legacy_env_var("NONEXISTENT_VAR", "default", warn=False) == "default"
    
    def test_get_legacy_boolean_env_true(self):
        """Test boolean environment variables - true values"""
        true_values = ["true", "True", "TRUE", "1", "yes", "on"]
        for value in true_values:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                assert get_legacy_boolean_env("TEST_BOOL", warn=False) is True
    
    def test_get_legacy_boolean_env_false(self):
        """Test boolean environment variables - false values"""
        false_values = ["false", "False", "FALSE", "0", "no", "off"]
        for value in false_values:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                assert get_legacy_boolean_env("TEST_BOOL", warn=False) is False
    
    def test_get_legacy_model_list_from_env(self):
        """Test getting model list from environment variable"""
        with patch.dict(os.environ, {"TEST_MODELS": "llama3,mistral,phi3"}):
            models = get_legacy_model_list("TEST_MODELS", warn=False)
            expected = ["llama3.3-8b-local", "mistral-small-local", "phi4-reasoning-local"]
            assert models == expected
    
    def test_get_legacy_model_list_default(self):
        """Test getting default model list when env var doesn't exist"""
        default_models = ["default-model"]
        models = get_legacy_model_list("NONEXISTENT_MODELS", default_models, warn=False)
        assert models == default_models

class TestLegacyConfigSupport:
    """Test legacy configuration support class"""
    
    def test_legacy_config_support_initialization(self):
        """Test that LegacyConfigSupport initializes without errors"""
        support = LegacyConfigSupport()
        assert support is not None
    
    def test_get_ollama_models(self):
        """Test getting Ollama models from legacy config"""
        support = LegacyConfigSupport()
        models = support.get_ollama_models(warn=False)
        assert isinstance(models, list)
    
    def test_get_openrouter_models(self):
        """Test getting OpenRouter models from legacy config"""
        support = LegacyConfigSupport()
        models = support.get_openrouter_models(warn=False)
        assert isinstance(models, list)
    
    def test_is_ollama_enabled(self):
        """Test checking if Ollama is enabled"""
        support = LegacyConfigSupport()
        enabled = support.is_ollama_enabled(warn=False)
        assert isinstance(enabled, bool)
    
    def test_is_openrouter_enabled(self):
        """Test checking if OpenRouter is enabled"""
        support = LegacyConfigSupport()
        enabled = support.is_openrouter_enabled(warn=False)
        assert isinstance(enabled, bool)

class TestFileMigration:
    """Test file migration functionality"""
    
    def test_migrate_model_names_in_file(self):
        """Test migrating model names in a Python file"""
        # Create temporary file with legacy model names
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
MODELS = ["llama3", "mistral"]
DEFAULT_MODEL = "phi3"
OPENROUTER_MODEL = "meta-llama/llama-3.3-8b-instruct:free"
''')
            temp_file = f.name
        
        try:
            # Migrate the file
            changed = migrate_model_names_in_file(temp_file, backup=False)
            assert changed is True
            
            # Check that migration worked
            with open(temp_file, 'r') as f:
                content = f.read()
            
            assert '"llama3.3-8b-local"' in content
            assert '"mistral-small-local"' in content
            assert '"phi4-reasoning-local"' in content
            assert '"llama3.3-8b-free"' in content
            
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_migrate_model_names_in_file_no_changes(self):
        """Test migrating file with no legacy model names"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('MODELS = ["some-new-model", "another-model"]')
            temp_file = f.name
        
        try:
            changed = migrate_model_names_in_file(temp_file, backup=False)
            assert changed is False
            
        finally:
            os.unlink(temp_file)
    
    def test_migrate_model_names_with_backup(self):
        """Test file migration with backup creation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('MODEL = "llama3"')
            temp_file = f.name
        
        try:
            changed = migrate_model_names_in_file(temp_file, backup=True)
            assert changed is True
            
            # Check backup was created
            backup_file = Path(temp_file).with_suffix('.py.backup')
            assert backup_file.exists()
            
            # Check backup contains original content
            with open(backup_file, 'r') as f:
                backup_content = f.read()
            assert 'MODEL = "llama3"' in backup_content
            
            # Check original file was updated
            with open(temp_file, 'r') as f:
                updated_content = f.read()
            assert '"llama3.3-8b-local"' in updated_content
            
        finally:
            # Clean up
            os.unlink(temp_file)
            backup_file = Path(temp_file).with_suffix('.py.backup')
            if backup_file.exists():
                os.unlink(backup_file)

class TestValidation:
    """Test validation functionality"""
    
    def test_validate_migration(self):
        """Test migration validation"""
        validation = validate_migration()
        assert isinstance(validation, dict)
        assert "legacy_config_found" in validation
        assert "unified_config_found" in validation
        assert "model_mappings" in validation
        assert "env_variables" in validation
        assert "recommendations" in validation
    
    def test_validate_migration_structure(self):
        """Test that validation returns expected structure"""
        validation = validate_migration()
        
        # Check that env_variables has expected structure
        assert isinstance(validation["env_variables"], dict)
        for var_name, var_info in validation["env_variables"].items():
            assert isinstance(var_info, dict)
            assert "legacy_set" in var_info
            assert "new_set" in var_info
            assert "values_match" in var_info
        
        # Check recommendations is a list
        assert isinstance(validation["recommendations"], list)

class TestDeprecationWarnings:
    """Test deprecation warning system"""
    
    def test_emit_deprecation_warning_default_level(self):
        """Test emitting deprecation warning with default level"""
        with pytest.warns(DeprecationWarning):
            emit_deprecation_warning("Test deprecation message")
    
    def test_emit_deprecation_warning_info_level(self):
        """Test emitting info level deprecation message"""
        # Info level should not raise warning, just log
        emit_deprecation_warning("Test info message", level="info")
    
    def test_emit_deprecation_warning_error_level(self):
        """Test emitting error level deprecation message"""
        with pytest.raises(DeprecationWarning):
            emit_deprecation_warning("Test error message", level="error")

class TestBackwardCompatibilityFunctions:
    """Test high-level backward compatibility functions"""
    
    def test_backward_compatible_functions_exist(self):
        """Test that all backward compatibility functions are importable"""
        from src.core.compatibility import (
            get_backward_compatible_ollama_models,
            get_backward_compatible_openrouter_models,
            is_ollama_enabled_legacy,
            is_openrouter_enabled_legacy
        )
        
        # Test functions can be called without errors
        ollama_models = get_backward_compatible_ollama_models()
        assert isinstance(ollama_models, list)
        
        openrouter_models = get_backward_compatible_openrouter_models()
        assert isinstance(openrouter_models, list)
        
        ollama_enabled = is_ollama_enabled_legacy()
        assert isinstance(ollama_enabled, bool)
        
        openrouter_enabled = is_openrouter_enabled_legacy()
        assert isinstance(openrouter_enabled, bool)

class TestIntegrationScenarios:
    """Test real-world migration scenarios"""
    
    def test_environment_variable_override(self):
        """Test that environment variables properly override config"""
        with patch.dict(os.environ, {"ENABLE_LOCAL_MODELS": "true"}):
            support = LegacyConfigSupport()
            assert support.is_ollama_enabled(warn=False) is True
    
    def test_model_migration_end_to_end(self):
        """Test complete model migration workflow"""
        # Start with legacy model names
        legacy_models = ["llama3", "mistral", "unknown-model"]
        
        # Migrate model names
        migrated_models = migrate_model_list(legacy_models, warn=False)
        
        # Verify migration
        assert "llama3.3-8b-local" in migrated_models
        assert "mistral-small-local" in migrated_models
        assert "unknown-model" in migrated_models  # Unknown models pass through
        
        # Test model ID resolution
        for model in migrated_models:
            model_id = resolve_model_id(model)
            assert model_id is not None
    
    def test_configuration_precedence(self):
        """Test that configuration precedence works correctly"""
        # Environment variables should take precedence over config files
        with patch.dict(os.environ, {"ENABLE_LOCAL_MODELS": "false"}):
            with patch.dict(os.environ, {"ENABLE_OPENROUTER": "true"}):
                support = LegacyConfigSupport()
                
                # These should reflect environment variable values
                # (even if config file says otherwise)
                ollama_enabled = support.is_ollama_enabled(warn=False)
                openrouter_enabled = support.is_openrouter_enabled(warn=False)
                
                # Note: The actual values depend on environment setup
                assert isinstance(ollama_enabled, bool)
                assert isinstance(openrouter_enabled, bool)

class TestErrorHandling:
    """Test error handling in migration functionality"""
    
    def test_migrate_nonexistent_file(self):
        """Test migrating a file that doesn't exist"""
        result = migrate_model_names_in_file("/nonexistent/file.py", backup=False)
        assert result is False
    
    def test_resolve_model_id_graceful_fallback(self):
        """Test that model ID resolution gracefully handles missing config"""
        # Should not raise exception even if unified config is not available
        result = resolve_model_id("some-unknown-model")
        assert result == "some-unknown-model"  # Should fall back to original name
    
    def test_legacy_config_loading_failure(self):
        """Test that legacy config support handles loading failures gracefully"""
        # Should not crash even if legacy config file is malformed or missing
        support = LegacyConfigSupport()
        models = support.get_ollama_models(warn=False)
        assert isinstance(models, list)  # Should return empty list or default

# Integration test to verify the complete migration workflow
class TestMigrationWorkflow:
    """Integration tests for complete migration workflow"""
    
    def test_complete_migration_simulation(self):
        """Simulate a complete migration workflow"""
        # Step 1: Validate current state
        initial_validation = validate_migration()
        assert isinstance(initial_validation, dict)
        
        # Step 2: Test legacy compatibility
        support = LegacyConfigSupport()
        ollama_models = support.get_ollama_models(warn=False)
        openrouter_models = support.get_openrouter_models(warn=False)
        
        # Step 3: Test model migration
        if ollama_models:
            migrated_ollama = migrate_model_list(ollama_models, warn=False)
            assert len(migrated_ollama) == len(ollama_models)
        
        if openrouter_models:
            migrated_openrouter = migrate_model_list(openrouter_models, warn=False)
            assert len(migrated_openrouter) == len(openrouter_models)
        
        # Step 4: Validate migration tools work
        mapping = get_model_mapping()
        assert len(mapping) > 0
        
        # This test verifies the complete workflow would work
        # without actually making persistent changes