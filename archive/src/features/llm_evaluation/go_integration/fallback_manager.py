"""
Fallback manager for Go service integration.
Handles fallback logic and retry mechanisms when Go service is unavailable.
"""

import asyncio
import time
from typing import Callable, Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class FallbackManager:
    """Manages fallback mechanisms for Go service integration."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.5,
                 circuit_breaker_threshold: int = 5, circuit_breaker_timeout: int = 60):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
        # Circuit breaker state
        self.go_service_failures = 0
        self.last_failure_time = None
        self.circuit_breaker_open = False
        
        # Performance tracking
        self.go_service_success_count = 0
        self.go_service_failure_count = 0
        self.direct_ollama_count = 0
        
        # Timing statistics
        self.go_service_response_times = []
        self.direct_ollama_response_times = []
        
        # Fallback state
        self.fallback_enabled = True
        self.prefer_go_service = True
    
    def _should_skip_go_service(self) -> bool:
        """Check if Go service should be skipped due to circuit breaker."""
        if not self.circuit_breaker_open:
            return False
        
        # Check if circuit breaker timeout has passed
        if (self.last_failure_time and 
            time.time() - self.last_failure_time > self.circuit_breaker_timeout):
            logger.info("Circuit breaker timeout passed, attempting to close circuit")
            self.circuit_breaker_open = False
            self.go_service_failures = 0
            return False
        
        return True
    
    def _record_go_service_success(self, response_time: float):
        """Record successful Go service call."""
        self.go_service_success_count += 1
        self.go_service_response_times.append(response_time)
        
        # Reset failure count on success
        if self.go_service_failures > 0:
            logger.info(f"Go service recovered after {self.go_service_failures} failures")
            self.go_service_failures = 0
        
        # Close circuit breaker if it was open
        if self.circuit_breaker_open:
            logger.info("Closing circuit breaker due to successful Go service call")
            self.circuit_breaker_open = False
    
    def _record_go_service_failure(self, error: Exception):
        """Record failed Go service call."""
        self.go_service_failure_count += 1
        self.go_service_failures += 1
        self.last_failure_time = time.time()
        
        logger.warning(f"Go service failure #{self.go_service_failures}: {error}")
        
        # Open circuit breaker if threshold reached
        if self.go_service_failures >= self.circuit_breaker_threshold:
            logger.error(f"Opening circuit breaker after {self.go_service_failures} failures")
            self.circuit_breaker_open = True
    
    def _record_direct_ollama_success(self, response_time: float):
        """Record successful direct Ollama call."""
        self.direct_ollama_count += 1
        self.direct_ollama_response_times.append(response_time)
    
    async def execute_with_fallback(self, go_func: Callable, direct_func: Callable, 
                                   *args, **kwargs) -> Any:
        """
        Execute function with Go service, fallback to direct on failure.
        
        Args:
            go_func: Function that uses Go service
            direct_func: Function that uses direct Ollama
            *args: Arguments to pass to both functions
            **kwargs: Keyword arguments to pass to both functions
            
        Returns:
            Result from either Go service or direct Ollama
        """
        if not self.fallback_enabled:
            # Fallback disabled, only try Go service
            return await go_func(*args, **kwargs)
        
        # Check if we should skip Go service due to circuit breaker
        if self._should_skip_go_service():
            logger.info("Circuit breaker open, using direct Ollama")
            start_time = time.time()
            result = await direct_func(*args, **kwargs)
            response_time = time.time() - start_time
            self._record_direct_ollama_success(response_time)
            return result
        
        # Try Go service first (if preferred)
        if self.prefer_go_service:
            try:
                start_time = time.time()
                result = await go_func(*args, **kwargs)
                response_time = time.time() - start_time
                self._record_go_service_success(response_time)
                return result
            except Exception as e:
                self._record_go_service_failure(e)
                
                if self.fallback_enabled:
                    logger.info("Falling back to direct Ollama due to Go service failure")
                    start_time = time.time()
                    result = await direct_func(*args, **kwargs)
                    response_time = time.time() - start_time
                    self._record_direct_ollama_success(response_time)
                    return result
                else:
                    raise
        else:
            # Direct Ollama preferred
            start_time = time.time()
            result = await direct_func(*args, **kwargs)
            response_time = time.time() - start_time
            self._record_direct_ollama_success(response_time)
            return result
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function
            
        Returns:
            Result from function
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed: {e}")
        
        # If we get here, all attempts failed
        if last_exception:
            raise last_exception
        else:
            raise Exception("All retry attempts failed")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance statistics
        """
        go_avg_time = (sum(self.go_service_response_times) / len(self.go_service_response_times) 
                      if self.go_service_response_times else 0)
        
        direct_avg_time = (sum(self.direct_ollama_response_times) / len(self.direct_ollama_response_times) 
                          if self.direct_ollama_response_times else 0)
        
        return {
            "go_service": {
                "success_count": self.go_service_success_count,
                "failure_count": self.go_service_failure_count,
                "avg_response_time": go_avg_time,
                "success_rate": (self.go_service_success_count / 
                               (self.go_service_success_count + self.go_service_failure_count)
                               if (self.go_service_success_count + self.go_service_failure_count) > 0 else 0)
            },
            "direct_ollama": {
                "call_count": self.direct_ollama_count,
                "avg_response_time": direct_avg_time
            },
            "circuit_breaker": {
                "open": self.circuit_breaker_open,
                "failures": self.go_service_failures,
                "threshold": self.circuit_breaker_threshold,
                "last_failure": self.last_failure_time
            },
            "fallback": {
                "enabled": self.fallback_enabled,
                "prefer_go_service": self.prefer_go_service
            }
        }
    
    def reset_statistics(self):
        """Reset all performance statistics."""
        self.go_service_success_count = 0
        self.go_service_failure_count = 0
        self.direct_ollama_count = 0
        self.go_service_response_times = []
        self.direct_ollama_response_times = []
        self.go_service_failures = 0
        self.last_failure_time = None
        self.circuit_breaker_open = False
    
    def configure_fallback(self, enabled: bool = True, prefer_go_service: bool = True):
        """
        Configure fallback behavior.
        
        Args:
            enabled: Whether fallback is enabled
            prefer_go_service: Whether to prefer Go service over direct Ollama
        """
        self.fallback_enabled = enabled
        self.prefer_go_service = prefer_go_service
        
        logger.info(f"Fallback configured: enabled={enabled}, prefer_go_service={prefer_go_service}")
    
    def force_circuit_breaker_open(self):
        """Force circuit breaker to open state."""
        self.circuit_breaker_open = True
        self.go_service_failures = self.circuit_breaker_threshold
        self.last_failure_time = time.time()
        logger.warning("Circuit breaker forced open")
    
    def force_circuit_breaker_closed(self):
        """Force circuit breaker to closed state."""
        self.circuit_breaker_open = False
        self.go_service_failures = 0
        self.last_failure_time = None
        logger.info("Circuit breaker forced closed")


