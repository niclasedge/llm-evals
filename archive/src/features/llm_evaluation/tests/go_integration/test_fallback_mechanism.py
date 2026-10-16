"""
Tests for fallback mechanism integration.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.features.llm_evaluation.go_integration.fallback_manager import FallbackManager


class TestFallbackMechanism:
    """Test cases for fallback mechanism."""
    
    @pytest.fixture
    def fallback_manager(self):
        """Create fallback manager for testing."""
        return FallbackManager(
            max_retries=3,
            backoff_factor=1.5,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60
        )
    
    @pytest.mark.asyncio
    async def test_go_service_success(self, fallback_manager):
        """Test successful Go service call."""
        async def mock_go_service():
            return {"response": "Go service response", "via_go_service": True}
        
        async def mock_direct_ollama():
            return {"response": "Direct Ollama response", "via_go_service": False}
        
        result = await fallback_manager.execute_with_fallback(
            mock_go_service, mock_direct_ollama
        )
        
        assert result["response"] == "Go service response"
        assert result["via_go_service"] is True
        assert fallback_manager.go_service_success_count == 1
        assert fallback_manager.go_service_failure_count == 0
    
    @pytest.mark.asyncio
    async def test_fallback_to_direct_ollama(self, fallback_manager):
        """Test fallback to direct Ollama when Go service fails."""
        async def mock_go_service():
            raise Exception("Go service unavailable")
        
        async def mock_direct_ollama():
            return {"response": "Direct Ollama response", "via_go_service": False}
        
        result = await fallback_manager.execute_with_fallback(
            mock_go_service, mock_direct_ollama
        )
        
        assert result["response"] == "Direct Ollama response"
        assert result["via_go_service"] is False
        assert fallback_manager.go_service_failure_count == 1
        assert fallback_manager.direct_ollama_count == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, fallback_manager):
        """Test circuit breaker opens after threshold failures."""
        async def mock_go_service():
            raise Exception("Go service unavailable")
        
        async def mock_direct_ollama():
            return {"response": "Direct Ollama response", "via_go_service": False}
        
        # Trigger failures to open circuit breaker
        for i in range(6):  # More than threshold (5)
            result = await fallback_manager.execute_with_fallback(
                mock_go_service, mock_direct_ollama
            )
            assert result["response"] == "Direct Ollama response"
        
        # Circuit breaker should now be open
        assert fallback_manager.circuit_breaker_open is True
        assert fallback_manager.go_service_failures >= fallback_manager.circuit_breaker_threshold
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_go_service(self, fallback_manager):
        """Test circuit breaker skips Go service when open."""
        # Force circuit breaker open
        fallback_manager.force_circuit_breaker_open()
        
        go_service_called = False
        
        async def mock_go_service():
            nonlocal go_service_called
            go_service_called = True
            return {"response": "Go service response", "via_go_service": True}
        
        async def mock_direct_ollama():
            return {"response": "Direct Ollama response", "via_go_service": False}
        
        result = await fallback_manager.execute_with_fallback(
            mock_go_service, mock_direct_ollama
        )
        
        assert result["response"] == "Direct Ollama response"
        assert go_service_called is False  # Go service should not be called
        assert fallback_manager.circuit_breaker_open is True
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, fallback_manager):
        """Test retry mechanism with backoff."""
        attempt_count = 0
        
        async def mock_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"Attempt {attempt_count} failed")
            return {"response": f"Success after {attempt_count} attempts"}
        
        result = await fallback_manager.execute_with_retry(mock_function)
        
        assert result["response"] == "Success after 3 attempts"
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self, fallback_manager):
        """Test retry mechanism when all attempts fail."""
        attempt_count = 0
        
        async def mock_function():
            nonlocal attempt_count
            attempt_count += 1
            raise Exception(f"Attempt {attempt_count} failed")
        
        with pytest.raises(Exception) as exc_info:
            await fallback_manager.execute_with_retry(mock_function)
        
        assert "Attempt" in str(exc_info.value)
        assert attempt_count == fallback_manager.max_retries + 1
    
    @pytest.mark.asyncio
    async def test_performance_stats(self, fallback_manager):
        """Test performance statistics collection."""
        async def mock_go_service():
            await asyncio.sleep(0.1)  # Simulate processing time
            return {"response": "Go service response", "via_go_service": True}
        
        async def mock_direct_ollama():
            await asyncio.sleep(0.05)  # Simulate processing time
            return {"response": "Direct Ollama response", "via_go_service": False}
        
        # Make some successful calls
        for _ in range(3):
            await fallback_manager.execute_with_fallback(mock_go_service, mock_direct_ollama)
        
        # Make some failed calls
        async def mock_failing_go_service():
            raise Exception("Service unavailable")
        
        for _ in range(2):
            await fallback_manager.execute_with_fallback(mock_failing_go_service, mock_direct_ollama)
        
        stats = fallback_manager.get_performance_stats()
        
        assert stats["go_service"]["success_count"] == 3
        assert stats["go_service"]["failure_count"] == 2
        assert stats["direct_ollama"]["call_count"] == 2
        assert stats["go_service"]["avg_response_time"] > 0
        assert stats["direct_ollama"]["avg_response_time"] > 0
        assert 0 <= stats["go_service"]["success_rate"] <= 1
    
    @pytest.mark.asyncio
    async def test_configuration_options(self, fallback_manager):
        """Test configuration of fallback behavior."""
        # Test with fallback disabled
        fallback_manager.configure_fallback(enabled=False)
        
        async def mock_go_service():
            raise Exception("Go service unavailable")
        
        async def mock_direct_ollama():
            return {"response": "Direct Ollama response", "via_go_service": False}
        
        with pytest.raises(Exception):
            await fallback_manager.execute_with_fallback(mock_go_service, mock_direct_ollama)
        
        # Test with direct Ollama preferred
        fallback_manager.configure_fallback(enabled=True, prefer_go_service=False)
        
        async def mock_go_service():
            return {"response": "Go service response", "via_go_service": True}
        
        result = await fallback_manager.execute_with_fallback(mock_go_service, mock_direct_ollama)
        
        assert result["response"] == "Direct Ollama response"
        assert result["via_go_service"] is False
    
    def test_circuit_breaker_manual_control(self, fallback_manager):
        """Test manual circuit breaker control."""
        # Test forcing circuit breaker open
        fallback_manager.force_circuit_breaker_open()
        assert fallback_manager.circuit_breaker_open is True
        
        # Test forcing circuit breaker closed
        fallback_manager.force_circuit_breaker_closed()
        assert fallback_manager.circuit_breaker_open is False
        assert fallback_manager.go_service_failures == 0
    
    def test_statistics_reset(self, fallback_manager):
        """Test statistics reset functionality."""
        # Set some statistics
        fallback_manager.go_service_success_count = 10
        fallback_manager.go_service_failure_count = 5
        fallback_manager.direct_ollama_count = 3
        
        # Reset statistics
        fallback_manager.reset_statistics()
        
        assert fallback_manager.go_service_success_count == 0
        assert fallback_manager.go_service_failure_count == 0
        assert fallback_manager.direct_ollama_count == 0
        assert fallback_manager.circuit_breaker_open is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])