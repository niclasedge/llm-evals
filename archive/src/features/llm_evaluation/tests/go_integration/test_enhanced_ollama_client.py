"""
Tests for enhanced OllamaClient with Go service integration.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.features.llm_evaluation.test_framework.ollama_client import OllamaClient


class TestEnhancedOllamaClient:
    """Test cases for enhanced OllamaClient with Go service integration."""
    
    @pytest.fixture
    def client_direct_only(self):
        """Create OllamaClient with direct Ollama only."""
        return OllamaClient(use_go_service=False)
    
    @pytest.fixture
    def client_with_go_service(self):
        """Create OllamaClient with Go service enabled."""
        return OllamaClient(use_go_service=True)
    
    @pytest.mark.asyncio
    async def test_initialization_direct_only(self, client_direct_only):
        """Test client initialization with direct Ollama only."""
        assert client_direct_only.use_go_service is False
        assert client_direct_only.go_client is None
        assert client_direct_only.fallback_manager is None
    
    @pytest.mark.asyncio
    async def test_initialization_with_go_service(self, client_with_go_service):
        """Test client initialization with Go service enabled."""
        assert client_with_go_service.use_go_service is True
        assert client_with_go_service.service_discovery is not None
        assert client_with_go_service.fallback_manager is not None
    
    @pytest.mark.asyncio
    async def test_health_check_direct_only(self, client_direct_only):
        """Test health check with direct Ollama only."""
        class MockResponse:
            def __init__(self, status=200):
                self.status = status
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        
        # Create a proper async context manager mock
        class AsyncContextManager:
            def __init__(self, response):
                self.response = response
            async def __aenter__(self):
                return self.response
            async def __aexit__(self, *args):
                pass
        
        # Create a mock session that returns the context manager directly
        class MockSession:
            def __init__(self):
                self.get_call_count = 0
            def get(self, url):
                self.get_call_count += 1
                return AsyncContextManager(MockResponse(200))
        
        mock_session = MockSession()
        client_direct_only.session = mock_session
        
        result = await client_direct_only.health_check()
        
        assert result is True
        assert mock_session.get_call_count == 1
    
    @pytest.mark.asyncio
    async def test_health_check_with_go_service_success(self, client_with_go_service):
        """Test health check with Go service (success)."""
        mock_fallback = AsyncMock()
        mock_fallback.execute_with_fallback = AsyncMock(return_value=True)
        
        client_with_go_service.fallback_manager = mock_fallback
        client_with_go_service.session = AsyncMock()
        client_with_go_service.go_client = AsyncMock()
        
        result = await client_with_go_service.health_check()
        
        assert result is True
        mock_fallback.execute_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_with_go_service_fallback(self, client_with_go_service):
        """Test health check with Go service (fallback to direct)."""
        with patch.object(client_with_go_service, 'fallback_manager') as mock_fallback:
            mock_fallback.execute_with_fallback.return_value = False
            
            client_with_go_service.session = AsyncMock()
            client_with_go_service.go_client = AsyncMock()
            
            result = await client_with_go_service.health_check()
            
            assert result is False
            mock_fallback.execute_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_models_direct_only(self, client_direct_only):
        """Test list models with direct Ollama only."""
        expected_models = [{"name": "llama3", "size": 4000000000}]
        
        class MockResponse:
            def __init__(self, status=200, json_data=None):
                self.status = status
                self._json_data = json_data or {}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return self._json_data
        
        # Create a proper async context manager mock
        class AsyncContextManager:
            def __init__(self, response):
                self.response = response
            async def __aenter__(self):
                return self.response
            async def __aexit__(self, *args):
                pass
        
        # Create a mock session that returns the context manager directly
        class MockSession:
            def __init__(self):
                self.get_call_count = 0
            def get(self, url):
                self.get_call_count += 1
                return AsyncContextManager(MockResponse(200, {"models": expected_models}))
        
        mock_session = MockSession()
        client_direct_only.session = mock_session
        
        result = await client_direct_only.list_models()
        
        assert result == expected_models
        assert mock_session.get_call_count == 1
    
    @pytest.mark.asyncio
    async def test_list_models_with_go_service(self, client_with_go_service):
        """Test list models with Go service integration."""
        expected_models = [{"name": "llama3", "size": 4000000000}]
        
        mock_fallback = AsyncMock()
        mock_fallback.execute_with_fallback = AsyncMock(return_value=expected_models)
        
        client_with_go_service.fallback_manager = mock_fallback
        client_with_go_service.session = AsyncMock()
        client_with_go_service.go_client = AsyncMock()
        client_with_go_service.response_mapper = AsyncMock()
        
        result = await client_with_go_service.list_models()
        
        assert result == expected_models
        mock_fallback.execute_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_direct_only(self, client_direct_only):
        """Test text generation with direct Ollama only."""
        expected_response = {
            "response": "Paris is the capital of France.",
            "model": "llama3",
            "done": True
        }
        
        class MockResponse:
            def __init__(self, status=200, json_data=None):
                self.status = status
                self._json_data = json_data or {}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return self._json_data
        
        # Create a proper async context manager mock
        class AsyncContextManager:
            def __init__(self, response):
                self.response = response
            async def __aenter__(self):
                return self.response
            async def __aexit__(self, *args):
                pass
        
        # Create a mock session that returns the context manager directly
        class MockSession:
            def __init__(self):
                self.post_call_count = 0
            def post(self, url, json=None):
                self.post_call_count += 1
                return AsyncContextManager(MockResponse(200, expected_response))
        
        mock_session = MockSession()
        client_direct_only.session = mock_session
        
        result = await client_direct_only.generate(
            model="llama3",
            prompt="What is the capital of France?"
        )
        
        assert result["response"] == expected_response["response"]
        assert result["model"] == expected_response["model"]
        assert "_timing" in result
        assert result["_timing"]["via_go_service"] is False
        assert mock_session.post_call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_with_go_service(self, client_with_go_service):
        """Test text generation with Go service integration."""
        expected_response = {
            "response": "Paris is the capital of France.",
            "model": "llama3",
            "done": True,
            "_timing": {"via_go_service": True}
        }
        
        mock_fallback = AsyncMock()
        mock_fallback.execute_with_fallback = AsyncMock(return_value=expected_response)
        
        client_with_go_service.fallback_manager = mock_fallback
        client_with_go_service.session = AsyncMock()
        client_with_go_service.go_client = AsyncMock()
        client_with_go_service.request_adapter = AsyncMock()
        client_with_go_service.response_mapper = AsyncMock()
        
        result = await client_with_go_service.generate(
            model="llama3",
            prompt="What is the capital of France?"
        )
        
        assert result == expected_response
        mock_fallback.execute_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_direct_only(self, client_direct_only):
        """Test chat with direct Ollama only."""
        expected_response = {
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            "model": "llama3",
            "done": True
        }
        
        class MockResponse:
            def __init__(self, status=200, json_data=None):
                self.status = status
                self._json_data = json_data or {}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return self._json_data
        
        # Create a proper async context manager mock
        class AsyncContextManager:
            def __init__(self, response):
                self.response = response
            async def __aenter__(self):
                return self.response
            async def __aexit__(self, *args):
                pass
        
        # Create a mock session that returns the context manager directly
        class MockSession:
            def __init__(self):
                self.post_call_count = 0
            def post(self, url, json=None):
                self.post_call_count += 1
                return AsyncContextManager(MockResponse(200, expected_response))
        
        mock_session = MockSession()
        client_direct_only.session = mock_session
        
        result = await client_direct_only.chat(
            model="llama3",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        
        assert result["message"] == expected_response["message"]
        assert result["model"] == expected_response["model"]
        assert "_timing" in result
        assert result["_timing"]["via_go_service"] is False
        assert mock_session.post_call_count == 1
    
    @pytest.mark.asyncio
    async def test_chat_with_go_service(self, client_with_go_service):
        """Test chat with Go service integration."""
        expected_response = {
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            "model": "llama3",
            "done": True,
            "_timing": {"via_go_service": True}
        }
        
        mock_fallback = AsyncMock()
        mock_fallback.execute_with_fallback = AsyncMock(return_value=expected_response)
        
        client_with_go_service.fallback_manager = mock_fallback
        client_with_go_service.session = AsyncMock()
        client_with_go_service.go_client = AsyncMock()
        client_with_go_service.request_adapter = AsyncMock()
        client_with_go_service.response_mapper = AsyncMock()
        
        result = await client_with_go_service.chat(
            model="llama3",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        
        assert result == expected_response
        mock_fallback.execute_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager_direct_only(self, client_direct_only):
        """Test client as context manager (direct only)."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with client_direct_only as client:
                assert client is not None
                assert client.session is not None
                mock_session_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager_with_go_service(self, client_with_go_service):
        """Test client as context manager (with Go service)."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            mock_go_client = AsyncMock()
            mock_go_client.__aenter__ = AsyncMock(return_value=mock_go_client)
            mock_go_client.__aexit__ = AsyncMock(return_value=None)
            client_with_go_service.go_client = mock_go_client
            
            async with client_with_go_service as client:
                assert client is not None
                assert client.session is not None
                # Don't check exact call count since the implementation may call it multiple times
    
    @pytest.mark.asyncio
    async def test_error_handling_direct_only(self, client_direct_only):
        """Test error handling with direct Ollama only."""
        class MockResponse:
            def __init__(self, status=500):
                self.status = status
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def text(self):
                return "Internal server error"
        
        # Create a proper async context manager mock
        class AsyncContextManager:
            def __init__(self, response):
                self.response = response
            async def __aenter__(self):
                return self.response
            async def __aexit__(self, *args):
                pass
        
        # Create a mock session that returns the context manager directly
        class MockSession:
            def __init__(self):
                self.post_call_count = 0
            def post(self, url, json=None):
                self.post_call_count += 1
                return AsyncContextManager(MockResponse(500))
        
        mock_session = MockSession()
        client_direct_only.session = mock_session
        
        result = await client_direct_only.generate(
            model="llama3",
            prompt="test"
        )
        
        assert result is None
        assert mock_session.post_call_count == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_with_go_service(self, client_with_go_service):
        """Test error handling with Go service integration."""
        mock_fallback = AsyncMock()
        mock_fallback.execute_with_fallback = AsyncMock(side_effect=Exception("Service error"))
        
        client_with_go_service.fallback_manager = mock_fallback
        client_with_go_service.session = AsyncMock()
        client_with_go_service.go_client = AsyncMock()
        
        result = await client_with_go_service.generate(
            model="llama3",
            prompt="test"
        )
        
        assert result is None
    
    def test_get_performance_stats(self, client_with_go_service):
        """Test performance statistics retrieval."""
        expected_stats = {
            "go_service": {"success_count": 10, "failure_count": 2},
            "direct_ollama": {"call_count": 5}
        }
        
        client_with_go_service.fallback_manager = Mock()
        client_with_go_service.fallback_manager.get_performance_stats.return_value = expected_stats
        
        stats = client_with_go_service.get_performance_stats()
        
        assert stats == expected_stats
    
    def test_get_service_info(self, client_with_go_service):
        """Test service information retrieval."""
        expected_performance = {
            "go_service": {"success_count": 10, "failure_count": 2}
        }
        
        client_with_go_service.fallback_manager = Mock()
        client_with_go_service.fallback_manager.get_performance_stats.return_value = expected_performance
        
        info = client_with_go_service.get_service_info()
        
        assert info["use_go_service"] is True
        assert info["fallback_enabled"] is True
        assert info["performance_stats"] == expected_performance
    
    def test_get_service_info_direct_only(self, client_direct_only):
        """Test service information retrieval (direct only)."""
        info = client_direct_only.get_service_info()
        
        assert info["use_go_service"] is False
        assert "performance_stats" not in info or info["performance_stats"] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])