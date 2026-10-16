"""
Tests for unified evaluation CLI

This module provides tests for the CLI interface.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch

from ..cli import cli


class TestCLI:
    """Test CLI interface"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    def test_cli_help(self, runner):
        """Test CLI help command"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'LLM Evaluation CLI' in result.output
    
    def test_models_command_help(self, runner):
        """Test models command help"""
        result = runner.invoke(cli, ['models', '--help'])
        assert result.exit_code == 0
        assert 'List available models' in result.output
    
    def test_providers_command_help(self, runner):
        """Test providers command help"""
        result = runner.invoke(cli, ['providers', '--help'])
        assert result.exit_code == 0
        assert 'List available providers' in result.output
    
    def test_coding_command_help(self, runner):
        """Test coding command help"""
        result = runner.invoke(cli, ['coding', '--help'])
        assert result.exit_code == 0
        assert 'Run coding evaluation tests' in result.output
    
    def test_vision_command_help(self, runner):
        """Test vision command help"""
        result = runner.invoke(cli, ['vision', '--help'])
        assert result.exit_code == 0
        assert 'Run vision evaluation tests' in result.output
    
    def test_tools_command_help(self, runner):
        """Test tools command help"""
        result = runner.invoke(cli, ['tools', '--help'])
        assert result.exit_code == 0
        assert 'Run tool call evaluation tests' in result.output
    
    def test_intelligence_command_help(self, runner):
        """Test intelligence command help"""
        result = runner.invoke(cli, ['intelligence', '--help'])
        assert result.exit_code == 0
        assert 'Run intelligence/reasoning evaluation tests' in result.output
    
    def test_all_command_help(self, runner):
        """Test all command help"""
        result = runner.invoke(cli, ['all', '--help'])
        assert result.exit_code == 0
        assert 'Run comprehensive evaluation' in result.output
    
    @patch('src.core.llm_unified_config.get_unified_config')
    def test_models_command_list(self, mock_get_config, runner):
        """Test models command list output"""
        # Mock configuration
        mock_config = Mock()
        mock_model = Mock(
            name="llama3",
            provider="openrouter",
            model_id="test-id",
            aliases=["llama-3"],
            capabilities=["text", "code"],
            free=True,
            enabled=True
        )
        mock_config.list_models.return_value = [mock_model]
        mock_get_config.return_value = mock_config
        
        result = runner.invoke(cli, ['models'])
        
        assert result.exit_code == 0
        assert 'llama3' in result.output
        assert 'openrouter' in result.output
    
    def test_models_command_json(self, runner):
        """Test models command JSON output"""
        result = runner.invoke(cli, ['models', '--format', 'json'])
        
        assert result.exit_code == 0
        # Should have valid JSON output with model data
        import json
        try:
            model_data = json.loads(result.output)
            assert isinstance(model_data, list)
            if model_data:
                model = model_data[0]
                assert 'name' in model
                assert 'provider' in model
                assert 'model_id' in model
                assert 'capabilities' in model
                assert 'free' in model
                assert 'enabled' in model
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")
    
    def test_providers_command_list(self, runner):
        """Test providers command list output"""
        result = runner.invoke(cli, ['providers'])
        
        assert result.exit_code == 0
        assert 'openrouter' in result.output
        assert 'ollama' in result.output
    
    def test_test_model_command_success(self, runner):
        """Test test-model command success"""
        result = runner.invoke(cli, ['test-model', 'llama3'])
        
        assert result.exit_code == 0
        # Should show model information
        assert 'Testing model:' in result.output
        assert 'Provider:' in result.output
        assert 'Model ID:' in result.output
    
    def test_test_model_command_not_found(self, runner):
        """Test test-model command with model not found"""
        result = runner.invoke(cli, ['test-model', 'nonexistent'])
        
        assert result.exit_code == 0
        assert 'Model \'nonexistent\' not found' in result.output