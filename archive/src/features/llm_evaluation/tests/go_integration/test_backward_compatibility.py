"""
Tests for backward compatibility with existing tests.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.features.llm_evaluation.test_framework.ollama_client import OllamaClient


class MockContextManager:
    """Helper class for mocking async context managers."""
    
    def __init__(self, response):
        self.response = response
        
    async def __aenter__(self):
        return self.response
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


class TestBackwardCompatibility:
    """Test cases to ensure backward compatibility."""
    
    @pytest.fixture
    def legacy_client(self):
        """Create OllamaClient as it would be used in legacy code."""
        return OllamaClient(use_go_service=False)  # Explicitly disable Go service for legacy tests
    
    @pytest.mark.asyncio
    async def test_legacy_health_check_interface(self, legacy_client):
        """Test that legacy health check interface still works."""
        mock_response = AsyncMock()
        mock_response.status = 200
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's get method
        with patch.object(legacy_client.session, 'get', return_value=MockContextManager(mock_response)):
            result = await legacy_client.health_check()
            
            assert isinstance(result, bool)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_legacy_list_models_interface(self, legacy_client):
        """Test that legacy list models interface still works."""
        expected_models = [{"name": "llama3", "size": 4000000000}]
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"models": expected_models}
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's get method
        with patch.object(legacy_client.session, 'get', return_value=MockContextManager(mock_response)):
            result = await legacy_client.list_models()
            
            assert isinstance(result, list)
            assert result == expected_models
    
    @pytest.mark.asyncio
    async def test_legacy_generate_interface(self, legacy_client):
        """Test that legacy generate interface still works."""
        expected_response = {
            "response": "Paris is the capital of France.",
            "model": "llama3",
            "done": True
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = expected_response
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)):
            result = await legacy_client.generate(
                model="llama3",
                prompt="What is the capital of France?"
            )
            
            assert isinstance(result, dict)
            assert result["response"] == expected_response["response"]
            assert result["model"] == expected_response["model"]
            assert "_timing" in result  # Should still have timing info
    
    @pytest.mark.asyncio
    async def test_legacy_generate_with_system_prompt(self, legacy_client):
        """Test that legacy generate with system prompt still works."""
        expected_response = {
            "response": "Paris is the capital of France.",
            "model": "llama3",
            "done": True
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = expected_response
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)):
            result = await legacy_client.generate(
                model="llama3",
                prompt="What is the capital of France?",
                system_prompt="You are a helpful assistant."
            )
            
            assert isinstance(result, dict)
            assert result["response"] == expected_response["response"]
            assert result["model"] == expected_response["model"]
    
    @pytest.mark.asyncio
    async def test_legacy_chat_interface(self, legacy_client):
        """Test that legacy chat interface still works."""
        expected_response = {
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            "model": "llama3",
            "done": True
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = expected_response
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)):
            result = await legacy_client.chat(
                model="llama3",
                messages=[{"role": "user", "content": "Hello!"}]
            )
            
            assert isinstance(result, dict)
            assert result["message"] == expected_response["message"]
            assert result["model"] == expected_response["model"]
            assert "_timing" in result
    
    @pytest.mark.asyncio
    async def test_legacy_pull_model_interface(self, legacy_client):
        """Test that legacy pull model interface still works."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content = AsyncMock()
        mock_response.content.__aiter__.return_value = [
            b'{"status": "downloading"}\n',
            b'{"status": "success"}\n'
        ]
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)):
            result = await legacy_client.pull_model("llama3")
            
            assert isinstance(result, bool)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_legacy_model_info_interface(self, legacy_client):
        """Test that legacy model info interface still works."""
        expected_info = {
            "license": "MIT",
            "modelfile": "FROM llama3",
            "parameters": {},
            "template": "{{ .Prompt }}"
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = expected_info
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)):
            result = await legacy_client.model_info("llama3")
            
            assert isinstance(result, dict)
            assert result["license"] == expected_info["license"]
            assert result["modelfile"] == expected_info["modelfile"]
    
    @pytest.mark.asyncio
    async def test_legacy_context_manager_usage(self, legacy_client):
        """Test that legacy context manager usage still works."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Make the session mock async-compatible
            mock_session.return_value.close = AsyncMock()
            async with legacy_client as client:
                assert client is not None
                assert hasattr(client, 'session')
                mock_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_legacy_manual_session_management(self, legacy_client):
        """Test that legacy manual session management still works."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Make the session mock async-compatible
            mock_session.return_value.close = AsyncMock()
            await legacy_client._ensure_session()
            assert legacy_client.session is not None
            mock_session.assert_called_once()
            
            await legacy_client.close()
            assert legacy_client.session is None
    
    @pytest.mark.asyncio
    async def test_legacy_error_handling(self, legacy_client):
        """Test that legacy error handling behavior is preserved."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal server error"
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)):
            result = await legacy_client.generate(
                model="llama3",
                prompt="test"
            )
            
            # Should return None on error (legacy behavior)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_legacy_timeout_handling(self, legacy_client):
        """Test that legacy timeout handling behavior is preserved."""
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method to raise timeout
        with patch.object(legacy_client.session, 'post', side_effect=asyncio.TimeoutError()):
            result = await legacy_client.generate(
                model="llama3",
                prompt="test"
            )
            
            # Should return None on timeout (legacy behavior)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_legacy_response_format_preserved(self, legacy_client):
        """Test that legacy response format is preserved."""
        expected_response = {
            "response": "Test response",
            "model": "llama3",
            "done": True,
            "total_duration": 1000000,
            "load_duration": 500000,
            "prompt_eval_count": 10,
            "prompt_eval_duration": 200000,
            "eval_count": 20,
            "eval_duration": 300000,
            "context": [1, 2, 3]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = expected_response
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)):
            result = await legacy_client.generate(
                model="llama3",
                prompt="test"
            )
            
            # All original fields should be preserved
            for key in expected_response:
                assert key in result
                assert result[key] == expected_response[key]
            
            # Timing information should be added
            assert "_timing" in result
            assert "response_time" in result["_timing"]
            assert "timestamp" in result["_timing"]
    
    @pytest.mark.asyncio
    async def test_legacy_streaming_parameter(self, legacy_client):
        """Test that legacy streaming parameter is preserved."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"response": "test", "done": True}
        
        # Ensure session exists
        await legacy_client._ensure_session()
        
        # Mock the session's post method
        with patch.object(legacy_client.session, 'post', return_value=MockContextManager(mock_response)) as mock_post:
            # Test with streaming=True
            await legacy_client.generate(
                model="llama3",
                prompt="test",
                stream=True
            )
            
            # Verify the request was made with stream=True
            call_args = mock_post.call_args
            assert call_args[1]['json']['stream'] is True
            
            # Test with streaming=False
            await legacy_client.generate(
                model="llama3",
                prompt="test",
                stream=False
            )
            
            # Verify the request was made with stream=False
            call_args = mock_post.call_args
            assert call_args[1]['json']['stream'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])