"""
Tests for unified evaluation runners

This module provides tests for the evaluation runners.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from ..runners import CodingRunner, VisionRunner, ToolsRunner, IntelligenceRunner
from ..models import EvaluationRequest, ModelSelection, OutputConfig, EvaluationType


class TestCodingRunner:
    """Test CodingRunner class"""
    
    @pytest.fixture
    def runner(self):
        """Create coding runner"""
        return CodingRunner()
    
    @pytest.fixture
    def model_config(self):
        """Create mock model config"""
        mock_config = Mock()
        mock_config.name = "llama3"
        mock_config.provider = "openrouter"
        mock_config.model_id = "test-id"
        mock_config.capabilities = ["text", "code"]
        return mock_config
    
    @pytest.fixture
    def eval_request(self):
        """Create sample request"""
        return EvaluationRequest(
            evaluation_type=EvaluationType.CODING,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
    
    @pytest.mark.asyncio
    async def test_run_evaluation_basic(self, runner, model_config, eval_request):
        """Test basic evaluation run"""
        with patch.object(runner, '_get_problems') as mock_get_problems:
            mock_problem = Mock()
            mock_problem.id = "test_problem"
            mock_problem.languages = [Mock(value="python")]
            mock_get_problems.return_value = [mock_problem]
            
            with patch.object(runner, '_run_problem_evaluations') as mock_run:
                mock_run.return_value = [{"problem_id": "test_problem", "score": 0.8}]
                
                result = await runner.run_evaluation(model_config, eval_request)
                
                assert result.model_name == "llama3"
                assert result.provider == "openrouter"
                assert result.model_id == "test-id"
                assert result.metrics is not None
    
    @pytest.mark.asyncio
    async def test_run_evaluation_with_exception(self, runner, model_config, eval_request):
        """Test evaluation with exception"""
        with patch.object(runner, '_get_problems') as mock_get_problems:
            mock_get_problems.side_effect = Exception("Test error")
            
            result = await runner.run_evaluation(model_config, eval_request)
            
            assert result.model_name == "llama3"
            assert len(result.errors) == 1
            assert "Test error" in result.errors[0]
    
    def test_filter_by_language(self, runner):
        """Test filtering problems by language"""
        mock_problem1 = Mock()
        mock_problem1.languages = [Mock(value="python"), Mock(value="javascript")]
        
        mock_problem2 = Mock()
        mock_problem2.languages = [Mock(value="java")]
        
        problems = [mock_problem1, mock_problem2]
        
        filtered = runner._filter_by_language(problems, ["python"])
        
        assert len(filtered) == 1
        assert filtered[0] == mock_problem1
    
    def test_get_test_languages(self, runner):
        """Test getting test languages for a problem"""
        mock_problem = Mock()
        mock_problem.languages = [Mock(value="python"), Mock(value="javascript")]
        
        # Test with requested languages
        languages = runner._get_test_languages(mock_problem, ["python"])
        assert languages == ["python"]
        
        # Test without requested languages
        languages = runner._get_test_languages(mock_problem, None)
        assert "python" in languages
        assert "javascript" in languages


class TestVisionRunner:
    """Test VisionRunner class"""
    
    @pytest.fixture
    def runner(self):
        """Create vision runner"""
        return VisionRunner()
    
    @pytest.fixture
    def model_config(self):
        """Create mock model config"""
        mock_config = Mock()
        mock_config.name = "llama3-vision"
        mock_config.provider = "openrouter"
        mock_config.model_id = "test-id"
        mock_config.capabilities = ["text", "vision"]
        return mock_config
    
    @pytest.fixture
    def eval_request(self):
        """Create sample request"""
        return EvaluationRequest(
            evaluation_type=EvaluationType.VISION,
            model_selection=ModelSelection(models=["llama3-vision"]),
            output_config=OutputConfig()
        )
    
    @pytest.mark.asyncio
    async def test_run_evaluation_basic(self, runner, model_config, eval_request):
        """Test basic vision evaluation"""
        with patch.object(runner, '_get_test_cases') as mock_get_cases:
            mock_get_cases.return_value = [{"id": "test_case"}]
            
            with patch.object(runner, '_run_vision_evaluations') as mock_run:
                mock_run.return_value = [{"test_case_id": "test_case", "score": 0.8}]
                
                result = await runner.run_evaluation(model_config, eval_request)
                
                assert result.model_name == "llama3-vision"
                assert result.provider == "openrouter"
                assert result.metrics is not None
    
    @pytest.mark.asyncio
    async def test_run_evaluation_no_vision_capability(self, runner, eval_request):
        """Test evaluation with model that doesn't support vision"""
        model_config = Mock()
        model_config.name = "llama3"
        model_config.provider = "openrouter"
        model_config.model_id = "test-id"
        model_config.capabilities = ["text"]
        
        result = await runner.run_evaluation(model_config, eval_request)
        
        assert result.model_name == "llama3"
        assert len(result.errors) == 1
        assert "does not support vision" in result.errors[0]
    
    def test_get_default_test_cases(self, runner):
        """Test getting default test cases"""
        test_cases = runner._get_default_test_cases()
        
        assert len(test_cases) > 0
        assert any(tc.get('category') == 'description' for tc in test_cases)
        assert any(tc.get('category') == 'counting' for tc in test_cases)


