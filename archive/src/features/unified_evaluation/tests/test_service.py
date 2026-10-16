"""
Tests for unified evaluation service

This module provides tests for the evaluation service that orchestrates
different types of evaluations.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from ..service import EvaluationService
from ..models import (
    EvaluationType,
    ModelSelection,
    OutputConfig,
    EvaluationRequest,
    EvaluationMetrics,
    ModelResult
)


class TestEvaluationService:
    """Test EvaluationService class"""
    
    @pytest.fixture
    def service(self):
        """Create evaluation service instance"""
        return EvaluationService()
    
    @pytest.fixture
    def sample_request(self):
        """Create sample evaluation request"""
        return EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
    
    @pytest.fixture
    def sample_model_config(self):
        """Create sample model configuration"""
        class MockModelConfig:
            def __init__(self):
                self.name = "llama3"
                self.provider = "openrouter"
                self.model_id = "meta-llama/llama-3.3-8b-instruct:free"
                self.capabilities = ["text", "code"]
                self.free = True
                self.enabled = True
        
        return MockModelConfig()
    
    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service.config is not None
        assert service.runners is not None
        assert len(service.runners) == 4  # coding, vision, tools, intelligence
    
    @patch('src.features.unified_evaluation.service.get_unified_config')
    def test_resolve_models_with_specific_models(self, mock_get_config, service):
        """Test resolving models with specific model names"""
        # Mock configuration
        mock_config = Mock()
        mock_model = Mock()
        mock_model.name = "llama3"
        mock_config.resolve_model_name.return_value = mock_model
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        model_selection = ModelSelection(models=["llama3"])
        
        models = service._resolve_models(model_selection)
        
        assert len(models) == 1
        assert models[0].name == "llama3"
        mock_config.resolve_model_name.assert_called_once_with("llama3")
    
    @patch('src.features.unified_evaluation.service.get_unified_config')
    def test_resolve_models_with_filtering(self, mock_get_config, service):
        """Test resolving models with filtering criteria"""
        # Mock configuration
        mock_config = Mock()
        mock_model = Mock()
        mock_model.name = "llama3"
        mock_model.provider = "openrouter"
        mock_model.capabilities = ["text"]
        mock_config.list_models.return_value = [mock_model]
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        model_selection = ModelSelection(
            models=[],
            providers=["openrouter"],
            capabilities=["text"],
            free_only=True
        )
        
        models = service._resolve_models(model_selection)
        
        assert len(models) == 1
        assert models[0].name == "llama3"
        mock_config.list_models.assert_called_once()
    
    @patch('src.features.unified_evaluation.service.get_unified_config')
    def test_resolve_models_not_found(self, mock_get_config, service):
        """Test resolving models when model not found"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = None
        mock_config.list_models.return_value = []
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        model_selection = ModelSelection(models=["nonexistent"])
        
        models = service._resolve_models(model_selection)
        
        assert len(models) == 0
    
    @pytest.mark.asyncio
    @patch('src.features.unified_evaluation.service.get_unified_config')
    async def test_run_single_evaluation_sequential(self, mock_get_config, service, sample_request, sample_model_config):
        """Test running single evaluation sequentially"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = sample_model_config
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        # Mock runner
        mock_runner = AsyncMock()
        mock_metrics = EvaluationMetrics(accuracy=0.85, success_rate=0.80)
        mock_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=mock_metrics
        )
        mock_runner.run_evaluation.return_value = mock_result
        service.runners[EvaluationType.CODING] = mock_runner
        
        # Set request to sequential
        sample_request.parallel = False
        
        # Test the method
        models = [sample_model_config]
        results = await service._run_single_evaluation(sample_request, models)
        
        assert len(results) == 1
        assert results[0].model_name == "llama3"
        mock_runner.run_evaluation.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.features.unified_evaluation.service.get_unified_config')
    async def test_run_single_evaluation_parallel(self, mock_get_config, service, sample_request, sample_model_config):
        """Test running single evaluation in parallel"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = sample_model_config
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        # Mock runner
        mock_runner = AsyncMock()
        mock_metrics = EvaluationMetrics(accuracy=0.85, success_rate=0.80)
        mock_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=mock_metrics
        )
        mock_runner.run_evaluation.return_value = mock_result
        service.runners[EvaluationType.CODING] = mock_runner
        
        # Set request to parallel
        sample_request.parallel = True
        
        # Test the method
        models = [sample_model_config]
        results = await service._run_single_evaluation(sample_request, models)
        
        assert len(results) == 1
        assert results[0].model_name == "llama3"
        mock_runner.run_evaluation.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.features.unified_evaluation.service.get_unified_config')
    async def test_run_single_evaluation_with_exception(self, mock_get_config, service, sample_request, sample_model_config):
        """Test running single evaluation with exception handling"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = sample_model_config
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        # Mock runner that raises exception
        mock_runner = AsyncMock()
        mock_runner.run_evaluation.side_effect = Exception("Test error")
        service.runners[EvaluationType.CODING] = mock_runner
        
        # Set request to sequential for easier testing
        sample_request.parallel = False
        
        # Test the method
        models = [sample_model_config]
        results = await service._run_single_evaluation(sample_request, models)
        
        assert len(results) == 1
        assert results[0].model_name == "llama3"
        assert len(results[0].errors) == 1
        assert "Test error" in results[0].errors[0]
    
    def test_generate_summary_empty_results(self, service, sample_request):
        """Test generating summary with empty results"""
        summary = service._generate_summary([], sample_request)
        
        assert summary == {"message": "No results to summarize"}
    
    def test_generate_summary_with_results(self, service, sample_request):
        """Test generating summary with results"""
        model_results = [
            ModelResult(
                model_name="model1",
                provider="test",
                model_id="id1",
                metrics=EvaluationMetrics(
                    success_rate=0.80,
                    average_time=2.0,
                    total_tests=10,
                    passed_tests=8,
                    failed_tests=2
                )
            ),
            ModelResult(
                model_name="model2",
                provider="test",
                model_id="id2",
                metrics=EvaluationMetrics(
                    success_rate=0.70,
                    average_time=3.0,
                    total_tests=10,
                    passed_tests=7,
                    failed_tests=3
                )
            )
        ]
        
        summary = service._generate_summary(model_results, sample_request)
        
        assert summary["evaluation_type"] == "coding"
        assert summary["models_evaluated"] == 2
        assert summary["total_tests"] == 20
        assert summary["total_passed"] == 15
        assert summary["total_failed"] == 5
        assert summary["overall_success_rate"] == 0.75  # 15/20
        assert summary["average_success_rate"] == 0.75  # (0.80 + 0.70) / 2
        assert summary["best_model"]["name"] == "model1"
        assert summary["worst_model"]["name"] == "model2"
    
    @patch('src.features.unified_evaluation.service.get_unified_config')
    def test_get_available_models(self, mock_get_config, service):
        """Test getting available models"""
        # Mock configuration
        mock_config = Mock()
        mock_model = Mock(
            name="llama3",
            provider="openrouter",
            model_id="test-id",
            capabilities=["text", "code"],
            free=True,
            enabled=True
        )
        mock_config.list_models.return_value = [mock_model]
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        models = service.get_available_models()
        
        assert len(models) == 1
        assert models[0]["name"] == mock_model.name
        assert models[0]["provider"] == mock_model.provider
        assert models[0]["capabilities"] == mock_model.capabilities
        assert models[0]["free"] == mock_model.free
        assert models[0]["enabled"] == mock_model.enabled
    
    @patch('src.features.unified_evaluation.service.get_unified_config')
    def test_validate_request_success(self, mock_get_config, service, sample_request):
        """Test successful request validation"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = Mock(name="llama3")
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        errors = service.validate_request(sample_request)
        
        assert len(errors) == 0
    
    @patch('src.features.unified_evaluation.service.get_unified_config')
    def test_validate_request_no_models(self, mock_get_config, service, sample_request):
        """Test request validation with no models found"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = None
        mock_config.list_models.return_value = []
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        errors = service.validate_request(sample_request)
        
        assert len(errors) > 0
        assert any("No models found" in error for error in errors)
    
    def test_validate_request_invalid_languages(self, service):
        """Test request validation with invalid languages"""
        request = EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig(),
            languages=["invalid_language"]
        )
        
        errors = service.validate_request(request)
        
        assert len(errors) > 0
        assert any("Invalid languages" in error for error in errors)
    
    def test_validate_request_vision_no_capable_models(self, service):
        """Test request validation for vision with no vision-capable models"""
        request = EvaluationRequest(
            evaluation_type=EvaluationType.VISION,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
        
        # Mock service to resolve models but none have vision capability
        with patch.object(service, '_resolve_models') as mock_resolve:
            mock_model = Mock(capabilities=["text"])
            mock_resolve.return_value = [mock_model]
            
            errors = service.validate_request(request)
            
            assert len(errors) > 0
            assert any("No vision-capable models" in error for error in errors)
    
    @pytest.mark.asyncio
    @patch('src.features.unified_evaluation.service.get_unified_config')
    async def test_run_evaluation_full_flow(self, mock_get_config, service, sample_request, sample_model_config):
        """Test full evaluation flow"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = sample_model_config
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        # Mock runner
        mock_runner = AsyncMock()
        mock_metrics = EvaluationMetrics(accuracy=0.85, success_rate=0.80)
        mock_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=mock_metrics
        )
        mock_runner.run_evaluation.return_value = mock_result
        service.runners[EvaluationType.CODING] = mock_runner
        
        # Run evaluation
        result = await service.run_evaluation(sample_request)
        
        assert result.evaluation_type == EvaluationType.CODING
        assert len(result.model_results) == 1
        assert result.model_results[0].model_name == "llama3"
        assert result.summary is not None
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration > 0
    
    @pytest.mark.asyncio
    @patch('src.features.unified_evaluation.service.get_unified_config')
    async def test_run_evaluation_no_models(self, mock_get_config, service, sample_request):
        """Test evaluation with no models found"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = None
        mock_config.list_models.return_value = []
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        # Should raise exception
        with pytest.raises(ValueError, match="No models found"):
            await service.run_evaluation(sample_request)
    
    @pytest.mark.asyncio
    @patch('src.features.unified_evaluation.service.get_unified_config')
    async def test_run_comprehensive_evaluation(self, mock_get_config, service, sample_model_config):
        """Test comprehensive evaluation (all types)"""
        # Mock configuration
        mock_config = Mock()
        mock_config.resolve_model_name.return_value = sample_model_config
        mock_get_config.return_value = mock_config
        service.config = mock_config
        
        # Mock all runners
        mock_metrics = EvaluationMetrics(accuracy=0.85, success_rate=0.80)
        mock_result = ModelResult(
            model_name="llama3",
            provider="openrouter",
            model_id="test-id",
            metrics=mock_metrics
        )
        
        for eval_type in [EvaluationType.CODING, EvaluationType.VISION, 
                         EvaluationType.TOOLS, EvaluationType.INTELLIGENCE]:
            mock_runner = AsyncMock()
            mock_runner.run_evaluation.return_value = mock_result
            service.runners[eval_type] = mock_runner
        
        # Create comprehensive request
        request = EvaluationRequest(
            evaluation_type=EvaluationType.ALL,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig(),
            parallel=False
        )
        
        # Run comprehensive evaluation
        models = [sample_model_config]
        results = await service._run_comprehensive_evaluation(request, models)
        
        assert len(results) == 1
        assert results[0].model_name == "llama3"
        # Should have details for all evaluation types
        assert len(results[0].details) == 4