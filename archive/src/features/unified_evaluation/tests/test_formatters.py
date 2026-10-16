"""
Tests for unified evaluation formatters

This module provides tests for the output formatters.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from ..formatters import (
    get_formatter,
    JSONFormatter,
    MarkdownFormatter,
    CSVFormatter,
    ConsoleFormatter
)
from ..models import (
    OutputFormat,
    EvaluationType,
    EvaluationResult,
    ModelResult,
    EvaluationMetrics,
    ModelSelection,
    OutputConfig,
    EvaluationRequest
)


class TestGetFormatter:
    """Test formatter factory function"""
    
    def test_get_json_formatter(self):
        """Test getting JSON formatter"""
        formatter = get_formatter(OutputFormat.JSON)
        assert isinstance(formatter, JSONFormatter)
    
    def test_get_markdown_formatter(self):
        """Test getting Markdown formatter"""
        formatter = get_formatter(OutputFormat.MARKDOWN)
        assert isinstance(formatter, MarkdownFormatter)
    
    def test_get_csv_formatter(self):
        """Test getting CSV formatter"""
        formatter = get_formatter(OutputFormat.CSV)
        assert isinstance(formatter, CSVFormatter)
    
    def test_get_console_formatter(self):
        """Test getting console formatter"""
        formatter = get_formatter(OutputFormat.CONSOLE)
        assert isinstance(formatter, ConsoleFormatter)


class TestJSONFormatter:
    """Test JSONFormatter class"""
    
    @pytest.fixture
    def formatter(self):
        """Create JSON formatter"""
        return JSONFormatter()
    
    @pytest.fixture
    def sample_result(self):
        """Create sample evaluation result"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(accuracy=0.85, success_rate=0.80),
            duration=120.5
        )
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
        
        return EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=request,
            model_results=[model_result],
            summary={"total_models": 1},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    
    def test_format_result(self, formatter, sample_result):
        """Test formatting evaluation result as JSON"""
        result = formatter.format_result(sample_result)
        
        assert isinstance(result, str)
        assert '"evaluation_type": "coding"' in result
        assert '"model_name": "llama3"' in result
        assert '"provider": "openrouter"' in result
    
    def test_format_summary(self, formatter, sample_result):
        """Test formatting summary as JSON"""
        summary = formatter.format_summary(sample_result)
        
        assert isinstance(summary, str)
        assert '"evaluation_type": "coding"' in summary
        assert '"total_models": 1' in summary
        assert '"duration"' in summary
    
    def test_format_model_result(self, formatter):
        """Test formatting model result as JSON"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(accuracy=0.85)
        )
        
        result = formatter.format_model_result(model_result)
        
        assert isinstance(result, str)
        assert '"model_name": "llama3"' in result
        assert '"accuracy": 0.85' in result
    
    def test_format_metrics(self, formatter):
        """Test formatting metrics as JSON"""
        metrics = EvaluationMetrics(
            accuracy=0.85,
            success_rate=0.80,
            total_tests=10,
            passed_tests=8
        )
        
        result = formatter.format_metrics(metrics)
        
        assert isinstance(result, str)
        assert '"accuracy": 0.85' in result
        assert '"success_rate": 0.8' in result
        assert '"total_tests": 10' in result


class TestMarkdownFormatter:
    """Test MarkdownFormatter class"""
    
    @pytest.fixture
    def formatter(self):
        """Create Markdown formatter"""
        return MarkdownFormatter()
    
    @pytest.fixture
    def sample_result(self):
        """Create sample evaluation result"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(accuracy=0.85, success_rate=0.80),
            duration=120.5
        )
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
        
        return EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=request,
            model_results=[model_result],
            summary={"total_models": 1},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    
    def test_format_result(self, formatter, sample_result):
        """Test formatting evaluation result as Markdown"""
        result = formatter.format_result(sample_result)
        
        assert isinstance(result, str)
        assert '# Coding Evaluation Results' in result
        assert '## Summary' in result
        assert '## Overall Metrics' in result
        assert '## Model Results' in result
        assert '### llama3' in result
    
    def test_format_summary(self, formatter, sample_result):
        """Test formatting summary as Markdown"""
        summary = formatter.format_summary(sample_result)
        
        assert isinstance(summary, str)
        assert '# Coding Evaluation Summary' in summary
        assert '## Key Metrics' in summary
        assert '**Models Evaluated**: 1' in summary
    
    def test_format_model_result(self, formatter):
        """Test formatting model result as Markdown"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(accuracy=0.85, success_rate=0.80)
        )
        
        result = formatter.format_model_result(model_result)
        
        assert isinstance(result, str)
        assert '### llama3' in result
        assert '**Provider**: openrouter' in result
        assert '**Metrics**:' in result
        assert 'Success Rate: 80.0%' in result
    
    def test_format_metrics(self, formatter):
        """Test formatting metrics as Markdown"""
        metrics = EvaluationMetrics(
            accuracy=0.85,
            success_rate=0.80,
            total_tests=10,
            passed_tests=8
        )
        
        result = formatter.format_metrics(metrics)
        
        assert isinstance(result, str)
        assert '## Metrics' in result
        assert '**Accuracy**: 85.0%' in result
        assert '**Success Rate**: 80.0%' in result
        assert '**Total Tests**: 10' in result


class TestCSVFormatter:
    """Test CSVFormatter class"""
    
    @pytest.fixture
    def formatter(self):
        """Create CSV formatter"""
        return CSVFormatter()
    
    @pytest.fixture
    def sample_result(self):
        """Create sample evaluation result"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(
                accuracy=0.85,
                success_rate=0.80,
                average_time=2.5,
                total_tests=10,
                passed_tests=8,
                failed_tests=2
            ),
            duration=120.5
        )
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
        
        return EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=request,
            model_results=[model_result],
            summary={"total_models": 1},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    
    def test_format_result(self, formatter, sample_result):
        """Test formatting evaluation result as CSV"""
        result = formatter.format_result(sample_result)
        
        assert isinstance(result, str)
        assert 'Model Name,Provider,Model ID' in result
        assert 'llama3,openrouter,test-id' in result
        assert '80.0%' in result  # Success rate
        assert '85.0%' in result  # Accuracy
    
    def test_format_summary(self, formatter, sample_result):
        """Test formatting summary as CSV"""
        summary = formatter.format_summary(sample_result)
        
        assert isinstance(summary, str)
        assert 'Metric,Value' in summary
        assert 'Evaluation Type,coding' in summary
        assert 'Models Evaluated,1' in summary
    
    def test_format_model_result(self, formatter):
        """Test formatting model result as CSV"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(
                accuracy=0.85,
                success_rate=0.80,
                total_tests=10,
                passed_tests=8
            )
        )
        
        result = formatter.format_model_result(model_result)
        
        assert isinstance(result, str)
        assert 'Metric,Value' in result
        assert 'Model Name,llama3' in result
        assert 'Provider,openrouter' in result
        assert 'Success Rate,80.0%' in result
    
    def test_format_metrics(self, formatter):
        """Test formatting metrics as CSV"""
        metrics = EvaluationMetrics(
            accuracy=0.85,
            success_rate=0.80,
            total_tests=10,
            passed_tests=8
        )
        
        result = formatter.format_metrics(metrics)
        
        assert isinstance(result, str)
        assert 'Metric,Value' in result
        assert 'Accuracy,85.0%' in result
        assert 'Success Rate,80.0%' in result
        assert 'Total Tests,10' in result


class TestConsoleFormatter:
    """Test ConsoleFormatter class"""
    
    @pytest.fixture
    def formatter(self):
        """Create console formatter"""
        return ConsoleFormatter()
    
    @pytest.fixture
    def sample_result(self):
        """Create sample evaluation result"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(
                accuracy=0.85,
                success_rate=0.80,
                average_time=2.5,
                total_tests=10,
                passed_tests=8,
                failed_tests=2
            ),
            duration=120.5
        )
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
        
        return EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=request,
            model_results=[model_result],
            summary={"total_models": 1},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    
    def test_format_result(self, formatter, sample_result):
        """Test formatting evaluation result for console"""
        result = formatter.format_result(sample_result)
        
        assert isinstance(result, str)
        assert 'Coding Evaluation Results' in result
        assert 'Summary' in result
        assert 'Overall Metrics' in result
        assert 'Model Results' in result
        assert 'llama3 (openrouter)' in result
    
    def test_format_summary(self, formatter, sample_result):
        """Test formatting summary for console"""
        summary = formatter.format_summary(sample_result)
        
        assert isinstance(summary, str)
        assert 'Coding Evaluation Summary' in summary
        assert 'Models Evaluated' in summary
        assert 'Overall Success Rate' in summary
        assert '🔍' in summary or 'Models Evaluated' in summary  # Emoji or fallback
    
    def test_format_model_result(self, formatter):
        """Test formatting model result for console"""
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=EvaluationMetrics(
                accuracy=0.85,
                success_rate=0.80,
                average_time=2.5,
                total_tests=10,
                passed_tests=8,
                failed_tests=2
            )
        )
        
        result = formatter.format_model_result(model_result)
        
        assert isinstance(result, str)
        assert 'llama3 (openrouter)' in result
        assert 'Success Rate' in result
        assert 'Accuracy' in result
        assert 'Average Time' in result
    
    def test_format_metrics(self, formatter):
        """Test formatting metrics for console"""
        metrics = EvaluationMetrics(
            accuracy=0.85,
            success_rate=0.80,
            total_tests=10,
            passed_tests=8
        )
        
        result = formatter.format_metrics(metrics)
        
        assert isinstance(result, str)
        assert 'Metrics' in result
        assert 'Accuracy' in result
        assert 'Success Rate' in result
        assert 'Total Tests' in result
    
    def test_colorize_percentage(self, formatter):
        """Test percentage colorization"""
        # Test high percentage (green)
        high_percent = formatter._colorize_percentage(0.85)
        assert '85.0%' in high_percent
        
        # Test medium percentage (yellow)
        medium_percent = formatter._colorize_percentage(0.65)
        assert '65.0%' in medium_percent
        
        # Test low percentage (red)
        low_percent = formatter._colorize_percentage(0.35)
        assert '35.0%' in low_percent
    
    def test_format_progress(self, formatter):
        """Test progress formatting"""
        progress = formatter.format_progress(5, 10, "llama3", "Running test")
        
        assert isinstance(progress, str)
        assert '[5/10]' in progress
        assert 'llama3' in progress
        assert 'Running test' in progress
        assert '50.0%' in progress
    
    def test_create_progress_bar(self, formatter):
        """Test progress bar creation"""
        progress_bar = formatter._create_progress_bar(75.0, width=20)
        
        assert isinstance(progress_bar, str)
        assert '75.0%' in progress_bar
        # Should contain progress characters
        assert '█' in progress_bar or '░' in progress_bar