class TestToolsRunner:
    """Test ToolsRunner class"""
    
    @pytest.fixture
    def runner(self):
        """Create tools runner"""
        return ToolsRunner()
    
    @pytest.fixture
    def model_config(self):
        """Create mock model config"""
        mock_config = Mock()
        mock_config.name = "llama3"
        mock_config.provider = "openrouter"
        mock_config.model_id = "test-id"
        mock_config.capabilities = ["text", "function_calling"]
        return mock_config
    
    @pytest.fixture
    def eval_request(self):
        """Create sample request"""
        return EvaluationRequest(
            evaluation_type=EvaluationType.TOOLS,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
    
    @pytest.mark.asyncio
    async def test_run_evaluation_basic(self, runner, model_config, eval_request):
        """Test basic tools evaluation"""
        with patch.object(runner, '_get_test_scenarios') as mock_get_scenarios:
            mock_get_scenarios.return_value = [{"id": "test_scenario"}]
            
            with patch.object(runner, '_run_tool_evaluations') as mock_run:
                mock_run.return_value = [{"scenario_id": "test_scenario", "score": 0.8}]
                
                result = await runner.run_evaluation(model_config, eval_request)
                
                assert result.model_name == "llama3"
                assert result.provider == "openrouter"
                assert result.metrics is not None
    
    def test_get_default_scenarios(self, runner):
        """Test getting default scenarios"""
        scenarios = runner._get_default_scenarios()
        
        assert len(scenarios) > 0
        assert any(s.get('category') == 'math' for s in scenarios)
        assert any(s.get('category') == 'api' for s in scenarios)
        assert any(s.get('category') == 'system' for s in scenarios)


class TestIntelligenceRunner:
    """Test IntelligenceRunner class"""
    
    @pytest.fixture
    def runner(self):
        """Create intelligence runner"""
        return IntelligenceRunner()
    
    @pytest.fixture
    def model_config(self):
        """Create mock model config"""
        mock_config = Mock()
        mock_config.name = "llama3"
        mock_config.provider = "openrouter"
        mock_config.model_id = "test-id"
        mock_config.capabilities = ["text", "reasoning"]
        return mock_config
    
    @pytest.fixture
    def eval_request(self):
        """Create sample request"""
        return EvaluationRequest(
            evaluation_type=EvaluationType.INTELLIGENCE,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
    
    @pytest.mark.asyncio
    async def test_run_evaluation_basic(self, runner, model_config, eval_request):
        """Test basic intelligence evaluation"""
        with patch.object(runner, '_get_test_categories') as mock_get_categories:
            mock_get_categories.return_value = ["logic", "reasoning"]
            
            with patch.object(runner, '_run_intelligence_evaluations') as mock_run:
                mock_run.return_value = [
                    {"test_id": "test1", "category": "logic", "score": 0.8},
                    {"test_id": "test2", "category": "reasoning", "score": 0.7}
                ]
                
                result = await runner.run_evaluation(model_config, eval_request)
                
                assert result.model_name == "llama3"
                assert result.provider == "openrouter"
                assert result.metrics is not None
    
    def test_get_test_categories_default(self, runner):
        """Test getting default test categories"""
        request = EvaluationRequest(
            evaluation_type=EvaluationType.INTELLIGENCE,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig()
        )
        
        categories = runner._get_test_categories(request)
        
        assert len(categories) > 0
        assert "logic" in categories
        assert "creative" in categories
        assert "pattern" in categories
        assert "reasoning" in categories
        assert "math" in categories
    
    def test_get_test_categories_filtered(self, runner):
        """Test getting filtered test categories"""
        request = EvaluationRequest(
            evaluation_type=EvaluationType.INTELLIGENCE,
            model_selection=ModelSelection(models=["llama3"]),
            output_config=OutputConfig(),
            categories=["logic", "reasoning"]
        )
        
        categories = runner._get_test_categories(request)
        
        assert len(categories) == 2
        assert "logic" in categories
        assert "reasoning" in categories
        assert "creative" not in categories
    
    def test_get_tests_for_category(self, runner):
        """Test getting tests for a specific category"""
        logic_tests = runner._get_tests_for_category("logic")
        
        assert len(logic_tests) > 0
        assert any(test.get('id') == 'logical_reasoning' for test in logic_tests)
        
        math_tests = runner._get_tests_for_category("math")
        
        assert len(math_tests) > 0
        assert any(test.get('id') == 'arithmetic' for test in math_tests)
        
        unknown_tests = runner._get_tests_for_category("unknown")
        
        assert len(unknown_tests) == 0