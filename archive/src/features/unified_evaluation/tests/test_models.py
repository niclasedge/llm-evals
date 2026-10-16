"""
Tests for unified evaluation models

This module provides tests for the data models used in the unified evaluation system.
"""

import pytest
from datetime import datetime
from pathlib import Path

from ..models import (
    EvaluationType,
    OutputFormat,
    ModelSelection,
    OutputConfig,
    EvaluationRequest,
    EvaluationMetrics,
    ModelResult,
    EvaluationResult,
    ProgressUpdate
)


class TestEvaluationType:
    """Test EvaluationType enum"""
    
    def test_evaluation_types(self):
        """Test that all evaluation types are defined"""
        assert EvaluationType.CODING.value == "coding"
        assert EvaluationType.VISION.value == "vision"
        assert EvaluationType.TOOLS.value == "tools"
        assert EvaluationType.INTELLIGENCE.value == "intelligence"
        assert EvaluationType.ALL.value == "all"


class TestOutputFormat:
    """Test OutputFormat enum"""
    
    def test_output_formats(self):
        """Test that all output formats are defined"""
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.CSV.value == "csv"
        assert OutputFormat.CONSOLE.value == "console"


class TestModelSelection:
    """Test ModelSelection class"""
    
    def test_default_model_selection(self):
        """Test default model selection"""
        selection = ModelSelection()
        assert selection.models == ["llama3"]  # Default model
        assert selection.providers == []
        assert selection.capabilities == []
        assert selection.free_only is False
        assert selection.enabled_only is True
    
    def test_custom_model_selection(self):
        """Test custom model selection"""
        selection = ModelSelection(
            models=["gpt-4", "claude-3"],
            providers=["openai", "anthropic"],
            capabilities=["text", "code"],
            free_only=True,
            enabled_only=False
        )
        assert selection.models == ["gpt-4", "claude-3"]
        assert selection.providers == ["openai", "anthropic"]
        assert selection.capabilities == ["text", "code"]
        assert selection.free_only is True
        assert selection.enabled_only is False
    
    def test_empty_model_selection(self):
        """Test empty model selection gets default"""
        selection = ModelSelection(models=[], providers=[])
        assert selection.models == ["llama3"]  # Should get default


class TestOutputConfig:
    """Test OutputConfig class"""
    
    def test_default_output_config(self):
        """Test default output configuration"""
        config = OutputConfig()
        assert config.format == OutputFormat.CONSOLE
        assert config.file_path is None
        assert config.verbose is False
        assert config.progress is True
    
    def test_custom_output_config(self):
        """Test custom output configuration"""
        config = OutputConfig(
            format=OutputFormat.JSON,
            file_path="/tmp/results.json",
            verbose=True,
            progress=False
        )
        assert config.format == OutputFormat.JSON
        assert config.file_path == Path("/tmp/results.json")
        assert config.verbose is True
        assert config.progress is False
    
    def test_string_path_conversion(self):
        """Test string path is converted to Path object"""
        config = OutputConfig(file_path="/tmp/test.json")
        assert isinstance(config.file_path, Path)
        assert str(config.file_path) == "/tmp/test.json"


class TestEvaluationRequest:
    """Test EvaluationRequest class"""
    
    def test_basic_evaluation_request(self):
        """Test basic evaluation request"""
        model_selection = ModelSelection(models=["llama3"])
        output_config = OutputConfig(format=OutputFormat.JSON)
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=model_selection,
            output_config=output_config
        )
        
        assert request.evaluation_type == EvaluationType.CODING
        assert request.model_selection == model_selection
        assert request.output_config == output_config
        assert request.timeout == 300
        assert request.max_retries == 3
        assert request.parallel is True
    
    def test_coding_evaluation_request(self):
        """Test coding evaluation request with specific parameters"""
        model_selection = ModelSelection(models=["llama3"])
        output_config = OutputConfig()
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=model_selection,
            output_config=output_config,
            problems=["fibonacci", "palindrome"],
            languages=["python", "javascript"],
            difficulty="medium"
        )
        
        assert request.problems == ["fibonacci", "palindrome"]
        assert request.languages == ["python", "javascript"]
        assert request.difficulty == "medium"
    
    def test_vision_evaluation_request(self):
        """Test vision evaluation request"""
        model_selection = ModelSelection(models=["llama3-vision"])
        output_config = OutputConfig()
        
        request = EvaluationRequest(
            evaluation_type=EvaluationType.VISION,
            model_selection=model_selection,
            output_config=output_config,
            images=["test1.jpg", "test2.png"],
            categories=["description", "counting"]
        )
        
        assert request.images == ["test1.jpg", "test2.png"]
        assert request.categories == ["description", "counting"]
    
    def test_invalid_model_selection_type(self):
        """Test invalid model selection type raises error"""
        with pytest.raises(ValueError, match="model_selection must be ModelSelection instance"):
            EvaluationRequest(
                evaluation_type=EvaluationType.CODING,
                model_selection="invalid",
                output_config=OutputConfig()
            )
    
    def test_invalid_output_config_type(self):
        """Test invalid output config type raises error"""
        with pytest.raises(ValueError, match="output_config must be OutputConfig instance"):
            EvaluationRequest(
                evaluation_type=EvaluationType.CODING,
                model_selection=ModelSelection(),
                output_config="invalid"
            )


