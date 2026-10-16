"""
Test suite for migration scripts

This module tests the configuration migration script and related functionality
to ensure migrations work correctly in various scenarios.
"""

import os
import pytest
import tempfile
import shutil
import yaml
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import migration script components
from scripts.migrate_config import MigrationConfig, ConfigMigrator

class TestMigrationConfig:
    """Test MigrationConfig class"""
    
    def test_migration_config_initialization(self):
        """Test that MigrationConfig initializes with correct paths"""
        config = MigrationConfig()
        
        # Check that paths are Path objects
        assert isinstance(config.LEGACY_CONFIG_PATH, Path)
        assert isinstance(config.UNIFIED_CONFIG_PATH, Path)
        assert isinstance(config.BACKUP_DIR, Path)
        assert isinstance(config.ENV_FILE_PATH, Path)
        
        # Check that default models are properly structured
        assert isinstance(config.DEFAULT_OLLAMA_MODELS, list)
        assert isinstance(config.DEFAULT_OPENROUTER_MODELS, list)
        
        # Verify model structure
        for model in config.DEFAULT_OLLAMA_MODELS:
            assert "name" in model
            assert "model_id" in model
            assert "capabilities" in model
            assert "description" in model
        
        for model in config.DEFAULT_OPENROUTER_MODELS:
            assert "name" in model
            assert "model_id" in model
            assert "capabilities" in model
            assert "description" in model

