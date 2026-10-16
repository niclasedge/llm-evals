#!/usr/bin/env python3
"""
Configuration Migration Script for LLM Evaluation Framework

This script helps migrate from legacy configuration patterns to the unified
configuration system. It handles:

- Environment variable migration
- Model name migration
- Configuration file format conversion
- Backup and rollback functionality

Usage:
    python scripts/migrate_config.py [options]

Examples:
    python scripts/migrate_config.py --analyze                    # Analyze current setup
    python scripts/migrate_config.py --migrate --backup          # Migrate with backup
    python scripts/migrate_config.py --generate-default          # Create default config
    python scripts/migrate_config.py --validate                  # Validate migration
"""

import argparse
import os
import json
import yaml
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.compatibility import (
    LEGACY_MODEL_MAPPING,
    get_legacy_env_var,
    get_legacy_boolean_env,
    validate_migration,
    emit_deprecation_warning
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationConfig:
    """Configuration for migration process"""
    
    # File paths
    LEGACY_CONFIG_PATH = project_root / "src" / "features" / "llm_evaluation" / "config.py"
    UNIFIED_CONFIG_PATH = project_root / "configs" / "llm_model_mapping.yaml"
    BACKUP_DIR = project_root / "migration_backups"
    ENV_FILE_PATH = project_root / ".env"
    
    # Default models for unified configuration
    DEFAULT_OLLAMA_MODELS = [
        {
            "name": "llama3.3-8b-local",
            "model_id": "llama3.3:8b",
            "capabilities": ["text", "reasoning"],
            "description": "Latest Llama model with balanced performance/size"
        },
        {
            "name": "mistral-small-local", 
            "model_id": "mistral-small3.2",
            "capabilities": ["text", "code"],
            "description": "Efficient Mistral variant for code and text"
        },
        {
            "name": "phi4-reasoning-local",
            "model_id": "phi4-reasoning", 
            "capabilities": ["reasoning", "math"],
            "description": "Microsoft's specialized reasoning model"
        },
        {
            "name": "gemma3-27b-local",
            "model_id": "gemma3:27b",
            "capabilities": ["text", "reasoning", "code"],
            "description": "Large Google model for complex reasoning tasks"
        },
        {
            "name": "devstral-local",
            "model_id": "devstral",
            "capabilities": ["code", "text"],
            "description": "Development-focused model optimized for coding"
        }
    ]
    
    DEFAULT_OPENROUTER_MODELS = [
        {
            "name": "llama3.3-8b-free",
            "model_id": "meta-llama/llama-3.3-8b-instruct:free",
            "capabilities": ["text", "reasoning"],
            "description": "Free tier Llama 3.3 8B model"
        },
        {
            "name": "gemma3-1b-free",
            "model_id": "google/gemma-3-1b-it:free", 
            "capabilities": ["text"],
            "description": "Free tier Gemma 3 1B model"
        },
        {
            "name": "gemma3-27b-free",
            "model_id": "google/gemma-2-27b-it:free",
            "capabilities": ["text", "reasoning"],
            "description": "Free tier Gemma 2 27B model"
        }
    ]

class ConfigMigrator:
    """Main migration class"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def analyze_current_setup(self) -> Dict[str, Any]:
        """Analyze current configuration setup"""
        logger.info("Analyzing current configuration setup...")
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "legacy_config": self._analyze_legacy_config(),
            "environment_variables": self._analyze_environment_variables(),
            "unified_config": self._analyze_unified_config(),
            "migration_status": validate_migration(),
            "recommendations": []
        }
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _analyze_legacy_config(self) -> Dict[str, Any]:
        """Analyze legacy configuration file"""
        result = {
            "exists": self.config.LEGACY_CONFIG_PATH.exists(),
            "models": {},
            "settings": {}
        }
        
        if result["exists"]:
            try:
                # Try to extract configuration from legacy config.py
                with open(self.config.LEGACY_CONFIG_PATH, 'r') as f:
                    content = f.read()
                
                # Simple parsing to extract model lists (not executing Python code)
                result["has_ollama_models"] = "OLLAMA_MODELS_TO_TEST" in content
                result["has_openrouter_models"] = "OPENROUTER_MODELS_TO_TEST" in content
                result["has_enable_flags"] = "ENABLE_OLLAMA" in content or "ENABLE_OPENROUTER" in content
                
            except Exception as e:
                logger.warning(f"Could not analyze legacy config: {e}")
                result["error"] = str(e)
        
        return result
    
    def _analyze_environment_variables(self) -> Dict[str, Any]:
        """Analyze current environment variables"""
        env_vars = {
            "ENABLE_LOCAL_MODELS": os.getenv("ENABLE_LOCAL_MODELS"),
            "ENABLE_OPENROUTER": os.getenv("ENABLE_OPENROUTER"),
            "OPENROUTER_API_KEY": "***" if os.getenv("OPENROUTER_API_KEY") else None,
            "DEFAULT_OLLAMA_MODEL": os.getenv("DEFAULT_OLLAMA_MODEL"),
            "DEFAULT_OPENROUTER_MODEL": os.getenv("DEFAULT_OPENROUTER_MODEL"),
        }
        
        return {
            "found_variables": {k: v for k, v in env_vars.items() if v is not None},
            "missing_variables": [k for k, v in env_vars.items() if v is None],
            "env_file_exists": self.config.ENV_FILE_PATH.exists()
        }
    
    def _analyze_unified_config(self) -> Dict[str, Any]:
        """Analyze unified configuration file"""
        result = {
            "exists": self.config.UNIFIED_CONFIG_PATH.exists(),
            "valid": False,
            "providers": {}
        }
        
        if result["exists"]:
            try:
                with open(self.config.UNIFIED_CONFIG_PATH, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                result["valid"] = "providers" in config_data
                if result["valid"]:
                    result["providers"] = list(config_data.get("providers", {}).keys())
                    result["total_models"] = sum(
                        len(provider.get("models", []))
                        for provider in config_data["providers"].values()
                    )
                
            except Exception as e:
                logger.warning(f"Could not analyze unified config: {e}")
                result["error"] = str(e)
        
        return result
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate migration recommendations based on analysis"""
        recommendations = []
        
        # Check if migration is needed
        if analysis["legacy_config"]["exists"] and not analysis["unified_config"]["exists"]:
            recommendations.append("Create unified configuration file from legacy settings")
        
        # Check environment variables
        env_analysis = analysis["environment_variables"]
        if env_analysis["found_variables"]:
            recommendations.append("Consider migrating environment variables to .env file")
        
        if not env_analysis["found_variables"].get("OPENROUTER_API_KEY"):
            recommendations.append("Set OPENROUTER_API_KEY for cloud model testing")
        
        # Check configuration validity
        if analysis["unified_config"]["exists"] and not analysis["unified_config"]["valid"]:
            recommendations.append("Fix unified configuration file format")
        
        # Migration status recommendations
        migration_recs = analysis["migration_status"]["recommendations"]
        recommendations.extend(migration_recs)
        
        return recommendations
    
    def create_backup(self) -> Path:
        """Create backup of current configuration"""
        backup_dir = self.config.BACKUP_DIR / f"backup_{self.backup_timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating backup in: {backup_dir}")
        
        # Backup legacy config if it exists
        if self.config.LEGACY_CONFIG_PATH.exists():
            shutil.copy2(self.config.LEGACY_CONFIG_PATH, backup_dir / "config.py.backup")
            logger.info("Backed up legacy config.py")
        
        # Backup unified config if it exists
        if self.config.UNIFIED_CONFIG_PATH.exists():
            shutil.copy2(self.config.UNIFIED_CONFIG_PATH, backup_dir / "llm_model_mapping.yaml.backup")
            logger.info("Backed up unified configuration")
        
        # Backup .env file if it exists
        if self.config.ENV_FILE_PATH.exists():
            shutil.copy2(self.config.ENV_FILE_PATH, backup_dir / ".env.backup")
            logger.info("Backed up .env file")
        
        # Create backup metadata
        metadata = {
            "timestamp": self.backup_timestamp,
            "backup_reason": "pre_migration",
            "files_backed_up": list(backup_dir.iterdir())
        }
        
        with open(backup_dir / "backup_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Backup completed: {backup_dir}")
        return backup_dir
    
    def generate_default_config(self) -> Dict[str, Any]:
        """Generate default unified configuration"""
        config = {
            "# LLM Evaluation Framework - Unified Configuration": None,
            "version": "2.0",
            "providers": {
                "ollama": {
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                    "timeout": 60,
                    "models": self.config.DEFAULT_OLLAMA_MODELS
                },
                "openrouter": {
                    "enabled": True,
                    "api_key_env": "OPENROUTER_API_KEY",
                    "base_url": "https://openrouter.ai/api/v1",
                    "timeout": 30,
                    "models": self.config.DEFAULT_OPENROUTER_MODELS
                }
            },
            "defaults": {
                "ollama_model": "llama3.3-8b-local",
                "openrouter_model": "llama3.3-8b-free",
                "timeout": 30,
                "max_retries": 3
            },
            "compatibility": {
                "enable_legacy_imports": True,
                "warn_on_deprecated": True,
                "model_name_mapping": LEGACY_MODEL_MAPPING
            }
        }
        
        return config
    
    def migrate_configuration(self, backup: bool = True, force: bool = False) -> bool:
        """
        Migrate from legacy to unified configuration
        
        Args:
            backup: Whether to create backup before migration
            force: Whether to overwrite existing unified config
            
        Returns:
            True if migration was successful
        """
        logger.info("Starting configuration migration...")
        
        # Create backup if requested
        if backup:
            self.create_backup()
        
        # Check if unified config already exists
        if self.config.UNIFIED_CONFIG_PATH.exists() and not force:
            logger.warning(f"Unified config already exists: {self.config.UNIFIED_CONFIG_PATH}")
            logger.warning("Use --force to overwrite or --backup to create backup first")
            return False
        
        # Generate configuration
        config_data = self.generate_default_config()
        
        # Try to enhance with legacy settings
        self._enhance_config_from_legacy(config_data)
        self._enhance_config_from_environment(config_data)
        
        # Ensure config directory exists
        self.config.UNIFIED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Write unified configuration
        try:
            with open(self.config.UNIFIED_CONFIG_PATH, 'w') as f:
                # Write header comment
                f.write("# LLM Evaluation Framework - Unified Configuration\n")
                f.write(f"# Generated on: {datetime.now().isoformat()}\n")
                f.write("# This file replaces legacy configuration patterns\n\n")
                
                # Clean config data for YAML output
                clean_config = {k: v for k, v in config_data.items() if not k.startswith("#")}
                yaml.dump(clean_config, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Created unified configuration: {self.config.UNIFIED_CONFIG_PATH}")
            
            # Create .env file if it doesn't exist
            self._create_env_file_if_needed()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write unified configuration: {e}")
            return False
    
    def _enhance_config_from_legacy(self, config_data: Dict[str, Any]):
        """Enhance configuration with settings from legacy config"""
        try:
            from src.core.compatibility import LegacyConfigSupport
            legacy_support = LegacyConfigSupport()
            
            # Get legacy model lists
            ollama_models = legacy_support.get_ollama_models(warn=False)
            openrouter_models = legacy_support.get_openrouter_models(warn=False)
            
            # Update Ollama models if found
            if ollama_models:
                migrated_models = []
                for model_name in ollama_models:
                    # Find matching default model or create new entry
                    default_model = next(
                        (m for m in self.config.DEFAULT_OLLAMA_MODELS if m["name"] == model_name),
                        None
                    )
                    if default_model:
                        migrated_models.append(default_model)
                    else:
                        # Create new model entry
                        migrated_models.append({
                            "name": model_name,
                            "model_id": model_name.replace("-local", ""),
                            "capabilities": ["text"],
                            "description": f"Migrated from legacy config"
                        })
                
                if migrated_models:
                    config_data["providers"]["ollama"]["models"] = migrated_models
                    logger.info(f"Enhanced config with {len(migrated_models)} Ollama models from legacy config")
            
            # Update OpenRouter models if found
            if openrouter_models:
                migrated_models = []
                for model_name in openrouter_models:
                    default_model = next(
                        (m for m in self.config.DEFAULT_OPENROUTER_MODELS if m["name"] == model_name),
                        None
                    )
                    if default_model:
                        migrated_models.append(default_model)
                    else:
                        migrated_models.append({
                            "name": model_name,
                            "model_id": model_name,
                            "capabilities": ["text"],
                            "description": f"Migrated from legacy config"
                        })
                
                if migrated_models:
                    config_data["providers"]["openrouter"]["models"] = migrated_models
                    logger.info(f"Enhanced config with {len(migrated_models)} OpenRouter models from legacy config")
            
        except Exception as e:
            logger.warning(f"Could not enhance config from legacy settings: {e}")
    
    def _enhance_config_from_environment(self, config_data: Dict[str, Any]):
        """Enhance configuration with current environment variables"""
        # Update provider enable status
        if get_legacy_boolean_env("ENABLE_LOCAL_MODELS", warn=False):
            config_data["providers"]["ollama"]["enabled"] = True
        
        if get_legacy_boolean_env("ENABLE_OPENROUTER", warn=False):
            config_data["providers"]["openrouter"]["enabled"] = True
        
        # Update default models
        default_ollama = get_legacy_env_var("DEFAULT_OLLAMA_MODEL", warn=False)
        if default_ollama:
            config_data["defaults"]["ollama_model"] = default_ollama
        
        default_openrouter = get_legacy_env_var("DEFAULT_OPENROUTER_MODEL", warn=False) 
        if default_openrouter:
            config_data["defaults"]["openrouter_model"] = default_openrouter
        
        logger.info("Enhanced config with environment variables")
    
    def _create_env_file_if_needed(self):
        """Create .env file with common environment variables if it doesn't exist"""
        if not self.config.ENV_FILE_PATH.exists():
            env_content = """# LLM Evaluation Framework Environment Variables
# Generated during configuration migration

# OpenRouter API Key (required for cloud models)
# OPENROUTER_API_KEY=your_api_key_here

# Provider Enable Flags (optional - can be configured in YAML)
ENABLE_LOCAL_MODELS=true
ENABLE_OPENROUTER=true

# Default Models (optional - can be configured in YAML)
# DEFAULT_OLLAMA_MODEL=llama3.3-8b-local
# DEFAULT_OPENROUTER_MODEL=llama3.3-8b-free

# Performance Settings
# LLM_TIMEOUT=30
# LLM_MAX_RETRIES=3
"""
            
            with open(self.config.ENV_FILE_PATH, 'w') as f:
                f.write(env_content)
            
            logger.info(f"Created .env file template: {self.config.ENV_FILE_PATH}")
    
    def validate_migration(self) -> Dict[str, Any]:
        """Validate that migration was successful"""
        logger.info("Validating migration...")
        
        validation = validate_migration()
        
        # Additional validation checks
        validation["unified_config_valid"] = self._validate_unified_config()
        validation["legacy_compatibility"] = self._test_legacy_compatibility()
        
        return validation
    
    def _validate_unified_config(self) -> Dict[str, Any]:
        """Validate unified configuration file"""
        if not self.config.UNIFIED_CONFIG_PATH.exists():
            return {"valid": False, "reason": "File does not exist"}
        
        try:
            with open(self.config.UNIFIED_CONFIG_PATH, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Check required structure
            if "providers" not in config_data:
                return {"valid": False, "reason": "Missing 'providers' section"}
            
            # Check provider structure
            for provider_name, provider_config in config_data["providers"].items():
                if "models" not in provider_config:
                    return {"valid": False, "reason": f"Provider '{provider_name}' missing 'models'"}
                
                for model in provider_config["models"]:
                    if not all(key in model for key in ["name", "model_id"]):
                        return {"valid": False, "reason": f"Model in '{provider_name}' missing required fields"}
            
            return {"valid": True, "providers": list(config_data["providers"].keys())}
            
        except Exception as e:
            return {"valid": False, "reason": f"Error reading config: {e}"}
    
    def _test_legacy_compatibility(self) -> Dict[str, Any]:
        """Test that legacy compatibility layer works"""
        try:
            from src.core.compatibility import (
                get_backward_compatible_ollama_models,
                get_backward_compatible_openrouter_models,
                is_ollama_enabled_legacy,
                is_openrouter_enabled_legacy
            )
            
            result = {
                "compatibility_import": True,
                "ollama_models": len(get_backward_compatible_ollama_models()),
                "openrouter_models": len(get_backward_compatible_openrouter_models()),
                "ollama_enabled": is_ollama_enabled_legacy(),
                "openrouter_enabled": is_openrouter_enabled_legacy()
            }
            
            return result
            
        except Exception as e:
            return {"compatibility_import": False, "error": str(e)}

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Migrate LLM Evaluation Framework configuration")
    
    # Action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--analyze", action="store_true", 
                            help="Analyze current configuration setup")
    action_group.add_argument("--migrate", action="store_true",
                            help="Perform configuration migration")
    action_group.add_argument("--generate-default", action="store_true",
                            help="Generate default unified configuration")
    action_group.add_argument("--validate", action="store_true",
                            help="Validate migration status")
    action_group.add_argument("--restore-backup", type=str, metavar="BACKUP_DIR",
                            help="Restore from backup directory")
    
    # Option arguments
    parser.add_argument("--backup", action="store_true",
                       help="Create backup before migration")
    parser.add_argument("--force", action="store_true",
                       help="Force overwrite of existing files")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--output", type=str, metavar="FILE",
                       help="Output file for analysis results")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize migrator
    config = MigrationConfig()
    migrator = ConfigMigrator(config)
    
    try:
        if args.analyze:
            # Analyze current setup
            analysis = migrator.analyze_current_setup()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(analysis, f, indent=2, default=str)
                logger.info(f"Analysis saved to: {args.output}")
            else:
                print(json.dumps(analysis, indent=2, default=str))
        
        elif args.migrate:
            # Perform migration
            if args.dry_run:
                logger.info("DRY RUN: Would perform configuration migration")
                analysis = migrator.analyze_current_setup()
                print("Current setup analysis:")
                print(json.dumps(analysis, indent=2, default=str))
            else:
                success = migrator.migrate_configuration(backup=args.backup, force=args.force)
                if success:
                    logger.info("Migration completed successfully!")
                    # Validate migration
                    validation = migrator.validate_migration()
                    if validation.get("unified_config_valid", {}).get("valid", False):
                        logger.info("Migration validation passed!")
                    else:
                        logger.warning("Migration validation failed - please check configuration")
                else:
                    logger.error("Migration failed")
                    return 1
        
        elif args.generate_default:
            # Generate default configuration
            if args.dry_run:
                config_data = migrator.generate_default_config()
                print("Default configuration:")
                clean_config = {k: v for k, v in config_data.items() if not k.startswith("#")}
                print(yaml.dump(clean_config, default_flow_style=False))
            else:
                success = migrator.migrate_configuration(backup=args.backup, force=args.force)
                if success:
                    logger.info("Default configuration created successfully!")
                else:
                    logger.error("Failed to create default configuration")
                    return 1
        
        elif args.validate:
            # Validate migration
            validation = migrator.validate_migration()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(validation, f, indent=2, default=str)
                logger.info(f"Validation results saved to: {args.output}")
            else:
                print(json.dumps(validation, indent=2, default=str))
        
        elif args.restore_backup:
            # Restore from backup
            backup_dir = Path(args.restore_backup)
            if not backup_dir.exists():
                logger.error(f"Backup directory not found: {backup_dir}")
                return 1
            
            if args.dry_run:
                logger.info(f"DRY RUN: Would restore from {backup_dir}")
                backup_files = list(backup_dir.glob("*.backup"))
                for backup_file in backup_files:
                    logger.info(f"Would restore: {backup_file}")
            else:
                logger.info(f"Restoring from backup: {backup_dir}")
                # Implementation would restore backed up files
                logger.warning("Backup restoration not yet implemented")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())