class TestEvaluationMetrics:
    """Test EvaluationMetrics class"""
    
    def test_default_metrics(self):
        """Test default metrics"""
        metrics = EvaluationMetrics()
        assert metrics.accuracy is None
        assert metrics.success_rate is None
        assert metrics.average_time is None
        assert metrics.total_tests == 0
        assert metrics.passed_tests == 0
        assert metrics.failed_tests == 0
        assert metrics.error_tests == 0
    
    def test_custom_metrics(self):
        """Test custom metrics"""
        metrics = EvaluationMetrics(
            accuracy=0.85,
            success_rate=0.80,
            average_time=2.5,
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            error_tests=0
        )
        
        assert metrics.accuracy == 0.85
        assert metrics.success_rate == 0.80
        assert metrics.average_time == 2.5
        assert metrics.total_tests == 10
        assert metrics.passed_tests == 8
        assert metrics.failed_tests == 2
        assert metrics.error_tests == 0
    
    def test_metrics_to_dict(self):
        """Test metrics to dict conversion"""
        metrics = EvaluationMetrics(
            accuracy=0.85,
            success_rate=0.80,
            total_tests=10,
            passed_tests=8
        )
        
        result_dict = metrics.to_dict()
        assert result_dict["accuracy"] == 0.85
        assert result_dict["success_rate"] == 0.80
        assert result_dict["total_tests"] == 10
        assert result_dict["passed_tests"] == 8


class TestModelResult:
    """Test ModelResult class"""
    
    def test_basic_model_result(self):
        """Test basic model result"""
        metrics = EvaluationMetrics(accuracy=0.85, success_rate=0.80)
        
        result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="meta-llama/llama-3.3-8b-instruct:free",
            metrics=metrics
        )
        
        assert result.model_name == "llama3"
        assert result.provider == "openrouter"
        assert result.model_id == "meta-llama/llama-3.3-8b-instruct:free"
        assert result.metrics == metrics
        assert result.details == {}
        assert result.errors == []
        assert result.duration is None
    
    def test_model_result_with_errors(self):
        """Test model result with errors"""
        metrics = EvaluationMetrics()
        errors = ["Connection timeout", "Invalid response"]
        
        result = ModelResult(
            model_name="test-model",
            provider="test",
            model_id="test-id",
            metrics=metrics,
            errors=errors
        )
        
        assert result.errors == errors
    
    def test_model_result_to_dict(self):
        """Test model result to dict conversion"""
        metrics = EvaluationMetrics(accuracy=0.85)
        
        result = ModelResult(
            model_name="test-model",
            provider="test",
            model_id="test-id",
            metrics=metrics,
            duration=120.5
        )
        
        result_dict = result.to_dict()
        assert result_dict["model_name"] == "test-model"
        assert result_dict["provider"] == "test"
        assert result_dict["model_id"] == "test-id"
        assert result_dict["duration"] == 120.5
        assert "metrics" in result_dict