# Test function for fallback manager
async def test_fallback_manager():
    """Test the fallback manager functionality."""
    manager = FallbackManager(max_retries=2, backoff_factor=1.2)
    
    print("Testing fallback manager...")
    
    # Mock functions for testing
    async def mock_go_service_success():
        await asyncio.sleep(0.1)
        return {"response": "Go service response", "via_go_service": True}
    
    async def mock_go_service_failure():
        await asyncio.sleep(0.05)
        raise Exception("Go service unavailable")
    
    async def mock_direct_ollama():
        await asyncio.sleep(0.2)
        return {"response": "Direct Ollama response", "via_go_service": False}
    
    # Test successful Go service call
    result = await manager.execute_with_fallback(
        mock_go_service_success, mock_direct_ollama
    )
    print(f"Success result: {result}")
    
    # Test Go service failure with fallback
    result = await manager.execute_with_fallback(
        mock_go_service_failure, mock_direct_ollama
    )
    print(f"Fallback result: {result}")
    
    # Test circuit breaker behavior
    for i in range(6):  # Trigger circuit breaker
        try:
            await manager.execute_with_fallback(
                mock_go_service_failure, mock_direct_ollama
            )
        except Exception as e:
            print(f"Attempt {i+1}: {e}")
    
    # Test with circuit breaker open
    result = await manager.execute_with_fallback(
        mock_go_service_success, mock_direct_ollama
    )
    print(f"Circuit breaker open result: {result}")
    
    # Get performance stats
    stats = manager.get_performance_stats()
    print(f"Performance stats: {stats}")
    
    # Test retry mechanism
    async def mock_retry_function():
        if not hasattr(mock_retry_function, 'attempts'):
            mock_retry_function.attempts = 0
        mock_retry_function.attempts += 1
        
        if mock_retry_function.attempts < 3:
            raise Exception(f"Attempt {mock_retry_function.attempts} failed")
        
        return {"response": "Success after retries", "attempts": mock_retry_function.attempts}
    
    result = await manager.execute_with_retry(mock_retry_function)
    print(f"Retry result: {result}")


if __name__ == "__main__":
    asyncio.run(test_fallback_manager())