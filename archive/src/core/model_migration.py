"""
Model Migration Utilities

This module provides utilities to help migrate existing configurations
to the unified model configuration system.
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from .llm_unified_config import UnifiedLLMConfig, ModelConfig


@dataclass
class MigrationReport:
    """Report of migration results"""
    success: bool
    migrated_models: List[str]
    failed_models: List[str]
    warnings: List[str]
    errors: List[str]
    
    def __str__(self) -> str:
        """String representation of the migration report"""
        report = f"Migration Report:\n"
        report += f"  Success: {self.success}\n"
        report += f"  Migrated Models: {len(self.migrated_models)}\n"
        report += f"  Failed Models: {len(self.failed_models)}\n"
        report += f"  Warnings: {len(self.warnings)}\n"
        report += f"  Errors: {len(self.errors)}\n"
        
        if self.migrated_models:
            report += f"\nMigrated Models:\n"
            for model in self.migrated_models:
                report += f"  ✓ {model}\n"
        
        if self.failed_models:
            report += f"\nFailed Models:\n"
            for model in self.failed_models:
                report += f"  ✗ {model}\n"
        
        if self.warnings:
            report += f"\nWarnings:\n"
            for warning in self.warnings:
                report += f"  ⚠ {warning}\n"
        
        if self.errors:
            report += f"\nErrors:\n"
            for error in self.errors:
                report += f"  ❌ {error}\n"
        
        return report


class ModelMigration:
    """Utility class for migrating model configurations"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize the migration utility
        
        Args:
            config_path: Path to the unified configuration file
        """
        self.config_path = config_path or "configs/llm_model_mapping.yaml"
        self.unified_config = UnifiedLLMConfig(config_path)
        
    def migrate_openrouter_models(self, legacy_models: List[str]) -> MigrationReport:
        """
        Migrate OpenRouter models from legacy format to unified configuration
        
        Args:
            legacy_models: List of legacy OpenRouter model IDs
            
        Returns:
            MigrationReport with migration results
        """
        report = MigrationReport(
            success=True,
            migrated_models=[],
            failed_models=[],
            warnings=[],
            errors=[]
        )
        
        for model_id in legacy_models:
            try:
                # Check if model exists in unified config
                model = self.unified_config.get_model_by_id(model_id)
                if model:
                    report.migrated_models.append(f"{model_id} -> {model.name}")
                else:
                    report.failed_models.append(model_id)
                    report.warnings.append(f"Model {model_id} not found in unified configuration")
            except Exception as e:
                report.failed_models.append(model_id)
                report.errors.append(f"Error migrating {model_id}: {str(e)}")
                report.success = False
        
        return report
    
    def migrate_ollama_models(self, legacy_models: List[str]) -> MigrationReport:
        """
        Migrate Ollama models from legacy format to unified configuration
        
        Args:
            legacy_models: List of legacy Ollama model IDs
            
        Returns:
            MigrationReport with migration results
        """
        report = MigrationReport(
            success=True,
            migrated_models=[],
            failed_models=[],
            warnings=[],
            errors=[]
        )
        
        for model_id in legacy_models:
            try:
                # Check if model exists in unified config
                model = self.unified_config.get_model_by_id(model_id)
                if model:
                    report.migrated_models.append(f"{model_id} -> {model.name}")
                else:
                    report.failed_models.append(model_id)
                    report.warnings.append(f"Model {model_id} not found in unified configuration")
            except Exception as e:
                report.failed_models.append(model_id)
                report.errors.append(f"Error migrating {model_id}: {str(e)}")
                report.success = False
        
        return report
    
    def validate_model_availability(self, models: List[str]) -> Dict[str, bool]:
        """
        Validate if models are available and properly configured
        
        Args:
            models: List of model names, aliases, or IDs
            
        Returns:
            Dictionary mapping model names to availability status
        """
        availability = {}
        
        for model_name in models:
            try:
                is_available = self.unified_config.validate_model_availability(model_name)
                availability[model_name] = is_available
            except Exception as e:
                availability[model_name] = False
        
        return availability
    
    def generate_migration_report(self, 
                                legacy_openrouter_models: List[str] = None,
                                legacy_ollama_models: List[str] = None) -> MigrationReport:
        """
        Generate a comprehensive migration report
        
        Args:
            legacy_openrouter_models: List of legacy OpenRouter model IDs
            legacy_ollama_models: List of legacy Ollama model IDs
            
        Returns:
            Combined MigrationReport
        """
        combined_report = MigrationReport(
            success=True,
            migrated_models=[],
            failed_models=[],
            warnings=[],
            errors=[]
        )
        
        # Default legacy models if not provided
        if legacy_openrouter_models is None:
            legacy_openrouter_models = [
                "meta-llama/llama-3.3-8b-instruct:free",
                "google/gemma-3-1b-it:free",
                "meta-llama/llama-3.2-11b-vision-instruct:free",
                "meta-llama/llama-3.2-90b-vision-instruct:free",
                "google/gemma-2-9b-it:free",
                "google/gemma-2-27b-it:free",
                "qwen/qwen2-vl-7b-instruct:free",
                "qwen/qwen2-vl-72b-instruct:free"
            ]
        
        if legacy_ollama_models is None:
            legacy_ollama_models = [
                "llama3",
                "mistral",
                "llava:latest",
                "llava:7b",
                "llava:13b",
                "bakllava:latest",
                "moondream:latest"
            ]
        
        # Migrate OpenRouter models
        if legacy_openrouter_models:
            openrouter_report = self.migrate_openrouter_models(legacy_openrouter_models)
            combined_report.migrated_models.extend([f"OpenRouter: {m}" for m in openrouter_report.migrated_models])
            combined_report.failed_models.extend([f"OpenRouter: {m}" for m in openrouter_report.failed_models])
            combined_report.warnings.extend([f"OpenRouter: {w}" for w in openrouter_report.warnings])
            combined_report.errors.extend([f"OpenRouter: {e}" for e in openrouter_report.errors])
            if not openrouter_report.success:
                combined_report.success = False
        
        # Migrate Ollama models
        if legacy_ollama_models:
            ollama_report = self.migrate_ollama_models(legacy_ollama_models)
            combined_report.migrated_models.extend([f"Ollama: {m}" for m in ollama_report.migrated_models])
            combined_report.failed_models.extend([f"Ollama: {m}" for m in ollama_report.failed_models])
            combined_report.warnings.extend([f"Ollama: {w}" for w in ollama_report.warnings])
            combined_report.errors.extend([f"Ollama: {e}" for e in ollama_report.errors])
            if not ollama_report.success:
                combined_report.success = False
        
        # Add general validation
        try:
            all_models = self.unified_config.list_models()
            combined_report.warnings.append(f"Total models in unified config: {len(all_models)}")
            
            enabled_models = self.unified_config.list_models(enabled_only=True)
            combined_report.warnings.append(f"Enabled models: {len(enabled_models)}")
            
            free_models = self.unified_config.list_models(free_only=True)
            combined_report.warnings.append(f"Free models: {len(free_models)}")
            
        except Exception as e:
            combined_report.errors.append(f"Error validating unified config: {str(e)}")
            combined_report.success = False
        
        return combined_report
    
    def create_backup_config(self, backup_path: str = None) -> str:
        """
        Create a backup of the current configuration
        
        Args:
            backup_path: Path to save backup (optional)
            
        Returns:
            Path to the created backup
        """
        if backup_path is None:
            backup_path = f"{self.config_path}.backup"
        
        try:
            if os.path.exists(self.config_path):
                import shutil
                shutil.copy2(self.config_path, backup_path)
                return backup_path
            else:
                raise FileNotFoundError(f"Configuration file {self.config_path} not found")
        except Exception as e:
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def restore_backup_config(self, backup_path: str = None) -> bool:
        """
        Restore configuration from backup
        
        Args:
            backup_path: Path to backup file (optional)
            
        Returns:
            True if restoration was successful
        """
        if backup_path is None:
            backup_path = f"{self.config_path}.backup"
        
        try:
            if os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, self.config_path)
                return True
            else:
                raise FileNotFoundError(f"Backup file {backup_path} not found")
        except Exception as e:
            raise Exception(f"Failed to restore backup: {str(e)}")
    
    def export_legacy_format(self, output_path: str = None) -> Dict[str, List[str]]:
        """
        Export unified configuration to legacy format
        
        Args:
            output_path: Path to save legacy format (optional)
            
        Returns:
            Dictionary with legacy format model lists
        """
        legacy_format = self.unified_config.get_backward_compatible_lists()
        
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    json.dump(legacy_format, f, indent=2)
            except Exception as e:
                raise Exception(f"Failed to export legacy format: {str(e)}")
        
        return legacy_format
    
    def validate_configuration(self) -> MigrationReport:
        """
        Validate the current unified configuration
        
        Returns:
            MigrationReport with validation results
        """
        report = MigrationReport(
            success=True,
            migrated_models=[],
            failed_models=[],
            warnings=[],
            errors=[]
        )
        
        try:
            # Check if configuration file exists
            if not os.path.exists(self.config_path):
                report.errors.append(f"Configuration file {self.config_path} not found")
                report.success = False
                return report
            
            # Check if configuration is valid YAML
            try:
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    if not config_data:
                        report.errors.append("Configuration file is empty or invalid")
                        report.success = False
                        return report
            except yaml.YAMLError as e:
                report.errors.append(f"Invalid YAML in configuration file: {str(e)}")
                report.success = False
                return report
            
            # Check if providers are configured
            providers = self.unified_config.list_providers()
            if not providers:
                report.errors.append("No providers configured")
                report.success = False
            else:
                report.warnings.append(f"Configured providers: {providers}")
            
            # Check if models are configured
            models = self.unified_config.list_models()
            if not models:
                report.errors.append("No models configured")
                report.success = False
            else:
                report.warnings.append(f"Total models configured: {len(models)}")
            
            # Check for duplicate model names
            model_names = [model.name for model in models]
            duplicates = [name for name in model_names if model_names.count(name) > 1]
            if duplicates:
                report.errors.append(f"Duplicate model names found: {duplicates}")
                report.success = False
            
            # Check for duplicate aliases
            all_aliases = []
            for model in models:
                all_aliases.extend(model.aliases)
            duplicate_aliases = [alias for alias in all_aliases if all_aliases.count(alias) > 1]
            if duplicate_aliases:
                report.errors.append(f"Duplicate aliases found: {duplicate_aliases}")
                report.success = False
            
            # Check API key availability
            for provider in providers:
                api_key = self.unified_config.get_api_key(provider)
                if provider in ['openrouter', 'openai'] and not api_key:
                    report.warnings.append(f"API key for {provider} not set")
            
            # Validate model availability
            enabled_models = self.unified_config.list_models(enabled_only=True)
            for model in enabled_models:
                if model.provider in ['openrouter', 'openai']:
                    api_key = self.unified_config.get_api_key(model.provider)
                    if not api_key:
                        report.warnings.append(f"Model {model.name} is enabled but API key for {model.provider} is not set")
            
            report.warnings.append("Configuration validation completed")
            
        except Exception as e:
            report.errors.append(f"Error validating configuration: {str(e)}")
            report.success = False
        
        return report


def migrate_legacy_config(legacy_openrouter_models: List[str] = None,
                         legacy_ollama_models: List[str] = None,
                         config_path: str = None) -> MigrationReport:
    """
    Convenience function to migrate legacy configuration
    
    Args:
        legacy_openrouter_models: List of legacy OpenRouter model IDs
        legacy_ollama_models: List of legacy Ollama model IDs
        config_path: Path to unified configuration file
        
    Returns:
        MigrationReport with migration results
    """
    migration = ModelMigration(config_path)
    return migration.generate_migration_report(legacy_openrouter_models, legacy_ollama_models)


def validate_unified_config(config_path: str = None) -> MigrationReport:
    """
    Convenience function to validate unified configuration
    
    Args:
        config_path: Path to unified configuration file
        
    Returns:
        MigrationReport with validation results
    """
    migration = ModelMigration(config_path)
    return migration.validate_configuration()