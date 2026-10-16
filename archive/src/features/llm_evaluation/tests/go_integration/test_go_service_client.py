"""
Tests for Go service client integration.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
from aiohttp import ClientSession

from src.features.llm_evaluation.go_integration.go_service_client import GoServiceClient


class TestGoServiceClient:
    """Test cases for Go service client."""
    
    @pytest.fixture
    def client(self):
        """Create Go service client for testing."""
        return GoServiceClient("http://localhost:8080")
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
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
                self.last_url = None
            def get(self, url):
                self.get_call_count += 1
                self.last_url = url
                return AsyncContextManager(MockResponse(200, {"status": "healthy"}))
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.health_check()
        
        assert result is True
        assert mock_session.get_call_count == 1
        assert mock_session.last_url == "http://localhost:8080/health"
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test failed health check."""
        class MockResponse:
            def __init__(self, status=503, json_data=None):
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
                return AsyncContextManager(MockResponse(503, {"status": "unhealthy"}))
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.health_check()
        
        assert result is False
        assert mock_session.get_call_count == 1
    
    @pytest.mark.asyncio
    async def test_health_check_exception(self, client):
        """Test health check with exception."""
        # Create a mock session that raises an exception
        class MockSession:
            def __init__(self):
                self.get_call_count = 0
            def get(self, url):
                self.get_call_count += 1
                raise Exception("Connection error")
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.health_check()
        
        assert result is False
        assert mock_session.get_call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_service_info_success(self, client):
        """Test successful service info retrieval."""
        expected_info = {
            "version": "1.0.0",
            "features": ["generate", "chat", "models"],
            "ollama_connected": True
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
                self.get_call_count = 0
                self.last_url = None
            def get(self, url):
                self.get_call_count += 1
                self.last_url = url
                return AsyncContextManager(MockResponse(200, expected_info))
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.get_service_info()
        
        assert result == expected_info
        assert mock_session.get_call_count == 1
        assert mock_session.last_url == "http://localhost:8080/api/status"
    
    @pytest.mark.asyncio
    async def test_list_models_success(self, client):
        """Test successful model listing."""
        expected_models = [
            {"name": "llama3", "size": 4000000000},
            {"name": "gemma", "size": 2000000000}
        ]
        
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
                self.last_url = None
            def get(self, url):
                self.get_call_count += 1
                self.last_url = url
                return AsyncContextManager(MockResponse(200, {"models": expected_models}))
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.list_models()
        
        assert result == expected_models
        assert mock_session.get_call_count == 1
        assert mock_session.last_url == "http://localhost:8080/api/models"
    
    @pytest.mark.asyncio
    async def test_generate_success(self, client):
        """Test successful text generation."""
        request_data = {
            "model": "llama3",
            "prompt": "What is the capital of France?",
            "system": "You are a helpful assistant."
        }
        
        expected_response = {
            "response": "Paris is the capital of France.",
            "done": True,
            "model": "llama3"
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
                self.last_url = None
            def post(self, url, json=None, timeout=None):
                self.post_call_count += 1
                self.last_url = url
                return AsyncContextManager(MockResponse(200, expected_response))
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.generate(**request_data)
        
        assert result["response"] == expected_response["response"]
        assert result["model"] == expected_response["model"]
        assert "_timing" in result
        assert result["_timing"]["via_go_service"] is True
        assert mock_session.post_call_count == 1
    
    @pytest.mark.asyncio
    async def test_chat_success(self, client):
        """Test successful chat interaction."""
        request_data = {
            "model": "llama3",
            "messages": [{"role": "user", "content": "Hello!"}]
        }
        
        expected_response = {
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            "done": True,
            "model": "llama3"
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
                self.last_url = None
            def post(self, url, json=None, timeout=None):
                self.post_call_count += 1
                self.last_url = url
                return AsyncContextManager(MockResponse(200, expected_response))
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.chat(**request_data)
        
        assert result["message"] == expected_response["message"]
        assert result["model"] == expected_response["model"]
        assert "_timing" in result
        assert result["_timing"]["via_go_service"] is True
        assert mock_session.post_call_count == 1
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as context manager."""
        with patch.object(GoServiceClient, '__aenter__', return_value=AsyncMock()):
            with patch.object(GoServiceClient, '__aexit__', return_value=AsyncMock()):
                async with GoServiceClient() as client:
                    assert client is not None
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling in various scenarios."""
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
            def post(self, url, json=None, timeout=None):
                self.post_call_count += 1
                return AsyncContextManager(MockResponse(500))
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.generate(model="llama3", prompt="test")
        
        assert result is None
        assert mock_session.post_call_count == 1
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, client):
        """Test timeout handling."""
        # Create a mock session that raises a timeout error
        class MockSession:
            def __init__(self):
                self.post_call_count = 0
            def post(self, url, json=None, timeout=None):
                self.post_call_count += 1
                raise asyncio.TimeoutError()
        
        mock_session = MockSession()
        client.session = mock_session
        
        result = await client.generate(model="llama3", prompt="test")
        
        assert result is None
        assert mock_session.post_call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])