class TestConfigMigrator:
    """Test ConfigMigrator class"""
    
    def setup_method(self):
        """Setup test environment with temporary directories"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create a test config with temporary paths
        self.config = MigrationConfig()
        self.config.LEGACY_CONFIG_PATH = self.temp_dir / "config.py"
        self.config.UNIFIED_CONFIG_PATH = self.temp_dir / "configs" / "llm_model_mapping.yaml"
        self.config.BACKUP_DIR = self.temp_dir / "backups"
        self.config.ENV_FILE_PATH = self.temp_dir / ".env"
        
        self.migrator = ConfigMigrator(self.config)
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_migrator_initialization(self):
        """Test that ConfigMigrator initializes correctly"""
        assert self.migrator.config == self.config
        assert hasattr(self.migrator, 'backup_timestamp')
        assert isinstance(self.migrator.backup_timestamp, str)
    
    def test_analyze_current_setup_empty(self):
        """Test analysis when no configuration files exist"""
        analysis = self.migrator.analyze_current_setup()
        
        assert isinstance(analysis, dict)
        assert "timestamp" in analysis
        assert "legacy_config" in analysis
        assert "environment_variables" in analysis
        assert "unified_config" in analysis
        assert "migration_status" in analysis
        assert "recommendations" in analysis
        
        # Check that empty state is detected correctly
        assert analysis["legacy_config"]["exists"] is False
        assert analysis["unified_config"]["exists"] is False
    
    def test_analyze_legacy_config_exists(self):
        """Test analysis when legacy config exists"""
        # Create a mock legacy config file
        self.config.LEGACY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.LEGACY_CONFIG_PATH, 'w') as f:
            f.write('''
ENABLE_OLLAMA = True
ENABLE_OPENROUTER = True
OLLAMA_MODELS_TO_TEST = ["llama3", "mistral"]
OPENROUTER_MODELS_TO_TEST = ["meta-llama/llama-3.3-8b-instruct:free"]
''')
        
        analysis = self.migrator.analyze_current_setup()
        
        assert analysis["legacy_config"]["exists"] is True
        assert analysis["legacy_config"]["has_ollama_models"] is True
        assert analysis["legacy_config"]["has_openrouter_models"] is True
        assert analysis["legacy_config"]["has_enable_flags"] is True
    
    def test_analyze_environment_variables(self):
        """Test environment variable analysis"""
        test_env = {
            "ENABLE_LOCAL_MODELS": "true",
            "OPENROUTER_API_KEY": "test-key",
            "DEFAULT_OLLAMA_MODEL": "llama3"
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            analysis = self.migrator.analyze_current_setup()
            
            env_analysis = analysis["environment_variables"]
            assert "ENABLE_LOCAL_MODELS" in env_analysis["found_variables"]
            assert "OPENROUTER_API_KEY" in env_analysis["found_variables"]
            assert "DEFAULT_OLLAMA_MODEL" in env_analysis["found_variables"]
            assert env_analysis["found_variables"]["OPENROUTER_API_KEY"] == "***"  # Should be masked
    
    def test_generate_default_config(self):
        """Test generating default configuration"""
        config_data = self.migrator.generate_default_config()
        
        assert isinstance(config_data, dict)
        assert "version" in config_data
        assert "providers" in config_data
        assert "defaults" in config_data
        assert "compatibility" in config_data
        
        # Check provider structure
        assert "ollama" in config_data["providers"]
        assert "openrouter" in config_data["providers"]
        
        # Check model structure
        ollama_models = config_data["providers"]["ollama"]["models"]
        assert isinstance(ollama_models, list)
        assert len(ollama_models) > 0
        
        for model in ollama_models:
            assert "name" in model
            assert "model_id" in model
            assert "capabilities" in model
    
    def test_create_backup(self):
        """Test backup creation functionality"""
        # Create some files to backup
        self.config.LEGACY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.LEGACY_CONFIG_PATH, 'w') as f:
            f.write("# Legacy config")
        
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.UNIFIED_CONFIG_PATH, 'w') as f:
            f.write("# Unified config")
        
        with open(self.config.ENV_FILE_PATH, 'w') as f:
            f.write("# Environment file")
        
        # Create backup
        backup_dir = self.migrator.create_backup()
        
        assert backup_dir.exists()
        assert backup_dir.is_dir()
        assert (backup_dir / "config.py.backup").exists()
        assert (backup_dir / "llm_model_mapping.yaml.backup").exists()
        assert (backup_dir / ".env.backup").exists()
        assert (backup_dir / "backup_metadata.json").exists()
        
        # Check metadata
        with open(backup_dir / "backup_metadata.json", 'r') as f:
            metadata = json.load(f)
        
        assert "timestamp" in metadata
        assert "backup_reason" in metadata
        assert metadata["backup_reason"] == "pre_migration"
    
    def test_migrate_configuration_new_setup(self):
        """Test migration when creating new configuration"""
        # Ensure config directory exists
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Perform migration
        success = self.migrator.migrate_configuration(backup=False, force=False)
        
        assert success is True
        assert self.config.UNIFIED_CONFIG_PATH.exists()
        
        # Validate created configuration
        with open(self.config.UNIFIED_CONFIG_PATH, 'r') as f:
            config_data = yaml.safe_load(f)
        
        assert "providers" in config_data
        assert "ollama" in config_data["providers"]
        assert "openrouter" in config_data["providers"]
    
    def test_migrate_configuration_with_existing_file(self):
        """Test migration when unified config already exists"""
        # Create existing unified config
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.UNIFIED_CONFIG_PATH, 'w') as f:
            f.write("existing: config")
        
        # Should fail without force
        success = self.migrator.migrate_configuration(backup=False, force=False)
        assert success is False
        
        # Should succeed with force
        success = self.migrator.migrate_configuration(backup=False, force=True)
        assert success is True
    
    def test_migrate_configuration_with_backup(self):
        """Test migration with backup creation"""
        # Create legacy config to backup
        self.config.LEGACY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.LEGACY_CONFIG_PATH, 'w') as f:
            f.write("# Legacy config")
        
        # Ensure config directory exists
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Perform migration with backup
        success = self.migrator.migrate_configuration(backup=True, force=False)
        
        assert success is True
        assert self.config.UNIFIED_CONFIG_PATH.exists()
        
        # Check that backup was created
        backup_dirs = list(self.config.BACKUP_DIR.glob("backup_*"))
        assert len(backup_dirs) > 0
        
        backup_dir = backup_dirs[0]
        assert (backup_dir / "config.py.backup").exists()
    
    def test_validate_unified_config_valid(self):
        """Test validation of valid unified configuration"""
        # Create valid unified config
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        config_data = self.migrator.generate_default_config()
        clean_config = {k: v for k, v in config_data.items() if not k.startswith("#")}
        
        with open(self.config.UNIFIED_CONFIG_PATH, 'w') as f:
            yaml.dump(clean_config, f)
        
        validation = self.migrator._validate_unified_config()
        
        assert validation["valid"] is True
        assert "providers" in validation
        assert len(validation["providers"]) > 0
    
    def test_validate_unified_config_invalid(self):
        """Test validation of invalid unified configuration"""
        # Create invalid unified config
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.UNIFIED_CONFIG_PATH, 'w') as f:
            f.write("invalid: yaml: structure:")
        
        validation = self.migrator._validate_unified_config()
        
        assert validation["valid"] is False
        assert "reason" in validation
    
    def test_validate_migration_complete(self):
        """Test complete migration validation"""
        # Setup minimal valid configuration
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        config_data = self.migrator.generate_default_config()
        clean_config = {k: v for k, v in config_data.items() if not k.startswith("#")}
        
        with open(self.config.UNIFIED_CONFIG_PATH, 'w') as f:
            yaml.dump(clean_config, f)
        
        validation = self.migrator.validate_migration()
        
        assert isinstance(validation, dict)
        assert "unified_config_valid" in validation
        assert "legacy_compatibility" in validation
    
    def test_enhance_config_from_environment(self):
        """Test enhancing configuration with environment variables"""
        config_data = self.migrator.generate_default_config()
        
        test_env = {
            "ENABLE_LOCAL_MODELS": "true",
            "ENABLE_OPENROUTER": "false",
            "DEFAULT_OLLAMA_MODEL": "custom-model",
            "DEFAULT_OPENROUTER_MODEL": "custom-openrouter-model"
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            self.migrator._enhance_config_from_environment(config_data)
        
        # Check that environment variables were applied
        assert config_data["providers"]["ollama"]["enabled"] is True
        assert config_data["providers"]["openrouter"]["enabled"] is False
        assert config_data["defaults"]["ollama_model"] == "custom-model"
        assert config_data["defaults"]["openrouter_model"] == "custom-openrouter-model"
    
    def test_create_env_file_if_needed(self):
        """Test .env file creation"""
        # Should create .env file if it doesn't exist
        self.migrator._create_env_file_if_needed()
        
        assert self.config.ENV_FILE_PATH.exists()
        
        # Should contain expected content
        with open(self.config.ENV_FILE_PATH, 'r') as f:
            content = f.read()
        
        assert "OPENROUTER_API_KEY" in content
        assert "ENABLE_LOCAL_MODELS" in content
        assert "ENABLE_OPENROUTER" in content
        
        # Should not overwrite existing file
        original_content = content
        self.migrator._create_env_file_if_needed()
        
        with open(self.config.ENV_FILE_PATH, 'r') as f:
            new_content = f.read()
        
        assert new_content == original_content

class TestMigrationScriptIntegration:
    """Integration tests for the migration script"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create project structure
        (self.temp_dir / "src" / "features" / "llm_evaluation").mkdir(parents=True)
        (self.temp_dir / "configs").mkdir(parents=True)
        (self.temp_dir / "scripts").mkdir(parents=True)
    
    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_migration_workflow_new_project(self):
        """Test complete migration workflow for new project"""
        # Create minimal legacy config
        legacy_config_path = self.temp_dir / "src" / "features" / "llm_evaluation" / "config.py"
        with open(legacy_config_path, 'w') as f:
            f.write('''
import os
ENABLE_OLLAMA = True
ENABLE_OPENROUTER = True
OLLAMA_MODELS_TO_TEST = ["llama3", "mistral"]
OPENROUTER_MODELS_TO_TEST = ["meta-llama/llama-3.3-8b-instruct:free"]
''')
        
        # Initialize migrator with temporary paths
        config = MigrationConfig()
        config.LEGACY_CONFIG_PATH = legacy_config_path
        config.UNIFIED_CONFIG_PATH = self.temp_dir / "configs" / "llm_model_mapping.yaml"
        config.BACKUP_DIR = self.temp_dir / "migration_backups"
        config.ENV_FILE_PATH = self.temp_dir / ".env"
        
        migrator = ConfigMigrator(config)
        
        # Step 1: Analyze current setup
        analysis = migrator.analyze_current_setup()
        assert analysis["legacy_config"]["exists"] is True
        assert analysis["unified_config"]["exists"] is False
        
        # Step 2: Perform migration
        success = migrator.migrate_configuration(backup=True, force=False)
        assert success is True
        
        # Step 3: Validate migration
        validation = migrator.validate_migration()
        assert validation["unified_config_valid"]["valid"] is True
        
        # Verify files were created
        assert config.UNIFIED_CONFIG_PATH.exists()
        assert config.ENV_FILE_PATH.exists()
        
        # Verify backup was created
        backup_dirs = list(config.BACKUP_DIR.glob("backup_*"))
        assert len(backup_dirs) > 0
    
    def test_migration_with_environment_variables(self):
        """Test migration with various environment variables set"""
        test_env = {
            "ENABLE_LOCAL_MODELS": "true",
            "ENABLE_OPENROUTER": "false",
            "OPENROUTER_API_KEY": "test-api-key",
            "DEFAULT_OLLAMA_MODEL": "custom-llama",
            "DEFAULT_OPENROUTER_MODEL": "custom-openrouter"
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            config = MigrationConfig()
            config.UNIFIED_CONFIG_PATH = self.temp_dir / "configs" / "llm_model_mapping.yaml"
            config.BACKUP_DIR = self.temp_dir / "migration_backups"
            config.ENV_FILE_PATH = self.temp_dir / ".env"
            
            migrator = ConfigMigrator(config)
            
            # Perform migration
            success = migrator.migrate_configuration(backup=False, force=False)
            assert success is True
            
            # Check that environment variables influenced the configuration
            with open(config.UNIFIED_CONFIG_PATH, 'r') as f:
                config_data = yaml.safe_load(f)
            
            assert config_data["providers"]["ollama"]["enabled"] is True
            assert config_data["providers"]["openrouter"]["enabled"] is False
            assert config_data["defaults"]["ollama_model"] == "custom-llama"
            assert config_data["defaults"]["openrouter_model"] == "custom-openrouter"

class TestErrorHandling:
    """Test error handling in migration scripts"""
    
    def test_migration_with_readonly_directory(self):
        """Test migration when target directory is readonly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = MigrationConfig()
            config.UNIFIED_CONFIG_PATH = temp_path / "readonly" / "config.yaml"
            config.BACKUP_DIR = temp_path / "backups"
            config.ENV_FILE_PATH = temp_path / ".env"
            
            # Create readonly directory
            readonly_dir = temp_path / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)  # readonly
            
            migrator = ConfigMigrator(config)
            
            try:
                # Migration should fail gracefully
                success = migrator.migrate_configuration(backup=False, force=False)
                # Should either succeed (if permissions allow) or fail gracefully
                assert isinstance(success, bool)
            finally:
                # Restore permissions for cleanup
                readonly_dir.chmod(0o755)
    
    def test_migration_with_invalid_yaml_input(self):
        """Test migration when existing config has invalid YAML"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = MigrationConfig()
            config.UNIFIED_CONFIG_PATH = temp_path / "config.yaml"
            config.BACKUP_DIR = temp_path / "backups"
            config.ENV_FILE_PATH = temp_path / ".env"
            
            # Create invalid YAML file
            with open(config.UNIFIED_CONFIG_PATH, 'w') as f:
                f.write("invalid: yaml: structure: [unclosed")
            
            migrator = ConfigMigrator(config)
            
            # Validation should handle invalid YAML gracefully
            validation = migrator._validate_unified_config()
            assert validation["valid"] is False
            assert "reason" in validation

class TestMigrationRecommendations:
    """Test migration recommendation generation"""
    
    def test_recommendations_for_new_setup(self):
        """Test recommendations for new setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = MigrationConfig()
            config.LEGACY_CONFIG_PATH = temp_path / "config.py"
            config.UNIFIED_CONFIG_PATH = temp_path / "unified.yaml"
            config.BACKUP_DIR = temp_path / "backups"
            config.ENV_FILE_PATH = temp_path / ".env"
            
            # Create legacy config but no unified config
            with open(config.LEGACY_CONFIG_PATH, 'w') as f:
                f.write("ENABLE_OLLAMA = True")
            
            migrator = ConfigMigrator(config)
            analysis = migrator.analyze_current_setup()
            
            recommendations = analysis["recommendations"]
            assert isinstance(recommendations, list)
            
            # Should recommend creating unified configuration
            recommendation_text = " ".join(recommendations)
            assert "unified configuration" in recommendation_text.lower()
    
    def test_recommendations_for_complete_setup(self):
        """Test recommendations when setup is complete"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config = MigrationConfig()
            config.LEGACY_CONFIG_PATH = temp_path / "config.py"
            config.UNIFIED_CONFIG_PATH = temp_path / "unified.yaml"
            config.BACKUP_DIR = temp_path / "backups"
            config.ENV_FILE_PATH = temp_path / ".env"
            
            migrator = ConfigMigrator(config)
            
            # Create complete setup
            config_data = migrator.generate_default_config()
            clean_config = {k: v for k, v in config_data.items() if not k.startswith("#")}
            
            with open(config.UNIFIED_CONFIG_PATH, 'w') as f:
                yaml.dump(clean_config, f)
            
            with open(config.ENV_FILE_PATH, 'w') as f:
                f.write("OPENROUTER_API_KEY=test-key")
            
            test_env = {"OPENROUTER_API_KEY": "test-key"}
            
            with patch.dict(os.environ, test_env, clear=False):
                analysis = migrator.analyze_current_setup()
            
            recommendations = analysis["recommendations"]
            
            # Should have fewer recommendations for complete setup
            assert isinstance(recommendations, list)