class TestEvaluationResult:
    """Test EvaluationResult class"""
    
    def test_basic_evaluation_result(self):
        """Test basic evaluation result"""
        model_selection = ModelSelection(models=["llama3"])
        output_config = OutputConfig()
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=model_selection,
            output_config=output_config
        )
        
        metrics = EvaluationMetrics(accuracy=0.85, success_rate=0.80)
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=metrics
        )
        
        started_at = datetime.now()
        completed_at = datetime.now()
        
        result = EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=request,
            model_results=[model_result],
            summary={"total_models": 1},
            started_at=started_at,
            completed_at=completed_at
        )
        
        assert result.evaluation_type == EvaluationType.CODING
        assert result.request == request
        assert len(result.model_results) == 1
        assert result.model_results[0] == model_result
        assert result.summary == {"total_models": 1}
        assert result.started_at == started_at
        assert result.completed_at == completed_at
    
    def test_evaluation_result_duration(self):
        """Test evaluation result duration calculation"""
        started_at = datetime(2024, 1, 1, 12, 0, 0)
        completed_at = datetime(2024, 1, 1, 12, 2, 30)  # 2.5 minutes later
        
        result = EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=None,
            model_results=[],
            summary={},
            started_at=started_at,
            completed_at=completed_at
        )
        
        assert result.duration == 150.0  # 2.5 minutes = 150 seconds
    
    def test_get_best_model(self):
        """Test getting the best performing model"""
        model_results = [
            ModelResult(
                model_name="model1",
                provider="test",
                model_id="id1",
                metrics=EvaluationMetrics(success_rate=0.70)
            ),
            ModelResult(
                model_name="model2",
                provider="test",
                model_id="id2",
                metrics=EvaluationMetrics(success_rate=0.85)
            ),
            ModelResult(
                model_name="model3",
                provider="test",
                model_id="id3",
                metrics=EvaluationMetrics(success_rate=0.60)
            )
        ]
        
        result = EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=None,
            model_results=model_results,
            summary={},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        best_model = result.get_best_model()
        assert best_model.model_name == "model2"
        assert best_model.metrics.success_rate == 0.85
    
    def test_get_best_model_empty_results(self):
        """Test getting best model with no results"""
        result = EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=None,
            model_results=[],
            summary={},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        best_model = result.get_best_model()
        assert best_model is None
    
    def test_get_average_metrics(self):
        """Test getting average metrics"""
        model_results = [
            ModelResult(
                model_name="model1",
                provider="test",
                model_id="id1",
                metrics=EvaluationMetrics(
                    accuracy=0.80,
                    success_rate=0.75,
                    average_time=2.0,
                    total_tests=10,
                    passed_tests=8
                )
            ),
            ModelResult(
                model_name="model2",
                provider="test",
                model_id="id2",
                metrics=EvaluationMetrics(
                    accuracy=0.70,
                    success_rate=0.65,
                    average_time=3.0,
                    total_tests=10,
                    passed_tests=7
                )
            )
        ]
        
        result = EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=None,
            model_results=model_results,
            summary={},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        avg_metrics = result.get_average_metrics()
        assert avg_metrics.accuracy == 0.75  # (0.80 + 0.70) / 2
        assert avg_metrics.success_rate == 0.70  # (0.75 + 0.65) / 2
        assert avg_metrics.average_time == 2.5  # (2.0 + 3.0) / 2
        assert avg_metrics.total_tests == 20  # 10 + 10
        assert avg_metrics.passed_tests == 15  # 8 + 7
    
    def test_evaluation_result_to_dict(self):
        """Test evaluation result to dict conversion"""
        model_selection = ModelSelection(models=["llama3"])
        output_config = OutputConfig()
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=model_selection,
            output_config=output_config
        )
        
        metrics = EvaluationMetrics(accuracy=0.85)
        model_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=metrics
        )
        
        result = EvaluationResult(
            evaluation_type=EvaluationType.CODING,
            request=request,
            model_results=[model_result],
            summary={"total_models": 1},
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        result_dict = result.to_dict()
        assert result_dict["evaluation_type"] == "coding"
        assert "model_results" in result_dict
        assert "summary" in result_dict
        assert "started_at" in result_dict
        assert "completed_at" in result_dict
        assert "duration" in result_dict


class TestProgressUpdate:
    """Test ProgressUpdate class"""
    
    def test_basic_progress_update(self):
        """Test basic progress update"""
        update = ProgressUpdate(
            current_step=5,
            total_steps=10,
            current_model="llama3",
            current_test="fibonacci",
            message="Running test"
        )
        
        assert update.current_step == 5
        assert update.total_steps == 10
        assert update.current_model == "llama3"
        assert update.current_test == "fibonacci"
        assert update.message == "Running test"
    
    def test_progress_percent(self):
        """Test progress percentage calculation"""
        update = ProgressUpdate(
            current_step=5,
            total_steps=10,
            current_model="test",
            current_test="test",
            message="test"
        )
        
        assert update.progress_percent == 50.0
    
    def test_progress_percent_zero_total(self):
        """Test progress percentage with zero total"""
        update = ProgressUpdate(
            current_step=5,
            total_steps=0,
            current_model="test",
            current_test="test",
            message="test"
        )
        
        assert update.progress_percent == 0
    
    def test_progress_update_str(self):
        """Test progress update string representation"""
        update = ProgressUpdate(
            current_step=3,
            total_steps=10,
            current_model="llama3",
            current_test="test",
            message="Processing"
        )
        
        str_repr = str(update)
        assert "[3/10]" in str_repr
        assert "llama3" in str_repr
        assert "Processing" in str_repr